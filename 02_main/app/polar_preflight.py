from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

from app.config import AppSettings, get_settings

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PreflightCheck:
    """Polar sandbox 준비 상태를 표현하는 단일 점검 결과다."""

    key: str
    status: str
    detail: str


Requester = Callable[..., Any]
WhichLookup = Callable[[str], str | None]


def _ok(key: str, detail: str) -> PreflightCheck:
    """성공 점검 결과를 만든다."""
    return PreflightCheck(key=key, status="ok", detail=detail)


def _warn(key: str, detail: str) -> PreflightCheck:
    """주의 점검 결과를 만든다."""
    return PreflightCheck(key=key, status="warn", detail=detail)


def _fail(key: str, detail: str) -> PreflightCheck:
    """실패 점검 결과를 만든다."""
    return PreflightCheck(key=key, status="fail", detail=detail)


def build_env_checks(settings: AppSettings) -> list[PreflightCheck]:
    """필수 환경변수의 설정 여부를 점검한다."""
    env_pairs = [
        ("env.supabase_url", settings.auth.supabase_url),
        ("env.supabase_anon_key", settings.auth.supabase_anon_key),
        ("env.supabase_jwt_secret", settings.auth.supabase_jwt_secret),
        ("env.supabase_service_role_key", settings.auth.supabase_service_role_key),
        ("env.polar_access_token", settings.billing.polar_access_token),
        ("env.polar_webhook_secret", settings.billing.polar_webhook_secret),
        ("env.polar_server", settings.billing.polar_server),
        ("env.polar_product_single_id", settings.billing.polar_product_single_id),
        ("env.polar_product_starter_id", settings.billing.polar_product_starter_id),
        ("env.polar_product_pro_id", settings.billing.polar_product_pro_id),
    ]
    checks: list[PreflightCheck] = []
    for key, value in env_pairs:
        if not value:
            checks.append(_fail(key, "값이 비어 있습니다. .env를 채워야 합니다."))
            continue

        if key == "env.polar_server" and value != "sandbox":
            checks.append(_fail(key, "이 단계는 sandbox 검증이므로 POLAR_SERVER=sandbox 로 맞춰야 합니다."))
            continue

        checks.append(_ok(key, "설정됨"))
    return checks


def check_supabase_payment_columns(
    supabase_url: str,
    service_role_key: str,
    requester: Requester = requests.get,
) -> PreflightCheck:
    """payment_events의 Polar 전환 컬럼이 노출되는지 점검한다."""
    try:
        response = requester(
            f"{supabase_url.rstrip('/')}/rest/v1/payment_events",
            headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
            },
            params={
                "select": "provider,provider_event_id,provider_order_id,provider_checkout_id,provider_customer_id,currency",
                "limit": "1",
            },
            timeout=15,
        )
    except Exception as error:
        return _fail("supabase.payment_events_columns", f"REST 확인 실패: {error}")

    if response.status_code == 200:
        return _ok("supabase.payment_events_columns", "Polar billing 컬럼 조회가 가능합니다.")

    return _fail(
        "supabase.payment_events_columns",
        "payment_events Polar 컬럼 확인에 실패했습니다. 2026-03-16_polar_billing_upgrade.sql 적용 여부를 점검하세요.",
    )


def check_billing_catalog(api_base_url: str, requester: Requester = requests.get) -> PreflightCheck:
    """로컬 백엔드의 billing catalog 응답을 점검한다."""
    try:
        response = requester(f"{api_base_url.rstrip('/')}/billing/catalog", timeout=15)
    except Exception as error:
        return _fail("api.billing_catalog", f"catalog 호출 실패: {error}")

    if response.status_code != 200:
        return _fail("api.billing_catalog", f"catalog HTTP {response.status_code}: {response.text}")

    payload = response.json()
    plans = payload.get("plans") if isinstance(payload, dict) else None
    if not isinstance(plans, list) or len(plans) != 3:
        return _fail("api.billing_catalog", "3개 플랜 응답이 아니어서 Polar 상품 매핑을 다시 확인해야 합니다.")

    return _ok("api.billing_catalog", "billing catalog가 3개 플랜으로 응답합니다.")


