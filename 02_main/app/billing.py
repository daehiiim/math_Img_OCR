from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from polar_sdk import Polar, models as polar_models
from standardwebhooks.webhooks import Webhook, WebhookVerificationError

from app.auth import AuthenticatedUser
from app.config import get_settings
from app.supabase import SupabaseApiError, SupabaseClient, SupabaseConfig

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BillingPlan:
    plan_id: str
    product_id: str
    title: str
    amount: int
    currency: str
    credits: int


@dataclass(frozen=True)
class BillingProfile:
    user_id: str
    credits_balance: int
    used_credits: int
    openai_connected: bool
    openai_key_masked: str | None


class PolarGatewayProtocol(Protocol):
    """Polar 통신 계층 계약이다."""

    def get_product(self, product_id: str) -> dict: ...

    def create_checkout(
        self,
        *,
        external_customer_id: str,
        plan: BillingPlan,
        success_url: str,
        cancel_url: str | None,
    ) -> dict: ...

    def get_checkout(self, checkout_id: str) -> dict: ...

    def create_customer_session(self, customer_id: str, return_url: str | None = None) -> dict: ...

    def verify_event(self, payload: bytes, headers: dict[str, str]) -> dict: ...


class BillingStoreProtocol(Protocol):
    """Billing 영속화 계층 계약이다."""

    def get_or_create_profile(self, user: AuthenticatedUser) -> BillingProfile: ...

    def has_payment_event(self, provider: str, provider_event_id: str) -> bool: ...

    def has_recorded_order(self, provider: str, provider_order_id: str) -> bool: ...

    def find_payment_event_by_checkout_id(self, provider: str, checkout_id: str) -> dict | None: ...

    def find_customer_id_for_user(self, provider: str, user_id: str) -> str | None: ...

    def record_completed_payment(
        self,
        *,
        provider: str,
        provider_event_id: str,
        provider_order_id: str,
        provider_checkout_id: str | None,
        provider_customer_id: str,
        user_id: str,
        plan: BillingPlan,
        amount: int,
        currency: str,
        invoice_number: str | None,
        invoice_url: str | None,
        raw_payload: dict,
    ) -> dict: ...

    def consume_job_credit(self, user: AuthenticatedUser, job_id: str) -> dict: ...


def _build_polar_webhook_verifier(webhook_secret: str | None) -> Webhook | None:
    """Polar secret을 SDK 규칙대로 인코딩해 표준 검증기를 만든다."""
    secret = str(webhook_secret or "").strip()
    if not secret:
        return None
    encoded_secret = base64.b64encode(secret.encode("utf-8")).decode("utf-8")
    return Webhook(encoded_secret)


def _normalize_text(value: Any, field_name: str) -> str:
    """문자열 필드를 검증 가능한 텍스트로 정규화한다."""
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing {field_name}")
    return text


def _normalize_optional_text(value: Any) -> str | None:
    """선택 문자열 필드를 공백 제거 후 반환한다."""
    text = str(value or "").strip()
    return text or None


def _normalize_int(value: Any, field_name: str) -> int:
    """정수 필드를 안전하게 변환한다."""
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {field_name}") from error


def _read_price(product: Any) -> tuple[int, str]:
    """Polar product에서 첫 번째 고정 가격을 읽어온다."""
    prices = getattr(product, "prices", None) or []
    for price in prices:
        amount = getattr(price, "price_amount", None)
        currency = getattr(price, "price_currency", None)
        if amount is not None and currency:
            return int(amount), str(getattr(currency, "value", currency)).lower()
    raise ValueError("product price is missing")


def _read_product_metadata(product: Any) -> dict[str, Any]:
    """Polar product metadata를 일반 dict로 바꾼다."""
    metadata = getattr(product, "metadata", None) or {}
    if isinstance(metadata, dict):
        return metadata
    return dict(metadata)


def _map_product_to_plan(plan_id: str, product_id: str, product: dict) -> BillingPlan:
    """Polar product 응답을 애플리케이션 결제 플랜으로 변환한다."""
    metadata = product.get("metadata") or {}
    actual_plan_id = _normalize_text(metadata.get("plan_id"), "plan_id metadata")
    if actual_plan_id != plan_id:
        raise ValueError("polar product metadata plan_id mismatch")
    prices = product.get("prices") or []
    first_price = prices[0] if prices else {}
    amount = product.get("amount", first_price.get("price_amount"))
    currency = product.get("currency", first_price.get("price_currency"))
    return BillingPlan(
        plan_id=actual_plan_id,
        product_id=product_id,
        title=_normalize_text(product.get("title") or product.get("name"), "product title"),
        amount=_normalize_int(amount, "product amount"),
        currency=_normalize_text(currency, "product currency").lower(),
        credits=_normalize_int(metadata.get("credits"), "credits metadata"),
    )


