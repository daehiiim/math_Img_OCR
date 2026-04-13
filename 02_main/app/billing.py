from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from cryptography.fernet import Fernet
from polar_sdk import Polar, models as polar_models
from standardwebhooks.webhooks import Webhook, WebhookVerificationError

from app.auth import AuthenticatedUser
from app.config import get_settings
from app.schema_compat import (
    is_markdown_output_schema_error,
    remember_markdown_output_columns_available,
    should_use_markdown_output_columns,
)
from app.supabase import SupabaseApiError, SupabaseClient, SupabaseConfig

ROOT = Path(__file__).resolve().parents[1]
OPENAI_KEY_ENCRYPTION_SECRET_MISSING = "OPENAI_KEY_ENCRYPTION_SECRET is not configured"
POLAR_ACCESS_TOKEN_MISSING = "POLAR_ACCESS_TOKEN is not configured"
POLAR_SERVER_LIVE_BILLING_REQUIRED = "POLAR_SERVER must be production for live billing"
POLAR_ACCESS_TOKEN_SERVER_MISMATCH = "POLAR_ACCESS_TOKEN does not match POLAR_SERVER"
POLAR_PRODUCT_PRICE_MISSING = "missing product price"
POLAR_PRODUCT_CURRENCY_MISMATCH = "product currency mismatch"
POLAR_PRODUCT_ID_MISMATCH = "configured Polar product id mismatch"
POLAR_REQUIRED_CURRENCY = "krw"
POLAR_DEFAULT_BILLING_COUNTRY = "KR"
SIGNUP_BONUS_CREDITS = 3
SIGNUP_BONUS_REASON = "signup_bonus"
AUTO_DETECT_CHARGE_REASON = "auto_detect_charge"
CHECKOUT_ADDRESS_FIELDS = ("country", "line1", "line2", "postal_code", "city", "state")
CHECKOUT_BILLING_FIELD_NAMES = ("country", "state", "city", "postal_code", "line1", "line2")
JOB_ACTION_REASON_MAP = {
    "ocr": "ocr_charge",
    "image_stylize": "image_stylize_charge",
    "explanation": "explanation_charge",
}
JOB_ACTION_FLAG_MAP = {
    "ocr": "ocr_charged",
    "image_stylize": "image_charged",
    "explanation": "explanation_charged",
}
FREE_USER_KEY_ACTIONS = {"ocr", "explanation"}
_JOB_ACTION_CHARGE_BASE_SELECT_COLUMNS = (
    "region_key",
    "ocr_text",
    "mathml",
    "explanation",
    "styled_image_path",
    "ocr_charged",
    "image_charged",
    "explanation_charged",
)
_JOB_ACTION_CHARGE_MARKDOWN_COLUMNS = (
    "problem_markdown",
    "explanation_markdown",
)


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


@dataclass(frozen=True)
class StoredOpenAiKey:
    encrypted_api_key: str
    key_last4: str
    is_active: bool


@dataclass(frozen=True)
class ResolvedOpenAiApiKey:
    api_key: str
    processing_type: Literal["user_api_key", "service_api"]


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

    def upsert_openai_key(
        self,
        user: AuthenticatedUser,
        *,
        encrypted_api_key: str,
        key_last4: str,
        masked_key: str,
    ) -> BillingProfile: ...

    def deactivate_openai_key(self, user: AuthenticatedUser) -> BillingProfile: ...

    def get_active_openai_key(self, user: AuthenticatedUser) -> StoredOpenAiKey | None: ...

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

    def ensure_job_auto_detect_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict: ...

    def consume_job_auto_detect_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict: ...

    def ensure_job_region_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict: ...

    def consume_job_region_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict: ...

    def ensure_job_action_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict: ...

    def consume_job_action_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict: ...


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


def _normalize_checkout_value(value: Any) -> Any:
    """Polar checkout 필드를 직렬화 가능한 기본값으로 바꾼다."""
    value_type_name = type(value).__name__
    if value is None or value_type_name in {"Unset", "PydanticUndefinedType"}:
        return None
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return enum_value
    return value


def _normalize_int(value: Any, field_name: str) -> int:
    """정수 필드를 안전하게 변환한다."""
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {field_name}") from error


def _build_job_action_charge_select(include_markdown_output: bool) -> str:
    """과금 점검용 region 조회 컬럼 목록을 스키마 수준에 맞게 만든다."""
    columns = list(_JOB_ACTION_CHARGE_BASE_SELECT_COLUMNS)
    if include_markdown_output:
        columns[3:3] = list(_JOB_ACTION_CHARGE_MARKDOWN_COLUMNS)
    return ",".join(columns)