def _check_tunnel_tool(which: WhichLookup) -> PreflightCheck:
    """터널 도구가 준비되었는지 점검한다."""
    ngrok_path = which("ngrok")
    polar_path = which("polar")
    cloudflared_path = which("cloudflared")
    if ngrok_path:
        return _ok("tool.tunnel", f"ngrok 사용 가능: {ngrok_path}")
    if polar_path:
        return _ok("tool.tunnel", f"polar CLI 사용 가능: {polar_path}")
    if cloudflared_path:
        return _ok("tool.tunnel", f"cloudflared 사용 가능: {cloudflared_path}")
    return _warn("tool.tunnel", "ngrok, polar CLI, cloudflared가 없습니다. ngrok 또는 polar CLI 준비를 권장합니다.")


def collect_preflight_checks(
    *,
    settings: AppSettings | None = None,
    root_path: Path | None = None,
    requester: Requester = requests.get,
    which: WhichLookup = shutil.which,
    api_base_url: str | None = None,
) -> list[PreflightCheck]:
    """환경, 도구, Supabase, 로컬 API 점검 결과를 한 번에 모은다."""
    resolved_settings = settings or get_settings(root_path or ROOT)
    checks = build_env_checks(resolved_settings)
    checks.append(_check_tunnel_tool(which))

    if resolved_settings.auth.supabase_url and resolved_settings.auth.supabase_service_role_key:
        checks.append(
            check_supabase_payment_columns(
                resolved_settings.auth.supabase_url,
                resolved_settings.auth.supabase_service_role_key,
                requester=requester,
            )
        )
    else:
        checks.append(_warn("supabase.payment_events_columns", "Supabase 연결 정보가 없어서 컬럼 점검을 건너뜁니다."))

    if api_base_url:
        checks.append(check_billing_catalog(api_base_url, requester=requester))

    return checks


def build_next_steps(checks: list[PreflightCheck]) -> list[str]:
    """실패/경고 결과를 기준으로 사용자 다음 작업을 만든다."""
    status_by_key = {check.key: check.status for check in checks}
    steps: list[str] = []

    if any(
        status_by_key.get(key) == "fail"
        for key in ("env.supabase_service_role_key", "env.supabase_jwt_secret")
    ):
        steps.append("Supabase Dashboard에서 SUPABASE_SERVICE_ROLE_KEY 와 SUPABASE_JWT_SECRET 값을 채웁니다.")

    if status_by_key.get("supabase.payment_events_columns") == "fail":
        steps.append("Supabase SQL Editor에서 2026-03-16_polar_billing_upgrade.sql 을 적용합니다.")

    if any(
        status_by_key.get(key) == "fail"
        for key in (
            "env.polar_access_token",
            "env.polar_webhook_secret",
            "env.polar_product_single_id",
            "env.polar_product_starter_id",
            "env.polar_product_pro_id",
        )
    ):
        steps.append("https://sandbox.polar.sh 에 로그인하고 sandbox 전용 Access Token, 상품 3개, webhook secret을 준비합니다.")

    if status_by_key.get("tool.tunnel") == "warn":
        steps.append("ngrok, polar CLI, cloudflared 중 하나를 준비해 localhost:8000 을 외부 HTTPS로 노출합니다.")

    if not steps:
        steps.append("로컬 백엔드를 실행한 뒤 py scripts/polar_sandbox_preflight.py --api-base-url http://localhost:8000 로 API까지 확인합니다.")

    return steps


def has_blocking_failures(checks: list[PreflightCheck]) -> bool:
    """즉시 막히는 실패 항목이 있는지 확인한다."""
    return any(check.status == "fail" for check in checks)