class PolarGateway:
    """Polar SDK와 표준 webhook 검증기를 감싼다."""

    def __init__(self, access_token: str, webhook_secret: str | None, server: str | None) -> None:
        self._client = Polar(access_token=access_token, server=(server or "production"))
        self._webhook = _build_polar_webhook_verifier(webhook_secret)

    def get_product(self, product_id: str) -> dict:
        """Polar product를 읽어 앱이 쓰기 쉬운 형태로 바꾼다."""
        try:
            product = self._client.products.get(id=product_id)
        except polar_models.SDKError as error:
            raise ValueError(f"Polar product lookup failed: {error}") from error

        amount, currency = _read_price(product)
        return {
            "id": product.id,
            "title": product.name,
            "amount": amount,
            "currency": currency,
            "metadata": _read_product_metadata(product),
        }

    def create_checkout(
        self,
        *,
        external_customer_id: str,
        plan: BillingPlan,
        success_url: str,
        cancel_url: str | None,
    ) -> dict:
        """Polar hosted checkout 세션을 생성한다."""
        request = polar_models.CheckoutCreate(
            products=[plan.product_id],
            external_customer_id=external_customer_id,
            customer_metadata={"user_id": external_customer_id},
            metadata={"plan_id": plan.plan_id, "credits": plan.credits},
            success_url=success_url,
            return_url=cancel_url,
            allow_discount_codes=False,
        )
        try:
            checkout = self._client.checkouts.create(request=request)
        except polar_models.SDKError as error:
            raise ValueError(f"Polar checkout creation failed: {error}") from error

        return {
            "id": checkout.id,
            "url": checkout.url,
            "status": str(getattr(checkout.status, "value", checkout.status)).lower(),
        }

    def get_checkout(self, checkout_id: str) -> dict:
        """Polar checkout 상태를 조회한다."""
        try:
            checkout = self._client.checkouts.get(id=checkout_id)
        except polar_models.SDKError as error:
            raise ValueError(f"Polar checkout lookup failed: {error}") from error

        return {
            "id": checkout.id,
            "status": str(getattr(checkout.status, "value", checkout.status)).lower(),
        }

    def create_customer_session(self, customer_id: str, return_url: str | None = None) -> dict:
        """Polar customer portal 세션을 생성한다."""
        request: dict[str, str] = {"customer_id": customer_id}
        if return_url:
            request["return_url"] = return_url

        try:
            session = self._client.customer_sessions.create(request=request)
        except polar_models.SDKError as error:
            raise ValueError(f"Polar customer session creation failed: {error}") from error

        return {"customer_portal_url": session.customer_portal_url}

    def verify_event(self, payload: bytes, headers: dict[str, str]) -> dict:
        """표준 webhook 서명을 검증하고 이벤트 JSON을 반환한다."""
        if self._webhook is None:
            raise ValueError("POLAR_WEBHOOK_SECRET is not configured")

        try:
            event = self._webhook.verify(payload, headers)
        except WebhookVerificationError as error:
            raise ValueError(f"invalid polar webhook: {error}") from error

        if isinstance(event, dict):
            event["_event_id"] = headers.get("webhook-id")
        return event