def _validate_openai_api_key(api_key: str) -> str:
    """OpenAI API key 형식을 최소 기준으로 검증한다."""
    normalized = str(api_key or "").strip()
    if not normalized.startswith("sk-") or len(normalized) < 12:
        raise ValueError("invalid OpenAI API key format")
    return normalized


def _mask_openai_api_key(api_key: str) -> str:
    """UI와 profile에 저장할 마스킹 문자열을 만든다."""
    normalized = _validate_openai_api_key(api_key)
    return f"{normalized[:5]}••••{normalized[-4:]}"


def _build_openai_key_cipher(secret: str | None) -> Fernet:
    """환경 비밀값으로 Fernet 암호화기를 만든다."""
    normalized = str(secret or "").strip()
    if not normalized:
        raise ValueError(OPENAI_KEY_ENCRYPTION_SECRET_MISSING)
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_openai_api_key(secret: str | None, api_key: str) -> str:
    """평문 OpenAI key를 저장 가능한 암호문으로 바꾼다."""
    return _build_openai_key_cipher(secret).encrypt(api_key.encode("utf-8")).decode("utf-8")


def _decrypt_openai_api_key(secret: str | None, encrypted_api_key: str) -> str:
    """암호문 OpenAI key를 실행 시점 평문으로 복원한다."""
    decrypted = _build_openai_key_cipher(secret).decrypt(encrypted_api_key.encode("utf-8"))
    return decrypted.decode("utf-8")


def _read_price(product: Any) -> tuple[int, str]:
    """Polar product에서 첫 번째 고정 가격을 읽어온다."""
    prices = getattr(product, "prices", None) or []
    for price in prices:
        amount = getattr(price, "price_amount", None)
        currency = getattr(price, "price_currency", None)
        if amount is not None and currency:
            return int(amount), str(getattr(currency, "value", currency)).lower()
    raise ValueError(POLAR_PRODUCT_PRICE_MISSING)


def _read_product_metadata(product: Any) -> dict[str, Any]:
    """Polar product metadata를 일반 dict로 바꾼다."""
    metadata = getattr(product, "metadata", None) or {}
    if isinstance(metadata, dict):
        return metadata
    return dict(metadata)


def _read_product_price_fields(
    product: dict[str, Any],
    *,
    amount: Any | None = None,
    currency: Any | None = None,
) -> tuple[Any, Any]:
    """상품 dict에서 금액과 통화 원본 값을 읽는다."""
    prices = product.get("prices") or []
    first_price = prices[0] if prices else {}
    resolved_amount = product.get("amount") if amount is None else amount
    resolved_currency = product.get("currency") if currency is None else currency
    if resolved_amount is None:
        resolved_amount = first_price.get("price_amount")
    if resolved_currency is None or str(resolved_currency).strip() == "":
        resolved_currency = first_price.get("price_currency")
    if resolved_amount is None or resolved_currency is None:
        raise ValueError(POLAR_PRODUCT_PRICE_MISSING)
    return resolved_amount, resolved_currency


def _normalize_product_currency(value: Any) -> str:
    """운영 결제 통화를 KRW로 강제한다."""
    normalized = _normalize_text(value, "product currency").lower()
    if normalized != POLAR_REQUIRED_CURRENCY:
        raise ValueError(POLAR_PRODUCT_CURRENCY_MISMATCH)
    return normalized


def _resolve_billing_product_id(product: dict[str, Any], configured_product_id: str | None) -> str:
    """실제 상품 ID와 설정 상품 ID의 정합성을 검증한다."""
    actual_product_id = _normalize_optional_text(product.get("id"))
    configured_id = _normalize_optional_text(configured_product_id)
    if actual_product_id and configured_id and actual_product_id != configured_id:
        raise ValueError(POLAR_PRODUCT_ID_MISMATCH)
    if actual_product_id:
        return actual_product_id
    return _normalize_text(configured_product_id, "product id")


def build_validated_plan_from_product(
    product: dict[str, Any],
    *,
    expected_plan_id: str,
    configured_product_id: str | None,
    amount: Any | None = None,
    currency: Any | None = None,
) -> BillingPlan:
    """상품 payload를 운영 결제 규칙에 맞는 플랜으로 정규화한다."""
    metadata = product.get("metadata") or {}
    actual_plan_id = _normalize_text(metadata.get("plan_id"), "plan_id metadata")
    if actual_plan_id != expected_plan_id:
        raise ValueError("polar product metadata plan_id mismatch")
    resolved_amount, resolved_currency = _read_product_price_fields(
        product,
        amount=amount,
        currency=currency,
    )
    return BillingPlan(
        plan_id=actual_plan_id,
        product_id=_resolve_billing_product_id(product, configured_product_id),
        title=_normalize_text(product.get("title") or product.get("name"), "product title"),
        amount=_normalize_int(resolved_amount, "product amount"),
        currency=_normalize_product_currency(resolved_currency),
        credits=_normalize_int(metadata.get("credits"), "credits metadata"),
    )


