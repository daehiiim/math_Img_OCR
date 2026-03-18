import base64
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from standardwebhooks.webhooks import Webhook

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.auth as auth_module
import app.main as main_module
from app.auth import AuthenticatedUser
from app.billing import BillingPlan, BillingProfile, BillingService, PolarGateway, StoredOpenAiKey, build_billing_service
from app.config import AppSettings, AuthSettings, BillingSettings
from app.main import app
from tests.auth_test_utils import StubJwksResponse, build_es256_key_pair, build_es256_token


class FakePolarGateway:
    def __init__(self) -> None:
        self.created_checkouts: list[dict] = []
        self.created_customer_sessions: list[dict] = []
        self.products = {
            "prod_single": {
                "id": "prod_single",
                "name": "Single",
                "prices": [{"price_amount": 1000, "price_currency": "krw"}],
                "metadata": {"plan_id": "single", "credits": "1"},
            },
            "prod_starter": {
                "id": "prod_starter",
                "name": "Starter",
                "prices": [{"price_amount": 19000, "price_currency": "krw"}],
                "metadata": {"plan_id": "starter", "credits": "100"},
            },
            "prod_pro": {
                "id": "prod_pro",
                "name": "Pro",
                "prices": [{"price_amount": 29000, "price_currency": "krw"}],
                "metadata": {"plan_id": "pro", "credits": "200"},
            },
        }

    def get_product(self, product_id: str) -> dict:
        return self.products[product_id]

    def create_checkout(
        self,
        *,
        external_customer_id: str,
        plan: BillingPlan,
        success_url: str,
        cancel_url: str | None,
    ) -> dict:
        self.created_checkouts.append(
            {
                "external_customer_id": external_customer_id,
                "plan": plan,
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
        return {"id": "chk_test_123", "url": "https://sandbox-checkout.polar.sh/checkout/chk_test_123", "status": "open"}

    def get_checkout(self, checkout_id: str) -> dict:
        return {"id": checkout_id, "status": "succeeded"}

    def create_customer_session(self, customer_id: str, return_url: str | None = None) -> dict:
        self.created_customer_sessions.append({"customer_id": customer_id, "return_url": return_url})
        return {"customer_portal_url": "https://polar.sh/customer-portal/session"}

    def verify_event(self, payload: bytes, signature: str) -> dict:
        return {
            "id": "evt_123",
            "type": "order.paid",
            "data": {
                "id": "ord_123",
                "checkout_id": "chk_test_123",
                "customer": {
                    "id": "cus_123",
                    "external_id": "user-123",
                },
                "product": {
                    "id": "prod_starter",
                    "metadata": {
                        "plan_id": "starter",
                        "credits": "100",
                    },
                    "name": "Starter",
                    "prices": [{"price_amount": 19000, "price_currency": "krw"}],
                },
                "amount": 19000,
                "currency": "krw",
                "invoice_number": "INV-123",
                "invoice_url": "https://polar.sh/invoices/INV-123",
            },
        }


class FakeBillingStore:
    def __init__(self) -> None:
        self.profiles: dict[str, BillingProfile] = {}
        self.payment_events: dict[str, dict] = {}
        self.payment_events_by_checkout_id: dict[str, dict] = {}
        self.ledger_entries: list[dict] = []
        self.charged_jobs: set[str] = set()
        self.openai_keys: dict[str, dict] = {}

    def get_or_create_profile(self, user: AuthenticatedUser) -> BillingProfile:
        return self.profiles.setdefault(
            user.user_id,
            BillingProfile(
                user_id=user.user_id,
                credits_balance=0,
                used_credits=0,
                openai_connected=False,
                openai_key_masked=None,
            ),
        )

    def has_payment_event(self, provider: str, provider_event_id: str) -> bool:
        return f"{provider}:{provider_event_id}" in self.payment_events

    def has_recorded_order(self, provider: str, provider_order_id: str) -> bool:
        return any(
            payment_event["provider_order_id"] == provider_order_id
            for payment_event in self.payment_events.values()
            if payment_event["provider"] == provider
        )

    def find_payment_event_by_checkout_id(self, provider: str, checkout_id: str) -> dict | None:
        return self.payment_events_by_checkout_id.get(f"{provider}:{checkout_id}")

    def find_customer_id_for_user(self, provider: str, user_id: str) -> str | None:
        for payment_event in reversed(list(self.payment_events.values())):
            if payment_event["provider"] == provider and payment_event.get("provider_customer_id"):
                return payment_event["provider_customer_id"]
        return None

    def record_completed_payment(
        self,
        *,
        provider: str,
        provider_event_id: str,
        provider_order_id: str,
        provider_checkout_id: str,
        provider_customer_id: str,
        user_id: str,
        plan: BillingPlan,
        amount: int,
        currency: str,
        invoice_number: str | None,
        invoice_url: str | None,
        raw_payload: dict,
    ) -> dict:
        profile = self.profiles.setdefault(
            user_id,
            BillingProfile(
                user_id=user_id,
                credits_balance=0,
                used_credits=0,
                openai_connected=False,
                openai_key_masked=None,
            ),
        )
        new_profile = BillingProfile(
            user_id=profile.user_id,
            credits_balance=profile.credits_balance + plan.credits,
            used_credits=profile.used_credits,
            openai_connected=profile.openai_connected,
            openai_key_masked=profile.openai_key_masked,
        )
        self.profiles[user_id] = new_profile
        event_key = f"{provider}:{provider_event_id}"
        recorded = {
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
        }
        self.payment_events[event_key] = recorded
        self.payment_events_by_checkout_id[f"{provider}:{provider_checkout_id}"] = recorded
        self.ledger_entries.append(
            {
                "user_id": user_id,
                "delta": plan.credits,
                "balance_after": new_profile.credits_balance,
                "reason": "purchase",
            }
        )
        return {
            "credits_balance": new_profile.credits_balance,
            "credits_added": plan.credits,
        }

    def consume_job_credit(self, user: AuthenticatedUser, job_id: str) -> dict:
        profile = self.get_or_create_profile(user)
        if job_id in self.charged_jobs:
            return {"charged": False, "credits_balance": profile.credits_balance}
        if profile.credits_balance <= 0:
            raise ValueError("insufficient credits")

        new_profile = BillingProfile(
            user_id=profile.user_id,
            credits_balance=profile.credits_balance - 1,
            used_credits=profile.used_credits + 1,
            openai_connected=profile.openai_connected,
            openai_key_masked=profile.openai_key_masked,
        )
        self.profiles[user.user_id] = new_profile
        self.charged_jobs.add(job_id)
        self.ledger_entries.append(
            {
                "user_id": user.user_id,
                "job_id": job_id,
                "delta": -1,
                "balance_after": new_profile.credits_balance,
                "reason": "ocr_success_charge",
            }
        )
        return {"charged": True, "credits_balance": new_profile.credits_balance}

    def upsert_openai_key(
        self,
        user: AuthenticatedUser,
        *,
        encrypted_api_key: str,
        key_last4: str,
        masked_key: str,
    ) -> BillingProfile:
        self.openai_keys[user.user_id] = {
            "encrypted_api_key": encrypted_api_key,
            "key_last4": key_last4,
            "is_active": True,
        }
        profile = self.get_or_create_profile(user)
        next_profile = BillingProfile(
            user_id=profile.user_id,
            credits_balance=profile.credits_balance,
            used_credits=profile.used_credits,
            openai_connected=True,
            openai_key_masked=masked_key,
        )
        self.profiles[user.user_id] = next_profile
        return next_profile

    def deactivate_openai_key(self, user: AuthenticatedUser) -> BillingProfile:
        key_row = self.openai_keys.get(user.user_id)
        if key_row is not None:
            key_row["is_active"] = False
        profile = self.get_or_create_profile(user)
        next_profile = BillingProfile(
            user_id=profile.user_id,
            credits_balance=profile.credits_balance,
            used_credits=profile.used_credits,
            openai_connected=False,
            openai_key_masked=None,
        )
        self.profiles[user.user_id] = next_profile
        return next_profile

    def get_active_openai_key(self, user: AuthenticatedUser) -> dict | None:
        key_row = self.openai_keys.get(user.user_id)
        if not key_row or not key_row.get("is_active"):
            return None
        return StoredOpenAiKey(
            encrypted_api_key=str(key_row["encrypted_api_key"]),
            key_last4=str(key_row["key_last4"]),
            is_active=bool(key_row["is_active"]),
        )


def make_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id="user-123", access_token="token-123")


def make_service():
    gateway = FakePolarGateway()
    store = FakeBillingStore()
    service = BillingService(
        store=store,
        polar_gateway=gateway,
        plan_product_ids={
            "single": "prod_single",
            "starter": "prod_starter",
            "pro": "prod_pro",
        },
        service_openai_api_key="sk-service-1234567890",
        openai_key_encryption_secret="encryption-secret",
    )
    return service, store, gateway


def test_create_checkout_uses_product_metadata():
    service, _, gateway = make_service()

    result = service.create_checkout(
        make_user(),
        plan_id="starter",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )

    created = gateway.created_checkouts[0]
    assert created["external_customer_id"] == "user-123"
    assert created["plan"].plan_id == "starter"
    assert created["plan"].credits == 100
    assert created["plan"].amount == 19000
    assert created["plan"].currency == "krw"
    assert result["checkout_url"] == "https://sandbox-checkout.polar.sh/checkout/chk_test_123"
    assert result["checkout_id"] == "chk_test_123"


def test_list_plans_returns_polar_catalog_metadata():
    service, _, _ = make_service()

    plans = service.list_plans()

    assert [plan["plan_id"] for plan in plans] == ["single", "starter", "pro"]
    starter = plans[1]
    assert starter["title"] == "Starter"
    assert starter["credits"] == 100
    assert starter["amount"] == 19000
    assert starter["currency"] == "krw"


def test_create_checkout_rejects_non_krw_product_currency():
    service, _, gateway = make_service()
    gateway.products["prod_starter"]["prices"] = [{"price_amount": 19000, "price_currency": "usd"}]

    with pytest.raises(ValueError) as error:
        service.create_checkout(
            make_user(),
            plan_id="starter",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

    assert str(error.value) == "product currency mismatch"


def test_create_checkout_rejects_missing_product_price():
    service, _, gateway = make_service()
    gateway.products["prod_starter"].pop("prices", None)

    with pytest.raises(ValueError) as error:
        service.create_checkout(
            make_user(),
            plan_id="starter",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

    assert str(error.value) == "missing product price"


def test_apply_order_paid_event_requires_plan_id_metadata():
    service, _, gateway = make_service()
    event = gateway.verify_event(b"{}", "signature")
    event["data"]["product"]["metadata"].pop("plan_id")

    with pytest.raises(ValueError) as error:
        service.apply_webhook_event(event)

    assert str(error.value) == "missing plan_id metadata"


def test_apply_order_paid_event_requires_valid_credits_metadata():
    service, _, gateway = make_service()
    event = gateway.verify_event(b"{}", "signature")
    event["data"]["product"]["metadata"]["credits"] = "abc"

    with pytest.raises(ValueError) as error:
        service.apply_webhook_event(event)

    assert str(error.value) == "invalid credits metadata"


def test_apply_order_paid_event_rejects_mismatched_configured_product_id():
    service, _, gateway = make_service()
    event = gateway.verify_event(b"{}", "signature")
    event["data"]["product"]["id"] = "prod_other"

    with pytest.raises(ValueError) as error:
        service.apply_webhook_event(event)

    assert str(error.value) == "configured Polar product id mismatch"


def test_apply_order_paid_event_is_idempotent():
    service, store, gateway = make_service()

    event = gateway.verify_event(b"{}", "signature")

    first = service.apply_webhook_event(event)
    second = service.apply_webhook_event(event)

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert store.profiles["user-123"].credits_balance == 100
    assert len(store.payment_events) == 1
    assert len(store.ledger_entries) == 1


def test_get_checkout_includes_credit_application_state():
    service, _, gateway = make_service()

    before = service.get_checkout("chk_test_123")
    service.apply_webhook_event(gateway.verify_event(b"{}", "signature"))
    after = service.get_checkout("chk_test_123")

    assert before["status"] == "succeeded"
    assert before["credits_applied"] is False
    assert after["credits_applied"] is True


def test_create_customer_portal_requires_recorded_customer():
    service, _, gateway = make_service()
    service.apply_webhook_event(gateway.verify_event(b"{}", "signature"))

    result = service.create_customer_portal(make_user())

    assert gateway.created_customer_sessions == [{"customer_id": "cus_123", "return_url": None}]
    assert result["customer_portal_url"] == "https://polar.sh/customer-portal/session"


def test_consume_job_credit_decrements_balance_only_once():
    service, store, _ = make_service()
    store.profiles["user-123"] = BillingProfile(
        user_id="user-123",
        credits_balance=3,
        used_credits=0,
        openai_connected=False,
        openai_key_masked=None,
    )

    first = service.consume_job_credit(make_user(), "job-123")
    second = service.consume_job_credit(make_user(), "job-123")

    assert first["charged"] is True
    assert first["credits_balance"] == 2
    assert second["charged"] is False
    assert store.profiles["user-123"].credits_balance == 2


def test_save_openai_key_encrypts_and_updates_profile():
    service, store, _ = make_service()

    profile = service.save_openai_key(make_user(), "sk-user-1234567890")

    key_row = store.openai_keys["user-123"]
    assert profile.openai_connected is True
    assert profile.openai_key_masked.endswith("7890")
    assert key_row["is_active"] is True
    assert key_row["key_last4"] == "7890"
    assert key_row["encrypted_api_key"] != "sk-user-1234567890"


def test_save_openai_key_overwrites_existing_ciphertext():
    service, store, _ = make_service()
    service.save_openai_key(make_user(), "sk-user-1234567890")
    first_ciphertext = store.openai_keys["user-123"]["encrypted_api_key"]

    profile = service.save_openai_key(make_user(), "sk-user-abcdef7891")

    assert store.openai_keys["user-123"]["encrypted_api_key"] != first_ciphertext
    assert store.openai_keys["user-123"]["key_last4"] == "7891"
    assert profile.openai_key_masked.endswith("7891")


def test_save_openai_key_requires_encryption_secret():
    gateway = FakePolarGateway()
    store = FakeBillingStore()
    service = BillingService(
        store=store,
        polar_gateway=gateway,
        plan_product_ids={
            "single": "prod_single",
            "starter": "prod_starter",
            "pro": "prod_pro",
        },
        service_openai_api_key="sk-service-1234567890",
        openai_key_encryption_secret=None,
    )

    try:
        service.save_openai_key(make_user(), "sk-user-1234567890")
    except ValueError as error:
        assert str(error) == "OPENAI_KEY_ENCRYPTION_SECRET is not configured"
    else:
        raise AssertionError("OPENAI key 저장은 암호화 secret 없이는 실패해야 한다.")


def test_delete_openai_key_deactivates_profile_and_key():
    service, store, _ = make_service()
    service.save_openai_key(make_user(), "sk-user-1234567890")

    profile = service.delete_openai_key(make_user())

    assert profile.openai_connected is False
    assert profile.openai_key_masked is None
    assert store.openai_keys["user-123"]["is_active"] is False


def test_resolve_openai_api_key_prefers_active_user_key():
    service, _, _ = make_service()
    service.save_openai_key(make_user(), "sk-user-1234567890")

    resolved = service.resolve_openai_api_key(make_user())

    assert resolved.processing_type == "user_api_key"
    assert resolved.api_key == "sk-user-1234567890"


def test_resolve_openai_api_key_falls_back_to_service_key():
    service, _, _ = make_service()

    resolved = service.resolve_openai_api_key(make_user())

    assert resolved.processing_type == "service_api"
    assert resolved.api_key == "sk-service-1234567890"


def _build_auth_settings() -> AppSettings:
    """인증 회귀 테스트용 최소 설정을 만든다."""
    return AppSettings(
        openai_api_key=None,
        openai_key_encryption_secret="encryption-secret",
        database_url=None,
        auth=AuthSettings(
            supabase_url="https://billing-auth.supabase.co",
            supabase_anon_key="anon-key",
            supabase_jwt_secret=None,
            supabase_storage_bucket="ocr-assets",
            supabase_service_role_key="service-role-key",
        ),
        billing=BillingSettings(
            polar_access_token="polar-token",
            polar_webhook_secret="whsec-test",
            polar_server="sandbox",
            polar_product_single_id="prod_single",
            polar_product_starter_id="prod_starter",
            polar_product_pro_id="prod_pro",
        ),
    )


def test_billing_profile_accepts_es256_authenticated_user(monkeypatch):
    private_key, jwk = build_es256_key_pair("billing-profile-kid")
    token = build_es256_token(private_key, "billing-profile-kid", "user-123")

    monkeypatch.setattr(auth_module, "get_settings", lambda root_path: _build_auth_settings())
    monkeypatch.setattr(
        auth_module.requests,
        "get",
        lambda url, timeout=5: StubJwksResponse({"keys": [jwk]}),
    )
    monkeypatch.setattr(
        main_module,
        "_get_billing_service",
        lambda require_polar=False: type(
            "StubBillingService",
            (),
            {
                "get_profile": lambda self, current_user: BillingProfile(
                    user_id=current_user.user_id,
                    credits_balance=12,
                    used_credits=3,
                    openai_connected=True,
                    openai_key_masked="sk-test",
                )
            },
        )(),
    )

    client = TestClient(app)
    response = client.get("/billing/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["credits_balance"] == 12
    assert response.json()["openai_connected"] is True


def test_billing_put_openai_key_accepts_es256_authenticated_user(monkeypatch):
    private_key, jwk = build_es256_key_pair("billing-openai-put-kid")
    token = build_es256_token(private_key, "billing-openai-put-kid", "user-123")

    monkeypatch.setattr(auth_module, "get_settings", lambda root_path: _build_auth_settings())
    monkeypatch.setattr(
        auth_module.requests,
        "get",
        lambda url, timeout=5: StubJwksResponse({"keys": [jwk]}),
    )
    save_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        main_module,
        "_get_billing_service",
        lambda require_polar=False: type(
            "StubBillingService",
            (),
            {
                "save_openai_key": lambda self, current_user, api_key: (
                    save_calls.append((current_user.user_id, api_key))
                    or BillingProfile(
                        user_id=current_user.user_id,
                        credits_balance=5,
                        used_credits=1,
                        openai_connected=True,
                        openai_key_masked="sk-us••••7890",
                    )
                )
            },
        )(),
    )

    client = TestClient(app)
    response = client.put(
        "/billing/openai-key",
        headers={"Authorization": f"Bearer {token}"},
        json={"api_key": "sk-user-1234567890"},
    )

    assert response.status_code == 200
    assert save_calls == [("user-123", "sk-user-1234567890")]
    assert response.json()["openai_connected"] is True
    assert response.json()["openai_key_masked"] == "sk-us••••7890"


def test_billing_delete_openai_key_accepts_es256_authenticated_user(monkeypatch):
    private_key, jwk = build_es256_key_pair("billing-openai-delete-kid")
    token = build_es256_token(private_key, "billing-openai-delete-kid", "user-123")

    monkeypatch.setattr(auth_module, "get_settings", lambda root_path: _build_auth_settings())
    monkeypatch.setattr(
        auth_module.requests,
        "get",
        lambda url, timeout=5: StubJwksResponse({"keys": [jwk]}),
    )
    delete_calls: list[str] = []
    monkeypatch.setattr(
        main_module,
        "_get_billing_service",
        lambda require_polar=False: type(
            "StubBillingService",
            (),
            {
                "delete_openai_key": lambda self, current_user: (
                    delete_calls.append(current_user.user_id)
                    or BillingProfile(
                        user_id=current_user.user_id,
                        credits_balance=5,
                        used_credits=1,
                        openai_connected=False,
                        openai_key_masked=None,
                    )
                )
            },
        )(),
    )

    client = TestClient(app)
    response = client.delete(
        "/billing/openai-key",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert delete_calls == ["user-123"]
    assert response.json()["openai_connected"] is False


def test_billing_checkout_accepts_es256_authenticated_user(monkeypatch):
    private_key, jwk = build_es256_key_pair("billing-checkout-kid")
    token = build_es256_token(private_key, "billing-checkout-kid", "user-123")

    monkeypatch.setattr(auth_module, "get_settings", lambda root_path: _build_auth_settings())
    monkeypatch.setattr(
        auth_module.requests,
        "get",
        lambda url, timeout=5: StubJwksResponse({"keys": [jwk]}),
    )
    monkeypatch.setattr(
        main_module,
        "_get_billing_service",
        lambda require_polar=False: type(
            "StubBillingService",
            (),
            {
                "create_checkout": lambda self, current_user, plan_id, success_url, cancel_url: {
                    "checkout_id": "chk_test_123",
                    "checkout_url": "https://example.com/checkout",
                    "plan_id": plan_id,
                    "credits": 100,
                    "amount": 19000,
                    "currency": "krw",
                }
            },
        )(),
    )

    client = TestClient(app)
    response = client.post(
        "/billing/checkout-session",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": "starter",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )

    assert response.status_code == 200
    assert response.json()["checkout_id"] == "chk_test_123"


def test_polar_gateway_verify_event_accepts_polar_secret_prefix():
    raw_secret = "polar_whs_test_secret_for_sdk_encoding"
    gateway = PolarGateway(
        access_token="polar-token",
        webhook_secret=raw_secret,
        server="sandbox",
    )
    payload = b'{"type":"order.paid","data":{"id":"ord_123"}}'
    timestamp = datetime.fromtimestamp(int(time.time()), tz=timezone.utc)
    headers = {
        "webhook-id": "evt_123",
        "webhook-timestamp": str(int(timestamp.timestamp())),
    }
    encoded_secret = base64.b64encode(raw_secret.encode("utf-8")).decode("utf-8")
    headers["webhook-signature"] = Webhook(encoded_secret).sign(
        msg_id=headers["webhook-id"],
        timestamp=timestamp,
        data=payload.decode("utf-8"),
    )

    event = gateway.verify_event(payload, headers)

    assert event["type"] == "order.paid"
    assert event["_event_id"] == "evt_123"


def test_build_billing_service_requires_production_server_for_live_billing(monkeypatch):
    monkeypatch.setattr(
        "app.billing.get_settings",
        lambda root_path: AppSettings(
            openai_api_key=None,
            openai_key_encryption_secret="encryption-secret",
            database_url=None,
            auth=AuthSettings(
                supabase_url="https://billing-auth.supabase.co",
                supabase_anon_key="anon-key",
                supabase_jwt_secret=None,
                supabase_storage_bucket="ocr-assets",
                supabase_service_role_key="service-role-key",
            ),
            billing=BillingSettings(
                polar_access_token="polar-token",
                polar_webhook_secret="whsec-test",
                polar_server="sandbox",
                polar_product_single_id="prod_single",
                polar_product_starter_id="prod_starter",
                polar_product_pro_id="prod_pro",
            ),
        ),
    )

    try:
        build_billing_service(root_path=Path("."), require_polar=True)
    except ValueError as error:
        assert str(error) == "POLAR_SERVER must be production for live billing"
    else:
        raise AssertionError("운영 결제 경로는 production Polar 서버만 허용해야 한다.")


def test_polar_gateway_normalizes_invalid_token_errors(monkeypatch):
    class FakeSDKError(Exception):
        """Polar SDK 401을 흉내 내는 테스트 예외다."""

    class FakeProductsClient:
        """상품 조회 시 invalid_token 에러를 던진다."""

        def get(self, *, id: str):
            raise FakeSDKError(
                'API error occurred: Status 401. Body: {"error": "invalid_token", '
                '"error_description": "The access token provided is expired, revoked, malformed, '
                'or invalid for other reasons."}'
            )

    class FakePolarClient:
        """products client만 노출하는 테스트용 Polar 클라이언트다."""

        def __init__(self) -> None:
            self.products = FakeProductsClient()

    monkeypatch.setattr("app.billing.polar_models.SDKError", FakeSDKError)
    monkeypatch.setattr("app.billing.Polar", lambda access_token, server: FakePolarClient())

    gateway = PolarGateway(
        access_token="polar-token",
        webhook_secret="whsec-test",
        server="production",
    )

    try:
        gateway.get_product("prod_live")
    except ValueError as error:
        assert str(error) == "POLAR_ACCESS_TOKEN does not match POLAR_SERVER"
    else:
        raise AssertionError("Polar 401 invalid_token 은 설정 불일치 오류로 정규화돼야 한다.")