class SupabaseBillingStore:
    """Profiles, payment_events, credit_ledger를 Supabase에 저장한다."""

    def __init__(self, root_path: Path) -> None:
        settings = get_settings(root_path)
        if not settings.auth.supabase_url or not settings.auth.supabase_anon_key:
            raise ValueError("Supabase settings are not configured")

        self._config = SupabaseConfig(
            url=settings.auth.supabase_url,
            anon_key=settings.auth.supabase_anon_key,
            storage_bucket=settings.auth.supabase_storage_bucket or "ocr-assets",
        )
        self._service_role_key = settings.auth.supabase_service_role_key

    def _user_client(self, user: AuthenticatedUser) -> SupabaseClient:
        """사용자 JWT가 붙은 Supabase 클라이언트를 만든다."""
        return SupabaseClient(self._config, user.access_token)

    def _admin_client(self) -> SupabaseClient:
        """Service role 권한의 Supabase 클라이언트를 만든다."""
        if not self._service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for billing webhooks")
        return SupabaseClient(
            self._config,
            access_token=self._service_role_key,
            api_key=self._service_role_key,
        )

    def _map_profile(self, row: dict) -> BillingProfile:
        """profiles row를 BillingProfile로 변환한다."""
        return BillingProfile(
            user_id=str(row["user_id"]),
            credits_balance=int(row.get("credits_balance") or 0),
            used_credits=int(row.get("used_credits") or 0),
            openai_connected=bool(row.get("openai_connected") or False),
            openai_key_masked=row.get("openai_key_masked"),
        )

    def _read_profile(self, client: SupabaseClient, user_id: str) -> BillingProfile | None:
        """profiles row를 읽어 BillingProfile로 바꾼다."""
        rows = client.select(
            "profiles",
            params={
                "select": "user_id,credits_balance,used_credits,openai_connected,openai_key_masked",
                "user_id": f"eq.{user_id}",
            },
        )
        return self._map_profile(rows[0]) if rows else None

    def _ensure_profile(self, client: SupabaseClient, user_id: str) -> BillingProfile:
        """profile이 없으면 기본 row를 만든다."""
        profile = self._read_profile(client, user_id)
        if profile is not None:
            return profile

        inserted = client.insert(
            "profiles",
            {
                "user_id": user_id,
                "display_name": user_id[:8],
                "credits_balance": 0,
                "used_credits": 0,
                "openai_connected": False,
                "openai_key_masked": None,
            },
        )
        return self._map_profile(inserted[0])

    def get_or_create_profile(self, user: AuthenticatedUser) -> BillingProfile:
        """사용자 profile을 읽고 없으면 기본 row를 만든다."""
        return self._ensure_profile(self._user_client(user), user.user_id)

    def has_payment_event(self, provider: str, provider_event_id: str) -> bool:
        """동일 provider event가 이미 처리되었는지 확인한다."""
        rows = self._admin_client().select(
            "payment_events",
            params={
                "select": "id",
                "provider": f"eq.{provider}",
                "provider_event_id": f"eq.{provider_event_id}",
            },
        )
        return bool(rows)

    def has_recorded_order(self, provider: str, provider_order_id: str) -> bool:
        """동일 provider order가 이미 처리되었는지 확인한다."""
        rows = self._admin_client().select(
            "payment_events",
            params={
                "select": "id",
                "provider": f"eq.{provider}",
                "provider_order_id": f"eq.{provider_order_id}",
            },
        )
        return bool(rows)

    def find_payment_event_by_checkout_id(self, provider: str, checkout_id: str) -> dict | None:
        """checkout ID로 적립 완료 이벤트를 찾는다."""
        rows = self._admin_client().select(
            "payment_events",
            params={
                "select": "id,provider_order_id,provider_customer_id,credits_added",
                "provider": f"eq.{provider}",
                "provider_checkout_id": f"eq.{checkout_id}",
                "status": "eq.completed",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def find_customer_id_for_user(self, provider: str, user_id: str) -> str | None:
        """사용자의 최근 provider customer ID를 찾는다."""
        rows = self._admin_client().select(
            "payment_events",
            params={
                "select": "provider_customer_id",
                "provider": f"eq.{provider}",
                "user_id": f"eq.{user_id}",
                "provider_customer_id": "not.is.null",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        return _normalize_optional_text(rows[0].get("provider_customer_id")) if rows else None

    def record_completed_payment(
        self,
        *,
        provider: str,
        provider_event_id: str,
        provider_order_id: str,
        provider_checkout_id: str | None,
        provider_customer_id: str,
        user_id: str,
        plan: BillingPlan,
        amount: int,
        currency: str,
        invoice_number: str | None,
        invoice_url: str | None,
        raw_payload: dict,
    ) -> dict:
        """결제 이벤트, profile balance, ledger를 일관되게 적재한다."""
        client = self._admin_client()
        profile = self._ensure_profile(client, user_id)
        try:
            event_rows = client.insert(
                "payment_events",
                {
                    "user_id": user_id,
                    "provider": provider,
                    "provider_event_id": provider_event_id,
                    "provider_order_id": provider_order_id,
                    "provider_checkout_id": provider_checkout_id,
                    "provider_customer_id": provider_customer_id,
                    "plan_id": plan.plan_id,
                    "credits_added": plan.credits,
                    "amount": amount,
                    "currency": currency,
                    "invoice_number": invoice_number,
                    "invoice_url": invoice_url,
                    "status": "completed",
                    "raw_payload": raw_payload,
                },
            )
        except SupabaseApiError as error:
            message = str(error).lower()
            if "duplicate key value" not in message and "23505" not in message:
                raise
            current_profile = self._ensure_profile(client, user_id)
            return {
                "credits_balance": current_profile.credits_balance,
                "credits_added": 0,
                "duplicate": True,
            }
        payment_event_id = str(event_rows[0]["id"])
        new_balance = profile.credits_balance + plan.credits
        client.update(
            "profiles",
            filters={"user_id": f"eq.{user_id}"},
            payload={"credits_balance": new_balance},
        )
        client.insert(
            "credit_ledger",
            {
                "user_id": user_id,
                "payment_event_id": payment_event_id,
                "delta": plan.credits,
                "balance_after": new_balance,
                "reason": "purchase",
            },
        )
        return {"credits_balance": new_balance, "credits_added": plan.credits}

    def consume_job_credit(self, user: AuthenticatedUser, job_id: str) -> dict:
        """성공한 OCR job 1건에 대해 크레딧 1개를 차감한다."""
        client = self._user_client(user)
        job_rows = client.select(
            "ocr_jobs",
            params={
                "select": "id,was_charged,processing_type,status",
                "id": f"eq.{job_id}",
            },
        )
        if not job_rows:
            raise FileNotFoundError(f"job not found: {job_id}")

        job_row = job_rows[0]
        if bool(job_row.get("was_charged")) or job_row.get("processing_type") == "user_api_key":
            profile = self.get_or_create_profile(user)
            return {"charged": False, "credits_balance": profile.credits_balance}
        if job_row.get("status") not in ("completed", "exported"):
            raise ValueError("job is not eligible for charging")

        profile = self.get_or_create_profile(user)
        if profile.credits_balance <= 0:
            raise ValueError("insufficient credits")

        new_balance = profile.credits_balance - 1
        client.update(
            "profiles",
            filters={"user_id": f"eq.{user.user_id}"},
            payload={
                "credits_balance": new_balance,
                "used_credits": profile.used_credits + 1,
            },
        )
        client.insert(
            "credit_ledger",
            {
                "user_id": user.user_id,
                "job_id": job_id,
                "delta": -1,
                "balance_after": new_balance,
                "reason": "ocr_success_charge",
            },
        )
        client.update(
            "ocr_jobs",
            filters={"id": f"eq.{job_id}"},
            payload={
                "was_charged": True,
                "charged_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            },
        )
        return {"charged": True, "credits_balance": new_balance}


class BillingService:
    """Checkout, catalog, webhook 적재를 담당한다."""

    def __init__(
        self,
        store: BillingStoreProtocol,
        polar_gateway: PolarGatewayProtocol | None,
        plan_product_ids: dict[str, str],
    ) -> None:
        self._store = store
        self._polar_gateway = polar_gateway
        self._plan_product_ids = plan_product_ids

    def _require_polar_gateway(self) -> PolarGatewayProtocol:
        """Polar 기능이 필요한 경로에서 gateway 존재를 보장한다."""
        if self._polar_gateway is None:
            raise ValueError("Polar gateway is not configured")
        return self._polar_gateway

    def _load_plan(self, plan_id: str) -> BillingPlan:
        """Polar product metadata를 읽어 앱 결제 플랜을 만든다."""
        product_id = self._plan_product_ids.get(plan_id)
        if not product_id:
            raise ValueError("unsupported billing plan")
        product = self._require_polar_gateway().get_product(product_id)
        return _map_product_to_plan(plan_id, product_id, product)

    def list_plans(self) -> list[dict]:
        """허용된 Polar 상품 3개를 가격표 응답으로 반환한다."""
        plans = [self._load_plan(plan_id) for plan_id in ("single", "starter", "pro")]
        return [
            {
                "plan_id": plan.plan_id,
                "title": plan.title,
                "amount": plan.amount,
                "currency": plan.currency,
                "credits": plan.credits,
            }
            for plan in plans
        ]

    def create_checkout(
        self,
        user: AuthenticatedUser,
        *,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        """사용자와 플랜 기준으로 Polar checkout 세션을 생성한다."""
        plan = self._load_plan(plan_id)
        checkout = self._require_polar_gateway().create_checkout(
            external_customer_id=user.user_id,
            plan=plan,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {
            "checkout_id": checkout["id"],
            "checkout_url": checkout["url"],
            "plan_id": plan.plan_id,
            "credits": plan.credits,
            "amount": plan.amount,
            "currency": plan.currency,
        }

    def get_profile(self, user: AuthenticatedUser) -> BillingProfile:
        """현재 사용자 profile을 반환한다."""
        return self._store.get_or_create_profile(user)

    def get_checkout(self, checkout_id: str) -> dict:
        """Polar checkout 상태와 내부 적립 여부를 같이 반환한다."""
        checkout = self._require_polar_gateway().get_checkout(checkout_id)
        payment_event = self._store.find_payment_event_by_checkout_id("polar", checkout_id)
        return {
            "checkout_id": checkout["id"],
            "status": checkout["status"],
            "credits_applied": payment_event is not None,
        }

    def create_customer_portal(self, user: AuthenticatedUser, return_url: str | None = None) -> dict:
        """최근 결제 고객 ID 기준으로 Polar customer portal URL을 만든다."""
        customer_id = self._store.find_customer_id_for_user("polar", user.user_id)
        if not customer_id:
            raise ValueError("customer portal is not available yet")
        return self._require_polar_gateway().create_customer_session(customer_id, return_url=return_url)

    def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> dict:
        """Polar webhook payload를 검증한다."""
        return self._require_polar_gateway().verify_event(payload, headers)

    def apply_webhook_event(self, event: dict) -> dict:
        """완료된 주문 이벤트를 idempotent 하게 적립 처리한다."""
        if event.get("type") != "order.paid":
            return {"handled": False, "duplicate": False}

        provider_event_id = _normalize_text(event.get("_event_id") or event.get("id"), "provider event id")
        if self._store.has_payment_event("polar", provider_event_id):
            return {"handled": True, "duplicate": True}

        order = event.get("data") or {}
        provider_order_id = _normalize_text(order.get("id"), "order id")
        if self._store.has_recorded_order("polar", provider_order_id):
            return {"handled": True, "duplicate": True}

        customer = order.get("customer") or {}
        product = order.get("product") or {}
        metadata = product.get("metadata") or {}
        plan_id = _normalize_text(metadata.get("plan_id"), "plan_id")
        prices = product.get("prices") or []
        first_price = prices[0] if prices else {}
        amount = order.get("total_amount") or order.get("amount") or first_price.get("price_amount")
        currency = order.get("currency") or first_price.get("price_currency")
        user_id = _normalize_text(customer.get("external_id") or order.get("metadata", {}).get("user_id"), "user_id")
        plan = BillingPlan(
            plan_id=plan_id,
            product_id=_normalize_optional_text(product.get("id")) or _normalize_text(self._plan_product_ids.get(plan_id), "product id"),
            title=_normalize_text(product.get("name") or product.get("title"), "product title"),
            amount=_normalize_int(amount, "order amount"),
            currency=_normalize_text(currency, "order currency").lower(),
            credits=_normalize_int(metadata.get("credits"), "credits"),
        )
        result = self._store.record_completed_payment(
            provider="polar",
            provider_event_id=provider_event_id,
            provider_order_id=provider_order_id,
            provider_checkout_id=_normalize_optional_text(order.get("checkout_id")),
            provider_customer_id=_normalize_text(customer.get("id"), "customer id"),
            user_id=user_id,
            plan=plan,
            amount=plan.amount,
            currency=plan.currency,
            invoice_number=_normalize_optional_text(order.get("invoice_number")),
            invoice_url=_normalize_optional_text(order.get("invoice_url")),
            raw_payload=event,
        )
        if result.get("duplicate"):
            return {"handled": True, "duplicate": True, **result}
        return {"handled": True, "duplicate": False, **result}

    def consume_job_credit(self, user: AuthenticatedUser, job_id: str) -> dict:
        """성공한 OCR job에 대한 1회 차감을 수행한다."""
        return self._store.consume_job_credit(user, job_id)


def build_billing_service(root_path: Path | None = None, require_polar: bool = False) -> BillingService:
    """환경설정 기반 기본 BillingService를 만든다."""
    settings = get_settings(root_path or ROOT)
    product_ids = {
        "single": _normalize_optional_text(settings.billing.polar_product_single_id) or "",
        "starter": _normalize_optional_text(settings.billing.polar_product_starter_id) or "",
        "pro": _normalize_optional_text(settings.billing.polar_product_pro_id) or "",
    }
    if require_polar:
        if not settings.billing.polar_access_token:
            raise ValueError("POLAR_ACCESS_TOKEN is not configured")
        missing = [plan_id for plan_id, product_id in product_ids.items() if not product_id]
        if missing:
            raise ValueError(f"missing Polar product ids: {', '.join(missing)}")

    gateway = None
    if settings.billing.polar_access_token:
        gateway = PolarGateway(
            access_token=settings.billing.polar_access_token,
            webhook_secret=settings.billing.polar_webhook_secret,
            server=settings.billing.polar_server,
        )

    return BillingService(
        store=SupabaseBillingStore(root_path or ROOT),
        polar_gateway=gateway,
        plan_product_ids=product_ids,
    )