def _normalize_polar_sdk_error(action: str, error: Exception) -> ValueError:
    """Polar SDK 예외를 프런트가 해석할 수 있는 안정적인 문자열로 정규화한다."""
    message = str(error)
    normalized = message.lower()
    if "status 401" in normalized and "invalid_token" in normalized:
        return ValueError(POLAR_ACCESS_TOKEN_SERVER_MISMATCH)
    return ValueError(f"{action}: {message}")


def _build_default_checkout_address() -> polar_models.AddressInput:
    """운영 checkout 기본 청구지 국가를 South Korea로 preset 한다."""
    return polar_models.AddressInput(country=POLAR_DEFAULT_BILLING_COUNTRY)


def _read_checkout_address(value: Any) -> dict[str, Any] | None:
    """checkout 주소 객체를 일반 dict로 정규화한다."""
    if value is None:
        return None
    return {
        field_name: _normalize_checkout_value(getattr(value, field_name, None))
        for field_name in CHECKOUT_ADDRESS_FIELDS
    }


def _read_checkout_billing_fields(value: Any) -> dict[str, Any] | None:
    """checkout 주소 필드 모드를 일반 dict로 정규화한다."""
    if value is None:
        return None
    return {
        field_name: _normalize_checkout_value(getattr(value, field_name, None))
        for field_name in CHECKOUT_BILLING_FIELD_NAMES
    }


def _read_checkout_diagnostics(checkout: Any) -> dict[str, Any]:
    """Polar checkout 응답에서 운영 진단 필드를 읽는다."""
    return {
        "payment_processor": _normalize_checkout_value(getattr(checkout, "payment_processor", None)),
        "is_payment_required": getattr(checkout, "is_payment_required", None),
        "is_payment_form_required": getattr(checkout, "is_payment_form_required", None),
        "customer_billing_address": _read_checkout_address(getattr(checkout, "customer_billing_address", None)),
        "billing_address_fields": _read_checkout_billing_fields(getattr(checkout, "billing_address_fields", None)),
        "currency": _normalize_checkout_value(getattr(checkout, "currency", None)),
        "amount": getattr(checkout, "amount", None),
        "product_id": _normalize_checkout_value(getattr(checkout, "product_id", None)),
        "product_price_id": _normalize_checkout_value(getattr(checkout, "product_price_id", None)),
    }


