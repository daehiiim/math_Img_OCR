from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import secrets
import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import requests
from polar_sdk import Polar

ROOT = Path(__file__).resolve().parents[1] / "02_main"
sys.path.insert(0, str(ROOT))

from app.config import get_settings

STATE_PATH = Path(__file__).resolve().with_name("polar_e2e_state.json")
DEFAULT_API_BASE_URL = "http://localhost:8000"


def _b64url(data: bytes) -> str:
    """JWT 인코딩에 필요한 base64url 문자열을 만든다."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _print_json(payload: dict[str, Any]) -> None:
    """검증 결과를 사람이 읽기 쉬운 JSON으로 출력한다."""
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _read_mapping_value(item: Any, key: str) -> Any:
    """dict 또는 SDK 모델에서 같은 키를 공통 방식으로 읽는다."""
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _normalize_api_base_url(api_base_url: str) -> str:
    """API base URL의 끝 슬래시를 제거해 요청 경로를 안정화한다."""
    return api_base_url.rstrip("/")


def build_test_jwt(user_id: str, jwt_secret: str) -> str:
    """백엔드가 허용하는 HS256 테스트 JWT를 발급한다."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "aud": "authenticated",
        "role": "authenticated",
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "iat": now,
        "exp": now + 3600,
    }
    header_segment = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _b64url(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def request_api(
    method: str,
    path: str,
    token: str,
    *,
    api_base_url: str,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """백엔드 API를 인증 토큰과 함께 호출하고 JSON 응답을 반환한다."""
    response = requests.request(
        method=method,
        url=f"{_normalize_api_base_url(api_base_url)}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=json_body,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def request_supabase(
    method: str,
    path: str,
    *,
    api_key: str,
    access_token: str,
    params: dict[str, str] | None = None,
    json_body: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> Any:
    """Supabase REST를 service role 권한으로 호출하고 응답을 반환한다."""
    settings = get_settings(ROOT)
    if not settings.auth.supabase_url:
        raise SystemExit("SUPABASE_URL is required")

    response = requests.request(
        method=method,
        url=f"{settings.auth.supabase_url.rstrip('/')}{path}",
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        params=params,
        json=json_body,
        timeout=60,
    )
    response.raise_for_status()
    if not response.text:
        return None
    return response.json()


def save_state(payload: dict[str, Any]) -> None:
    """만료 가능한 토큰을 제외한 helper 상태를 파일에 저장한다."""
    persisted = dict(payload)
    persisted.pop("token", None)
    STATE_PATH.write_text(json.dumps(persisted, indent=2), encoding="utf-8")


def load_state() -> dict[str, Any]:
    """저장된 helper 상태를 읽고 없으면 종료한다."""
    if not STATE_PATH.exists():
        raise SystemExit("state file is missing")
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def refresh_state_token(state: dict[str, Any], jwt_secret: str) -> dict[str, Any]:
    """state에 저장된 사용자 UUID로 항상 새 테스트 JWT를 발급한다."""
    user_id = str(state.get("user_id") or "").strip()
    if not user_id:
        raise ValueError("state user_id is missing")
    refreshed = dict(state)
    refreshed["token"] = build_test_jwt(user_id, jwt_secret)
    return refreshed


def ensure_state_user(
    state: dict[str, Any] | None,
    create_user: Callable[[], tuple[str, str]],
) -> dict[str, Any]:
    """state에 사용자 정보가 없으면 새 Supabase Auth 사용자를 만든다."""
    current = dict(state or {})
    user_id = str(current.get("user_id") or "").strip()
    email = str(current.get("email") or "").strip()
    if user_id and email:
        return current

    user_id, email = create_user()
    current["user_id"] = user_id
    current["email"] = email
    return current


def load_runtime_state(*, force_new_user: bool = False) -> dict[str, Any]:
    """현재 helper state를 읽고 API 호출용 새 JWT를 주입한다."""
    settings = get_settings(ROOT)
    if not settings.auth.supabase_jwt_secret:
        raise SystemExit("SUPABASE_JWT_SECRET is required")

    base_state: dict[str, Any] = {}
    if not force_new_user and STATE_PATH.exists():
        base_state = load_state()

    ensured_state = ensure_state_user(base_state, create_auth_user)
    refreshed = refresh_state_token(ensured_state, settings.auth.supabase_jwt_secret)
    save_state(refreshed)
    return refreshed


def create_auth_user() -> tuple[str, str]:
    """Supabase Admin API로 검증 전용 테스트 사용자를 만든다."""
    settings = get_settings(ROOT)
    if not settings.auth.supabase_url or not settings.auth.supabase_service_role_key:
        raise SystemExit("Supabase admin settings are required")

    email = f"polar-e2e-{secrets.token_hex(6)}@example.com"
    response = requests.post(
        f"{settings.auth.supabase_url.rstrip('/')}/auth/v1/admin/users",
        headers={
            "apikey": settings.auth.supabase_service_role_key,
            "Authorization": f"Bearer {settings.auth.supabase_service_role_key}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "password": secrets.token_urlsafe(18),
            "email_confirm": True,
            "user_metadata": {"source": "polar-e2e"},
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    user_id = payload.get("id") or payload.get("user", {}).get("id")
    if not user_id:
        raise SystemExit("created auth user id is missing")
    return str(user_id), email


def init_user(*, force_new_user: bool = False) -> None:
    """같은 검증 사용자 state를 준비하고 출력한다."""
    state = load_runtime_state(force_new_user=force_new_user)
    _print_json({key: value for key, value in state.items() if key != "token"})


def create_checkout(plan_id: str, *, api_base_url: str, force_new_user: bool = False) -> None:
    """같은 테스트 사용자로 checkout을 만들고 상태 파일을 갱신한다."""
    state = load_runtime_state(force_new_user=force_new_user)
    token = state["token"]
    profile = request_api("GET", "/billing/profile", token, api_base_url=api_base_url)
    checkout = request_api(
        "POST",
        "/billing/checkout",
        token,
        api_base_url=api_base_url,
        json_body={
            "plan_id": plan_id,
            "success_url": f"http://localhost:5173/payment/{plan_id}?checkout=success&checkout_id={{CHECKOUT_ID}}",
            "cancel_url": f"http://localhost:5173/payment/{plan_id}?checkout=cancel",
        },
    )
    updated_state = {
        **state,
        "profile": profile,
        "checkout_id": checkout["checkout_id"],
        "checkout_url": checkout["checkout_url"],
        "plan_id": plan_id,
        "last_checkout_requested_at": int(time.time()),
        "api_base_url": _normalize_api_base_url(api_base_url),
    }
    save_state(updated_state)
    _print_json({key: value for key, value in updated_state.items() if key != "token"})


def checkout_status(*, api_base_url: str) -> None:
    """현재 state의 checkout 상태와 적립 여부를 조회한다."""
    state = load_runtime_state()
    checkout_id = state.get("checkout_id")
    if not checkout_id:
        raise SystemExit("checkout_id is missing in state")
    payload = request_api(
        "GET",
        f"/billing/checkout/{checkout_id}",
        state["token"],
        api_base_url=api_base_url,
    )
    _print_json(payload)


def wait_checkout(*, api_base_url: str, timeout_seconds: int, interval_seconds: int) -> None:
    """credits_applied=true가 될 때까지 checkout 상태를 polling한다."""
    state = load_runtime_state()
    checkout_id = state.get("checkout_id")
    if not checkout_id:
        raise SystemExit("checkout_id is missing in state")

    deadline = time.time() + timeout_seconds
    last_payload: dict[str, Any] | None = None
    while time.time() < deadline:
        last_payload = request_api(
            "GET",
            f"/billing/checkout/{checkout_id}",
            state["token"],
            api_base_url=api_base_url,
        )
        if last_payload.get("credits_applied") is True:
            _print_json(last_payload)
            return
        time.sleep(interval_seconds)

    if last_payload is not None:
        _print_json(last_payload)
    raise SystemExit("checkout polling timed out before credits_applied=true")


def portal(*, api_base_url: str) -> None:
    """현재 state 사용자 기준 customer portal URL을 생성한다."""
    state = load_runtime_state()
    payload = request_api("GET", "/billing/portal", state["token"], api_base_url=api_base_url)
    _print_json(payload)


def _query_table(table: str, *, filters: dict[str, str]) -> list[dict[str, Any]]:
    """service role로 PostgREST select를 수행한다."""
    settings = get_settings(ROOT)
    if not settings.auth.supabase_service_role_key:
        raise SystemExit("SUPABASE_SERVICE_ROLE_KEY is required")
    payload = request_supabase(
        "GET",
        f"/rest/v1/{table}",
        api_key=settings.auth.supabase_service_role_key,
        access_token=settings.auth.supabase_service_role_key,
        params=filters,
    )
    return list(payload or [])


def build_db_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """profiles, payment_events, credit_ledger를 한 번에 묶어 검증 스냅샷을 만든다."""
    user_id = str(state.get("user_id") or "").strip()
    if not user_id:
        raise SystemExit("user_id is missing in state")

    profile_rows = _query_table(
        "profiles",
        filters={
            "select": "user_id,credits_balance,used_credits,openai_connected,openai_key_masked",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        },
    )
    payment_event_rows = _query_table(
        "payment_events",
        filters={
            "select": "id,provider,provider_event_id,provider_order_id,provider_checkout_id,provider_customer_id,plan_id,credits_added,amount,currency,status,created_at",
            "user_id": f"eq.{user_id}",
            "provider": "eq.polar",
            "order": "created_at.desc",
            "limit": "20",
        },
    )
    ledger_rows = _query_table(
        "credit_ledger",
        filters={
            "select": "id,payment_event_id,job_id,delta,balance_after,reason,created_at",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": "50",
        },
    )

    checkout_id = str(state.get("checkout_id") or "").strip()
    matching_checkout_rows = [
        row for row in payment_event_rows if str(row.get("provider_checkout_id") or "") == checkout_id
    ]
    purchase_rows = [row for row in ledger_rows if str(row.get("reason") or "") == "purchase"]
    ocr_charge_rows = [row for row in ledger_rows if str(row.get("reason") or "") == "ocr_success_charge"]

    snapshot = {
        "user_id": user_id,
        "email": state.get("email"),
        "checkout_id": checkout_id or None,
        "profile": profile_rows[0] if profile_rows else None,
        "payment_events": {
            "count": len(payment_event_rows),
            "rows": payment_event_rows,
            "matching_checkout_count": len(matching_checkout_rows),
            "matching_checkout_rows": matching_checkout_rows,
        },
        "credit_ledger": {
            "count": len(ledger_rows),
            "rows": ledger_rows,
            "purchase_count": len(purchase_rows),
            "purchase_rows": purchase_rows,
            "ocr_success_charge_count": len(ocr_charge_rows),
            "ocr_success_charge_rows": ocr_charge_rows,
        },
    }
    return snapshot


def db_snapshot() -> None:
    """현재 state 기준 DB 검증 스냅샷을 출력하고 event 정보를 state에 저장한다."""
    state = load_runtime_state()
    snapshot = build_db_snapshot(state)
    matching_rows = snapshot["payment_events"]["matching_checkout_rows"]
    if matching_rows:
        latest = matching_rows[0]
        state["provider_event_id"] = latest.get("provider_event_id")
        state["provider_order_id"] = latest.get("provider_order_id")
        state["provider_customer_id"] = latest.get("provider_customer_id")
        save_state(state)
        snapshot["state_update"] = {
            "provider_event_id": state.get("provider_event_id"),
            "provider_order_id": state.get("provider_order_id"),
            "provider_customer_id": state.get("provider_customer_id"),
        }
    _print_json(snapshot)


def _iter_recent_deliveries() -> Iterable[Any]:
    """최근 Polar webhook delivery 목록을 순회한다."""
    settings = get_settings(ROOT)
    if not settings.billing.polar_access_token:
        raise SystemExit("POLAR_ACCESS_TOKEN is required")
    client = Polar(
        access_token=settings.billing.polar_access_token,
        server=settings.billing.polar_server,
    )
    response = client.webhooks.list_webhook_deliveries(limit=100)
    while response is not None:
        for item in response.result.items:
            yield item
        response = response.next() if response.next else None


def find_webhook_event_id(deliveries: Iterable[Any], checkout_id: str) -> str:
    """delivery payload에서 checkout_id와 일치하는 webhook event id를 찾는다."""
    target_checkout_id = str(checkout_id).strip()
    for delivery in deliveries:
        webhook_event = _read_mapping_value(delivery, "webhook_event")
        payload = _read_mapping_value(webhook_event, "payload")
        if not payload:
            continue
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        data = decoded.get("data") or {}
        if str(data.get("checkout_id") or "").strip() == target_checkout_id:
            event_id = _read_mapping_value(webhook_event, "id")
            if event_id:
                return str(event_id)
    raise ValueError("matching webhook event was not found for checkout_id")


def resolve_provider_event_id(state: dict[str, Any]) -> str:
    """state와 DB 스냅샷을 기반으로 redelivery 대상 event id를 결정한다."""
    provider_event_id = str(state.get("provider_event_id") or "").strip()
    if provider_event_id:
        return provider_event_id

    snapshot = build_db_snapshot(state)
    matching_rows = snapshot["payment_events"]["matching_checkout_rows"]
    if matching_rows:
        provider_event_id = str(matching_rows[0].get("provider_event_id") or "").strip()
        if provider_event_id:
            state["provider_event_id"] = provider_event_id
            save_state(state)
            return provider_event_id

    checkout_id = str(state.get("checkout_id") or "").strip()
    if not checkout_id:
        raise SystemExit("checkout_id is missing in state")

    provider_event_id = find_webhook_event_id(_iter_recent_deliveries(), checkout_id=checkout_id)
    state["provider_event_id"] = provider_event_id
    save_state(state)
    return provider_event_id


def redeliver() -> None:
    """현재 checkout에 연결된 Polar webhook event를 1회 재전송한다."""
    settings = get_settings(ROOT)
    if not settings.billing.polar_access_token:
        raise SystemExit("POLAR_ACCESS_TOKEN is required")

    state = load_runtime_state()
    provider_event_id = resolve_provider_event_id(state)
    client = Polar(
        access_token=settings.billing.polar_access_token,
        server=settings.billing.polar_server,
    )
    payload = client.webhooks.redeliver_webhook_event(id=provider_event_id)
    result = {
        "provider_event_id": provider_event_id,
        "response": payload,
    }
    _print_json(result)


def show_state() -> None:
    """저장된 helper state를 그대로 출력한다."""
    _print_json(load_state())


def parse_args() -> argparse.Namespace:
    """helper CLI 인자를 정의하고 파싱한다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-user")
    init_parser.add_argument("--force-new-user", action="store_true")

    create_parser = subparsers.add_parser("create-checkout")
    create_parser.add_argument("--plan-id", default="single")
    create_parser.add_argument("--force-new-user", action="store_true")

    subparsers.add_parser("checkout-status")

    wait_parser = subparsers.add_parser("wait-checkout")
    wait_parser.add_argument("--timeout-seconds", type=int, default=300)
    wait_parser.add_argument("--interval-seconds", type=int, default=5)

    subparsers.add_parser("portal")
    subparsers.add_parser("db-snapshot")
    subparsers.add_parser("redeliver")
    subparsers.add_parser("state")

    return parser.parse_args()


def main() -> None:
    """지정한 subcommand에 맞는 검증 동작을 실행한다."""
    args = parse_args()
    if args.command == "init-user":
        init_user(force_new_user=args.force_new_user)
        return
    if args.command == "create-checkout":
        create_checkout(
            args.plan_id,
            api_base_url=args.api_base_url,
            force_new_user=args.force_new_user,
        )
        return
    if args.command == "checkout-status":
        checkout_status(api_base_url=args.api_base_url)
        return
    if args.command == "wait-checkout":
        wait_checkout(
            api_base_url=args.api_base_url,
            timeout_seconds=args.timeout_seconds,
            interval_seconds=args.interval_seconds,
        )
        return
    if args.command == "portal":
        portal(api_base_url=args.api_base_url)
        return
    if args.command == "db-snapshot":
        db_snapshot()
        return
    if args.command == "redeliver":
        redeliver()
        return
    if args.command == "state":
        show_state()
        return
    raise SystemExit("unsupported command")


if __name__ == "__main__":
    main()