def _validate_required_polar_settings(
    access_token: str | None,
    server: str | None,
    product_ids: dict[str, str],
) -> None:
    """운영 결제 경로에 필요한 Polar 설정을 사전에 검증한다."""
    if not access_token:
        raise ValueError(POLAR_ACCESS_TOKEN_MISSING)
    if (server or "").strip().lower() != "production":
        raise ValueError(POLAR_SERVER_LIVE_BILLING_REQUIRED)
    missing = [plan_id for plan_id, product_id in product_ids.items() if not product_id]
    if missing:
        raise ValueError(f"missing Polar product ids: {', '.join(missing)}")


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
            raise _normalize_polar_sdk_error("Polar product lookup failed", error) from error

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
            require_billing_address=True,
            customer_billing_address=_build_default_checkout_address(),
        )
        try:
            checkout = self._client.checkouts.create(request=request)
        except polar_models.SDKError as error:
            raise _normalize_polar_sdk_error("Polar checkout creation failed", error) from error

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
            raise _normalize_polar_sdk_error("Polar checkout lookup failed", error) from error

        return {
            "id": checkout.id,
            "status": str(getattr(checkout.status, "value", checkout.status)).lower(),
            **_read_checkout_diagnostics(checkout),
        }

    def create_customer_session(self, customer_id: str, return_url: str | None = None) -> dict:
        """Polar customer portal 세션을 생성한다."""
        request: dict[str, str] = {"customer_id": customer_id}
        if return_url:
            request["return_url"] = return_url

        try:
            session = self._client.customer_sessions.create(request=request)
        except polar_models.SDKError as error:
            raise _normalize_polar_sdk_error("Polar customer session creation failed", error) from error

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

    def _billing_write_client(self) -> SupabaseClient:
        """과금 쓰기 전용 service role 클라이언트를 반환한다."""
        try:
            return self._admin_client()
        except ValueError as error:
            normalized = str(error).lower()
            if "supabase_service_role_key" in normalized:
                raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for billing writes") from error
            raise

    def _map_profile(self, row: dict) -> BillingProfile:
        """profiles row를 BillingProfile로 변환한다."""
        return BillingProfile(
            user_id=str(row["user_id"]),
            credits_balance=int(row.get("credits_balance") or 0),
            used_credits=int(row.get("used_credits") or 0),
            openai_connected=bool(row.get("openai_connected") or False),
            openai_key_masked=row.get("openai_key_masked"),
        )

    def _map_openai_key(self, row: dict) -> StoredOpenAiKey:
        """user_openai_keys row를 도메인 모델로 변환한다."""
        return StoredOpenAiKey(
            encrypted_api_key=str(row.get("encrypted_api_key") or ""),
            key_last4=str(row.get("key_last4") or ""),
            is_active=bool(row.get("is_active") or False),
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

    def _build_default_profile_payload(self, user_id: str) -> dict[str, Any]:
        """신규 사용자 기본 profile payload를 만든다."""
        return {
            "user_id": user_id,
            "display_name": user_id[:8],
            "credits_balance": SIGNUP_BONUS_CREDITS,
            "used_credits": 0,
            "openai_connected": False,
            "openai_key_masked": None,
        }

    def _record_signup_bonus(self, user_id: str) -> None:
        """신규 가입 보너스 적립 이력을 원장에 남긴다."""
        self._billing_write_client().insert(
            "credit_ledger",
            {
                "user_id": user_id,
                "delta": SIGNUP_BONUS_CREDITS,
                "balance_after": SIGNUP_BONUS_CREDITS,
                "reason": SIGNUP_BONUS_REASON,
            },
        )

    def _ensure_profile(self, client: SupabaseClient, user_id: str) -> BillingProfile:
        """profile이 없으면 기본 row를 만든다."""
        profile = self._read_profile(client, user_id)
        if profile is not None:
            return profile

        inserted = client.insert("profiles", self._build_default_profile_payload(user_id))
        self._record_signup_bonus(user_id)
        return self._map_profile(inserted[0])

    def _sync_openai_profile(
        self,
        client: SupabaseClient,
        user_id: str,
        *,
        openai_connected: bool,
        openai_key_masked: str | None,
    ) -> BillingProfile:
        """OpenAI 연결 메타를 profile과 동기화한다."""
        self._ensure_profile(client, user_id)
        updated = client.update(
            "profiles",
            filters={"user_id": f"eq.{user_id}"},
            payload={
                "openai_connected": openai_connected,
                "openai_key_masked": openai_key_masked,
            },
        )
        if updated:
            return self._map_profile(updated[0])
        return self._ensure_profile(client, user_id)

    def get_or_create_profile(self, user: AuthenticatedUser) -> BillingProfile:
        """사용자 profile을 읽고 없으면 기본 row를 만든다."""
        return self._ensure_profile(self._user_client(user), user.user_id)

    def upsert_openai_key(
        self,
        user: AuthenticatedUser,
        *,
        encrypted_api_key: str,
        key_last4: str,
        masked_key: str,
    ) -> BillingProfile:
        """사용자 OpenAI key 암호문을 upsert하고 profile 상태를 갱신한다."""
        client = self._user_client(user)
        client.upsert(
            "user_openai_keys",
            payload=[
                {
                    "user_id": user.user_id,
                    "encrypted_api_key": encrypted_api_key,
                    "key_last4": key_last4,
                    "is_active": True,
                }
            ],
            on_conflict="user_id",
        )
        return self._sync_openai_profile(
            client,
            user.user_id,
            openai_connected=True,
            openai_key_masked=masked_key,
        )

    def deactivate_openai_key(self, user: AuthenticatedUser) -> BillingProfile:
        """사용자 OpenAI key를 비활성화하고 profile 상태를 정리한다."""
        client = self._user_client(user)
        client.update(
            "user_openai_keys",
            filters={"user_id": f"eq.{user.user_id}"},
            payload={"is_active": False},
        )
        return self._sync_openai_profile(
            client,
            user.user_id,
            openai_connected=False,
            openai_key_masked=None,
        )

    def get_active_openai_key(self, user: AuthenticatedUser) -> StoredOpenAiKey | None:
        """활성 사용자 OpenAI key row를 읽는다."""
        rows = self._user_client(user).select(
            "user_openai_keys",
            params={
                "select": "encrypted_api_key,key_last4,is_active",
                "user_id": f"eq.{user.user_id}",
                "is_active": "eq.true",
                "limit": "1",
            },
        )
        return self._map_openai_key(rows[0]) if rows else None

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
        admin_client = self._billing_write_client()
        admin_client.update(
            "profiles",
            filters={"user_id": f"eq.{user.user_id}"},
            payload={
                "credits_balance": new_balance,
                "used_credits": profile.used_credits + 1,
            },
        )
        admin_client.insert(
            "credit_ledger",
            {
                "user_id": user.user_id,
                "job_id": job_id,
                "delta": -1,
                "balance_after": new_balance,
                "reason": "ocr_success_charge",
            },
        )
        admin_client.update(
            "ocr_jobs",
            filters={"id": f"eq.{job_id}"},
            payload={
                "was_charged": True,
                "charged_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            },
        )
        return {"charged": True, "credits_balance": new_balance}

    def _read_job_auto_detect_charge_state(self, client: SupabaseClient, job_id: str) -> dict[str, Any]:
        """자동 분할 1회 과금 여부를 확인하기 위한 job 상태를 읽는다."""
        rows = client.select(
            "ocr_jobs",
            params={
                "select": "id,auto_detect_charged,auto_detect_charged_at",
                "id": f"eq.{job_id}",
            },
        )
        if not rows:
            raise FileNotFoundError(f"job not found: {job_id}")
        return rows[0]

    def ensure_job_auto_detect_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict:
        """자동 분할을 실행하기 전에 1회 차감 여지가 있는지 점검한다."""
        client = self._user_client(user)
        job_row = self._read_job_auto_detect_charge_state(client, job_id)
        profile = self.get_or_create_profile(user)
        required_credits = 0 if bool(job_row.get("auto_detect_charged")) else 1
        if profile.credits_balance < required_credits:
            raise ValueError("insufficient credits")
        return {
            "required_credits": required_credits,
            "credits_balance": profile.credits_balance,
        }

    def consume_job_auto_detect_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict:
        """자동 분할이 처음 성공했을 때만 job당 1크레딧을 차감한다."""
        client = self._user_client(user)
        job_row = self._read_job_auto_detect_charge_state(client, job_id)
        profile = self.get_or_create_profile(user)
        if bool(job_row.get("auto_detect_charged")):
            return {"charged": False, "charged_count": 0, "credits_balance": profile.credits_balance}
        if profile.credits_balance <= 0:
            raise ValueError("insufficient credits")

        new_balance = profile.credits_balance - 1
        charged_at = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
        admin_client = self._billing_write_client()
        admin_client.update(
            "profiles",
            filters={"user_id": f"eq.{user.user_id}"},
            payload={
                "credits_balance": new_balance,
                "used_credits": profile.used_credits + 1,
            },
        )
        admin_client.insert(
            "credit_ledger",
            {
                "user_id": user.user_id,
                "job_id": job_id,
                "delta": -1,
                "balance_after": new_balance,
                "reason": AUTO_DETECT_CHARGE_REASON,
            },
        )
        admin_client.update(
            "ocr_jobs",
            filters={"id": f"eq.{job_id}"},
            payload={
                "auto_detect_charged": True,
                "auto_detect_charged_at": charged_at,
            },
        )
        return {"charged": True, "charged_count": 1, "credits_balance": new_balance}

    def _read_job_region_charge_rows(self, client: SupabaseClient, job_id: str) -> list[dict[str, Any]]:
        """region 단위 과금 상태와 결과 텍스트를 조회한다."""
        rows = client.select(
            "ocr_job_regions",
            params={
                "select": "region_key,status,ocr_text,explanation,was_charged",
                "job_id": f"eq.{job_id}",
                "order": "region_order.asc",
            },
        )
        if not rows:
            raise FileNotFoundError(f"job not found: {job_id}")
        return rows

    def _read_job_status(self, client: SupabaseClient, job_id: str) -> dict[str, Any]:
        """과금 대상 job의 종료 상태를 읽는다."""
        rows = client.select(
            "ocr_jobs",
            params={
                "select": "id,status",
                "id": f"eq.{job_id}",
            },
        )
        if not rows:
            raise FileNotFoundError(f"job not found: {job_id}")
        return rows[0]

    def _count_required_region_credits(self, region_rows: list[dict[str, Any]]) -> int:
        """재실행 시 새로 처리할 영역 수를 계산한다."""
        return sum(1 for row in region_rows if not bool(row.get("was_charged")))

    def _list_chargeable_region_keys(self, region_rows: list[dict[str, Any]]) -> list[str]:
        """문서에 포함 가능한 미과금 영역만 골라낸다."""
        region_keys: list[str] = []
        for row in region_rows:
            has_text = bool(str(row.get("ocr_text") or "").strip() or str(row.get("explanation") or "").strip())
            if bool(row.get("was_charged")) or row.get("status") != "completed" or not has_text:
                continue
            region_keys.append(str(row.get("region_key")))
        return region_keys

    def ensure_job_region_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict:
        """이번 실행에서 새로 처리할 영역 수만큼 잔액이 있는지 확인한다."""
        profile = self.get_or_create_profile(user)
        if processing_type == "user_api_key":
            return {"required_credits": 0, "credits_balance": profile.credits_balance}

        client = self._user_client(user)
        required_credits = self._count_required_region_credits(self._read_job_region_charge_rows(client, job_id))
        if profile.credits_balance < required_credits:
            raise ValueError("insufficient credits")
        return {
            "required_credits": required_credits,
            "credits_balance": profile.credits_balance,
        }

    def consume_job_region_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict:
        """문서 포함 가능한 완료 영역 수만큼만 크레딧을 차감한다."""
        profile = self.get_or_create_profile(user)
        if processing_type == "user_api_key":
            return {"charged_count": 0, "credits_balance": profile.credits_balance}

        client = self._user_client(user)
        job_row = self._read_job_status(client, job_id)
        if job_row.get("status") not in ("completed", "failed", "exported"):
            raise ValueError("job is not eligible for charging")

        region_rows = self._read_job_region_charge_rows(client, job_id)
        chargeable_region_keys = self._list_chargeable_region_keys(region_rows)
        charged_count = len(chargeable_region_keys)
        if charged_count == 0:
            return {"charged_count": 0, "credits_balance": profile.credits_balance}
        if profile.credits_balance < charged_count:
            raise ValueError("insufficient credits")

        new_balance = profile.credits_balance - charged_count
        admin_client = self._billing_write_client()
        admin_client.update(
            "profiles",
            filters={"user_id": f"eq.{user.user_id}"},
            payload={
                "credits_balance": new_balance,
                "used_credits": profile.used_credits + charged_count,
            },
        )
        admin_client.insert(
            "credit_ledger",
            {
                "user_id": user.user_id,
                "job_id": job_id,
                "delta": -charged_count,
                "balance_after": new_balance,
                "reason": "ocr_success_charge",
            },
        )
        charged_at = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
        for region_key in chargeable_region_keys:
            admin_client.update(
                "ocr_job_regions",
                filters={
                    "job_id": f"eq.{job_id}",
                    "region_key": f"eq.{region_key}",
                },
                payload={
                    "was_charged": True,
                    "charged_at": charged_at,
                },
            )
        return {
            "charged_count": charged_count,
            "credits_balance": new_balance,
        }

    def _read_job_charge_state(self, client: SupabaseClient, job_id: str) -> dict:
        """job별 항목 과금 상태를 읽어온다."""
        rows = client.select(
            "ocr_jobs",
            params={
                "select": "id,status,processing_type",
                "id": f"eq.{job_id}",
            },
        )
        if not rows:
            raise FileNotFoundError(f"job not found: {job_id}")
        return rows[0]

    def _read_job_action_charge_rows(
        self,
        client: SupabaseClient,
        job_id: str,
    ) -> list[dict[str, Any]]:
        """job 하위 region들의 액션별 과금 상태와 산출물 존재 여부를 읽는다."""
        params = {
            "job_id": f"eq.{job_id}",
            "order": "region_order.asc",
        }
        if should_use_markdown_output_columns():
            try:
                rows = client.select(
                    "ocr_job_regions",
                    params={**params, "select": _build_job_action_charge_select(include_markdown_output=True)},
                )
                remember_markdown_output_columns_available(True)
                return rows
            except Exception as error:
                if not is_markdown_output_schema_error(error):
                    raise
                remember_markdown_output_columns_available(False)
        return client.select(
            "ocr_job_regions",
            params={**params, "select": _build_job_action_charge_select(include_markdown_output=False)},
        )

    def _has_region_action_output(self, region_row: dict[str, Any], action: str) -> bool:
        """region row에서 액션별 성공 산출물 존재 여부를 판단한다."""
        if action == "ocr":
            return bool(
                str(region_row.get("problem_markdown") or "").strip()
                or str(region_row.get("ocr_text") or "").strip()
                or str(region_row.get("mathml") or "").strip()
            )
        if action == "image_stylize":
            return bool(str(region_row.get("styled_image_path") or "").strip())
        if action == "explanation":
            return bool(
                str(region_row.get("explanation_markdown") or "").strip()
                or str(region_row.get("explanation") or "").strip()
            )
        return False

    def _build_pending_region_actions(
        self,
        region_rows: list[dict[str, Any]],
        actions: list[str],
        *,
        require_output: bool,
    ) -> list[tuple[str, str]]:
        """region별로 아직 처리되지 않은 액션 목록을 순서대로 계산한다."""
        pending_region_actions: list[tuple[str, str]] = []
        for region_row in region_rows:
            region_key = str(region_row.get("region_key") or "")
            if not region_key:
                continue
            for action in actions:
                charge_flag = JOB_ACTION_FLAG_MAP.get(action)
                if not charge_flag:
                    continue
                if bool(region_row.get(charge_flag)):
                    continue
                if require_output and not self._has_region_action_output(region_row, action):
                    continue
                pending_region_actions.append((region_key, action))
        return pending_region_actions

    def ensure_job_action_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict:
        """선택된 작업을 실행하기에 크레딧이 충분한지 사전 점검한다."""
        client = self._user_client(user)
        self._read_job_charge_state(client, job_id)
        region_rows = self._read_job_action_charge_rows(client, job_id)
        profile = self.get_or_create_profile(user)
        pending_region_actions = self._build_pending_region_actions(
            region_rows,
            actions,
            require_output=False,
        )
        required_credits = sum(
            1
            for _, action in pending_region_actions
            if not (processing_type == "user_api_key" and action in FREE_USER_KEY_ACTIONS)
        )
        if profile.credits_balance < required_credits:
            raise ValueError("insufficient credits")
        return {
            "required_credits": required_credits,
            "credits_balance": profile.credits_balance,
        }

    def consume_job_action_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict:
        """실제로 성공한 region 액션별 항목만큼 크레딧을 차감한다."""
        client = self._user_client(user)
        job_row = self._read_job_charge_state(client, job_id)
        if job_row.get("status") not in ("completed", "failed", "exported"):
            raise ValueError("job is not eligible for charging")

        profile = self.get_or_create_profile(user)
        region_rows = self._read_job_action_charge_rows(client, job_id)
        completed_region_actions = self._build_pending_region_actions(
            region_rows,
            actions,
            require_output=True,
        )
        if not completed_region_actions:
            return {
                "charged_actions": [],
                "charged_count": 0,
                "credits_balance": profile.credits_balance,
            }

        paid_region_actions = [
            (region_key, action)
            for region_key, action in completed_region_actions
            if not (processing_type == "user_api_key" and action in FREE_USER_KEY_ACTIONS)
        ]
        if profile.credits_balance < len(paid_region_actions):
            raise ValueError("insufficient credits")

        new_balance = profile.credits_balance
        new_used_credits = profile.used_credits
        charged_actions: list[str] = []
        charged_at = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
        handled_actions = sorted({action for _, action in completed_region_actions})
        admin_client = self._billing_write_client()

        for _, action in paid_region_actions:
            new_balance -= 1
            new_used_credits += 1
            charged_actions.append(action)
            admin_client.insert(
                "credit_ledger",
                {
                    "user_id": user.user_id,
                    "job_id": job_id,
                    "delta": -1,
                    "balance_after": new_balance,
                    "reason": JOB_ACTION_REASON_MAP[action],
                },
            )

        if paid_region_actions:
            admin_client.update(
                "profiles",
                filters={"user_id": f"eq.{user.user_id}"},
                payload={
                    "credits_balance": new_balance,
                    "used_credits": new_used_credits,
                },
            )

        for region_key, action in completed_region_actions:
            admin_client.update(
                "ocr_job_regions",
                filters={
                    "job_id": f"eq.{job_id}",
                    "region_key": f"eq.{region_key}",
                },
                payload={
                    JOB_ACTION_FLAG_MAP[action]: True,
                    "was_charged": True,
                    "charged_at": charged_at,
                },
            )

        admin_client.update(
            "ocr_jobs",
            filters={"id": f"eq.{job_id}"},
            payload={
                **{JOB_ACTION_FLAG_MAP[action]: True for action in handled_actions},
                "was_charged": True,
                "charged_at": charged_at,
            },
        )
        return {
            "charged_actions": charged_actions,
            "charged_count": len(paid_region_actions),
            "credits_balance": new_balance,
        }


class BillingService:
    """Checkout, catalog, webhook 적재를 담당한다."""

    def __init__(
        self,
        store: BillingStoreProtocol,
        polar_gateway: PolarGatewayProtocol | None,
        plan_product_ids: dict[str, str],
        service_openai_api_key: str | None,
        openai_key_encryption_secret: str | None,
    ) -> None:
        self._store = store
        self._polar_gateway = polar_gateway
        self._plan_product_ids = plan_product_ids
        self._service_openai_api_key = service_openai_api_key
        self._openai_key_encryption_secret = openai_key_encryption_secret

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
        return build_validated_plan_from_product(
            product,
            expected_plan_id=plan_id,
            configured_product_id=product_id,
        )

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

    def save_openai_key(self, user: AuthenticatedUser, api_key: str) -> BillingProfile:
        """사용자 OpenAI key를 암호화해 저장하고 profile을 갱신한다."""
        normalized = _validate_openai_api_key(api_key)
        encrypted_api_key = _encrypt_openai_api_key(self._openai_key_encryption_secret, normalized)
        return self._store.upsert_openai_key(
            user,
            encrypted_api_key=encrypted_api_key,
            key_last4=normalized[-4:],
            masked_key=_mask_openai_api_key(normalized),
        )

    def delete_openai_key(self, user: AuthenticatedUser) -> BillingProfile:
        """사용자 OpenAI key를 비활성화하고 profile을 갱신한다."""
        return self._store.deactivate_openai_key(user)

    def resolve_openai_api_key(self, user: AuthenticatedUser) -> ResolvedOpenAiApiKey:
        """OCR 실행에 사용할 OpenAI key와 처리 유형을 결정한다."""
        stored_key = self._store.get_active_openai_key(user)
        if stored_key is not None:
            return ResolvedOpenAiApiKey(
                api_key=_decrypt_openai_api_key(
                    self._openai_key_encryption_secret,
                    stored_key.encrypted_api_key,
                ),
                processing_type="user_api_key",
            )
        if self._service_openai_api_key:
            return ResolvedOpenAiApiKey(
                api_key=self._service_openai_api_key,
                processing_type="service_api",
            )
        raise ValueError("OpenAI API key is not configured")

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
        plan_id = _normalize_text(metadata.get("plan_id"), "plan_id metadata")
        user_id = _normalize_text(customer.get("external_id") or order.get("metadata", {}).get("user_id"), "user_id")
        plan = build_validated_plan_from_product(
            product,
            expected_plan_id=plan_id,
            configured_product_id=self._plan_product_ids.get(plan_id),
            amount=order.get("total_amount") or order.get("amount"),
            currency=order.get("currency"),
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

    def ensure_job_auto_detect_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict:
        """자동 분할 1회 차감이 필요한지와 잔액을 확인한다."""
        return self._store.ensure_job_auto_detect_credits_available(user, job_id)

    def consume_job_auto_detect_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict:
        """자동 분할이 성공 저장됐을 때만 1회 차감을 수행한다."""
        return self._store.consume_job_auto_detect_credits(user, job_id)

    def ensure_job_region_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict:
        """이번 실행에서 새로 처리할 영역 수 기준으로 잔액을 확인한다."""
        return self._store.ensure_job_region_credits_available(
            user,
            job_id,
            processing_type=processing_type,
        )

    def consume_job_region_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict:
        """내보내기 가능한 완료 영역 수만큼만 후차감한다."""
        return self._store.consume_job_region_credits(
            user,
            job_id,
            processing_type=processing_type,
        )

    def ensure_job_action_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict:
        """선택한 작업 조합을 실행할 수 있는 크레딧이 있는지 확인한다."""
        return self._store.ensure_job_action_credits_available(
            user,
            job_id,
            actions,
            processing_type=processing_type,
        )

    def consume_job_action_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict:
        """실행 성공 후 실제 수행된 항목만큼 크레딧을 차감한다."""
        return self._store.consume_job_action_credits(
            user,
            job_id,
            actions,
            processing_type=processing_type,
        )


def build_billing_service(root_path: Path | None = None, require_polar: bool = False) -> BillingService:
    """환경설정 기반 기본 BillingService를 만든다."""
    settings = get_settings(root_path or ROOT)
    product_ids = {
        "single": _normalize_optional_text(settings.billing.polar_product_single_id) or "",
        "starter": _normalize_optional_text(settings.billing.polar_product_starter_id) or "",
        "pro": _normalize_optional_text(settings.billing.polar_product_pro_id) or "",
    }
    if require_polar:
        _validate_required_polar_settings(
            settings.billing.polar_access_token,
            settings.billing.polar_server,
            product_ids,
        )

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
        service_openai_api_key=settings.openai_api_key,
        openai_key_encryption_secret=settings.openai_key_encryption_secret,
    )
