import base64
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic_core import PydanticUndefined
from fastapi.testclient import TestClient
from standardwebhooks.webhooks import Webhook

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.auth as auth_module
import app.main as main_module
import app.schema_compat as schema_compat_module
from app.auth import AuthenticatedUser, require_authenticated_user
from app.billing import BillingPlan, BillingProfile, BillingService, PolarGateway, StoredOpenAiKey, SupabaseBillingStore, build_billing_service
from app.config import AppSettings, AuthSettings, BillingSettings
from app.main import app
from app.supabase import SupabaseApiError
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
        self.auto_detect_charged_jobs: set[str] = set()
        self.charged_actions: set[tuple[str, str]] = set()
        self.job_regions: dict[str, list[dict[str, object]]] = {}
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

    def ensure_job_auto_detect_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict:
        profile = self.get_or_create_profile(user)
        required = 0 if job_id in self.auto_detect_charged_jobs else 1
        if profile.credits_balance < required:
            raise ValueError("insufficient credits")
        return {"required_credits": required, "credits_balance": profile.credits_balance}

    def consume_job_auto_detect_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
    ) -> dict:
        profile = self.get_or_create_profile(user)
        if job_id in self.auto_detect_charged_jobs:
            return {"charged": False, "charged_count": 0, "credits_balance": profile.credits_balance}
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
        self.auto_detect_charged_jobs.add(job_id)
        self.ledger_entries.append(
            {
                "user_id": user.user_id,
                "job_id": job_id,
                "delta": -1,
                "balance_after": new_profile.credits_balance,
                "reason": "auto_detect_charge",
            }
        )
        return {"charged": True, "charged_count": 1, "credits_balance": new_profile.credits_balance}

    def ensure_job_action_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict:
        profile = self.get_or_create_profile(user)
        action_flag_map = {
            "ocr": "ocr_charged",
            "image_stylize": "image_charged",
            "explanation": "explanation_charged",
        }
        required = 0
        for region in self.job_regions.get(job_id, []):
            for action in actions:
                charge_flag = action_flag_map.get(action)
                if charge_flag is None:
                    continue
                if processing_type == "user_api_key" and action in {"ocr", "explanation"}:
                    continue
                if bool(region.get(charge_flag)):
                    continue
                required += 1
        if profile.credits_balance < required:
            raise ValueError("insufficient credits")
        return {"required_credits": required, "credits_balance": profile.credits_balance}

    def consume_job_action_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        actions: list[str],
        *,
        processing_type: str,
    ) -> dict:
        profile = self.get_or_create_profile(user)
        charged_actions: list[str] = []
        new_balance = profile.credits_balance
        new_used_credits = profile.used_credits
        action_flag_map = {
            "ocr": "ocr_charged",
            "image_stylize": "image_charged",
            "explanation": "explanation_charged",
        }

        for region in self.job_regions.get(job_id, []):
            for action in actions:
                charge_flag = action_flag_map.get(action)
                if charge_flag is None or bool(region.get(charge_flag)):
                    continue
                if action == "ocr":
                    has_output = bool(region.get("ocr_text") or region.get("mathml"))
                elif action == "image_stylize":
                    has_output = bool(region.get("styled_image_path"))
                else:
                    has_output = bool(region.get("explanation"))
                if not has_output:
                    continue

                region[charge_flag] = True
                region["was_charged"] = True
                if processing_type == "user_api_key" and action in {"ocr", "explanation"}:
                    continue
                if new_balance <= 0:
                    raise ValueError("insufficient credits")
                new_balance -= 1
                new_used_credits += 1
                charged_actions.append(action)
                self.ledger_entries.append(
                    {
                        "user_id": user.user_id,
                        "job_id": job_id,
                        "delta": -1,
                        "balance_after": new_balance,
                        "reason": f"{action}_charge",
                    }
                )

        self.profiles[user.user_id] = BillingProfile(
            user_id=profile.user_id,
            credits_balance=new_balance,
            used_credits=new_used_credits,
            openai_connected=profile.openai_connected,
            openai_key_masked=profile.openai_key_masked,
        )
        return {
            "charged_actions": charged_actions,
            "charged_count": len(charged_actions),
            "credits_balance": new_balance,
        }

    def ensure_job_region_credits_available(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict:
        regions = self.job_regions.get(job_id, [])
        required = 0
        if processing_type != "user_api_key":
            required = sum(1 for region in regions if not bool(region.get("was_charged")))
        profile = self.get_or_create_profile(user)
        if profile.credits_balance < required:
            raise ValueError("insufficient credits")
        return {"required_credits": required, "credits_balance": profile.credits_balance}

    def consume_job_region_credits(
        self,
        user: AuthenticatedUser,
        job_id: str,
        *,
        processing_type: str,
    ) -> dict:
        profile = self.get_or_create_profile(user)
        regions = self.job_regions.get(job_id, [])
        if processing_type == "user_api_key":
            return {"charged_count": 0, "credits_balance": profile.credits_balance}

        chargeable_regions = [
            region
            for region in regions
            if not bool(region.get("was_charged"))
            and bool(region.get("exportable"))
        ]
        charged_count = len(chargeable_regions)
        if profile.credits_balance < charged_count:
            raise ValueError("insufficient credits")

        new_balance = profile.credits_balance - charged_count
        self.profiles[user.user_id] = BillingProfile(
            user_id=profile.user_id,
            credits_balance=new_balance,
            used_credits=profile.used_credits + charged_count,
            openai_connected=profile.openai_connected,
            openai_key_masked=profile.openai_key_masked,
        )
        for region in chargeable_regions:
            region["was_charged"] = True
        if charged_count:
            self.ledger_entries.append(
                {
                    "user_id": user.user_id,
                    "job_id": job_id,
                    "delta": -charged_count,
                    "balance_after": new_balance,
                    "reason": "ocr_success_charge",
                }
            )
        return {"charged_count": charged_count, "credits_balance": new_balance}

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


class RecordingSupabaseClient:
    """SupabaseBillingStore 호출 경로를 기록하는 테스트용 클라이언트다."""

    def __init__(self, *, select_rows: dict[str, list[dict]] | None = None) -> None:
        self._select_rows = select_rows or {}
        self.operations: list[dict[str, object]] = []

    def select(self, table: str, *, params: dict[str, object]) -> list[dict]:
        """select 호출을 기록하고 미리 준비한 row를 반환한다."""
        self.operations.append({"method": "select", "table": table, "params": params})
        return [dict(row) for row in self._select_rows.get(table, [])]

    def insert(self, table: str, payload: dict[str, object] | list[dict[str, object]]) -> list[dict]:
        """insert 호출을 기록하고 payload를 그대로 돌려준다."""
        self.operations.append({"method": "insert", "table": table, "payload": payload})
        if isinstance(payload, list):
            return payload
        return [payload]

    def update(
        self,
        table: str,
        *,
        filters: dict[str, object],
        payload: dict[str, object],
    ) -> list[dict]:
        """update 호출을 기록하고 payload를 그대로 돌려준다."""
        self.operations.append(
            {
                "method": "update",
                "table": table,
                "filters": filters,
                "payload": payload,
            }
        )
        return [payload]


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


def test_consume_job_auto_detect_credits_charges_only_once_per_job():
    service, store, _ = make_service()
    store.profiles["user-123"] = BillingProfile(
        user_id="user-123",
        credits_balance=3,
        used_credits=0,
        openai_connected=True,
        openai_key_masked="sk-us••••7890",
    )

    preview_first = service.ensure_job_auto_detect_credits_available(make_user(), "job-123")
    charged_first = service.consume_job_auto_detect_credits(make_user(), "job-123")
    preview_second = service.ensure_job_auto_detect_credits_available(make_user(), "job-123")
    charged_second = service.consume_job_auto_detect_credits(make_user(), "job-123")

    assert preview_first["required_credits"] == 1
    assert charged_first["charged"] is True
    assert charged_first["charged_count"] == 1
    assert preview_second["required_credits"] == 0
    assert charged_second["charged"] is False
    assert charged_second["charged_count"] == 0
    assert store.profiles["user-123"].credits_balance == 2
    assert store.ledger_entries[-1]["reason"] == "auto_detect_charge"


def test_consume_job_action_credits_charges_only_selected_actions():
    service, store, _ = make_service()
    store.profiles["user-123"] = BillingProfile(
        user_id="user-123",
        credits_balance=8,
        used_credits=0,
        openai_connected=False,
        openai_key_masked=None,
    )
    store.job_regions["job-123"] = [
        {
            "region_id": "q1",
            "ocr_charged": False,
            "image_charged": False,
            "explanation_charged": False,
            "ocr_text": "문제 1",
            "explanation": "해설 1",
            "styled_image_path": "styled-1.png",
        },
        {
            "region_id": "q2",
            "ocr_charged": False,
            "image_charged": False,
            "explanation_charged": False,
            "ocr_text": "문제 2",
            "explanation": "해설 2",
            "styled_image_path": "styled-2.png",
        },
    ]

    preview = service.ensure_job_action_credits_available(
        make_user(),
        "job-123",
        ["ocr", "image_stylize", "explanation"],
        processing_type="service_api",
    )
    charged = service.consume_job_action_credits(
        make_user(),
        "job-123",
        ["ocr", "image_stylize", "explanation"],
        processing_type="service_api",
    )

    assert preview["required_credits"] == 6
    assert charged["charged_actions"] == [
        "ocr",
        "image_stylize",
        "explanation",
        "ocr",
        "image_stylize",
        "explanation",
    ]
    assert charged["credits_balance"] == 2
    assert [entry["reason"] for entry in store.ledger_entries[-6:]] == [
        "ocr_charge",
        "image_stylize_charge",
        "explanation_charge",
        "ocr_charge",
        "image_stylize_charge",
        "explanation_charge",
    ]


def test_consume_job_action_credits_skips_ocr_and_explanation_for_user_key():
    service, store, _ = make_service()
    store.profiles["user-123"] = BillingProfile(
        user_id="user-123",
        credits_balance=3,
        used_credits=0,
        openai_connected=True,
        openai_key_masked="sk-us••••7890",
    )
    store.job_regions["job-123"] = [
        {
            "region_id": "q1",
            "ocr_charged": False,
            "image_charged": False,
            "explanation_charged": False,
            "ocr_text": "문제 1",
            "explanation": "해설 1",
            "styled_image_path": "styled-1.png",
        },
        {
            "region_id": "q2",
            "ocr_charged": False,
            "image_charged": False,
            "explanation_charged": False,
            "ocr_text": "문제 2",
            "explanation": "해설 2",
            "styled_image_path": "styled-2.png",
        },
    ]

    preview = service.ensure_job_action_credits_available(
        make_user(),
        "job-123",
        ["ocr", "image_stylize", "explanation"],
        processing_type="user_api_key",
    )
    charged = service.consume_job_action_credits(
        make_user(),
        "job-123",
        ["ocr", "image_stylize", "explanation"],
        processing_type="user_api_key",
    )

    assert preview["required_credits"] == 2
    assert charged["charged_actions"] == ["image_stylize", "image_stylize"]
    assert charged["credits_balance"] == 1


def test_ensure_job_action_credits_available_falls_back_when_markdown_columns_are_missing():
    schema_compat_module._markdown_output_columns_available = None
    user = make_user()

    class SchemaFallbackClient:
        """Markdown 컬럼이 없는 배포 DB를 재현하는 테스트 클라이언트다."""

        def __init__(self) -> None:
            self.region_selects: list[str] = []

        def select(self, table: str, *, params: dict[str, object]) -> list[dict]:
            """과금 점검에 필요한 region row만 반환한다."""
            if table != "ocr_job_regions":
                raise AssertionError(f"unexpected table: {table}")
            select_value = str(params.get("select") or "")
            self.region_selects.append(select_value)
            if "problem_markdown" in select_value:
                raise SupabaseApiError(
                    'column problem_markdown does not exist in relation "ocr_job_regions"'
                )
            return [
                {
                    "region_key": "q1",
                    "ocr_text": "문제 1",
                    "mathml": None,
                    "explanation": "해설 1",
                    "styled_image_path": None,
                    "ocr_charged": False,
                    "image_charged": False,
                    "explanation_charged": False,
                }
            ]

    client = SchemaFallbackClient()
    store = object.__new__(SupabaseBillingStore)
    store._user_client = lambda current_user: client
    store._read_job_charge_state = lambda current_client, job_id: {"id": job_id, "status": "queued"}
    store.get_or_create_profile = lambda current_user: BillingProfile(
        user_id=current_user.user_id,
        credits_balance=5,
        used_credits=0,
        openai_connected=False,
        openai_key_masked=None,
    )

    preview = store.ensure_job_action_credits_available(
        user,
        "job-123",
        ["ocr", "explanation"],
        processing_type="service_api",
    )

    assert preview["required_credits"] == 2
    assert len(client.region_selects) == 2
    assert "problem_markdown" in client.region_selects[0]
    assert "problem_markdown" not in client.region_selects[1]


def test_ensure_job_region_credits_available_counts_only_uncharged_regions():
    service, store, _ = make_service()
    store.profiles["user-123"] = BillingProfile(
        user_id="user-123",
        credits_balance=3,
        used_credits=0,
        openai_connected=False,
        openai_key_masked=None,
    )
    store.job_regions["job-123"] = [
        {"region_id": "q1", "was_charged": False, "exportable": True},
        {"region_id": "q2", "was_charged": True, "exportable": True},
        {"region_id": "q3", "was_charged": False, "exportable": False},
    ]

    preview = service.ensure_job_region_credits_available(
        make_user(),
        "job-123",
        processing_type="service_api",
    )

    assert preview["required_credits"] == 2
    assert preview["credits_balance"] == 3


def test_consume_job_region_credits_charges_exportable_regions_only_once():
    service, store, _ = make_service()
    store.profiles["user-123"] = BillingProfile(
        user_id="user-123",
        credits_balance=5,
        used_credits=0,
        openai_connected=False,
        openai_key_masked=None,
    )
    store.job_regions["job-123"] = [
        {"region_id": "q1", "was_charged": False, "exportable": True},
        {"region_id": "q2", "was_charged": False, "exportable": True},
        {"region_id": "q3", "was_charged": False, "exportable": False},
    ]

    first = service.consume_job_region_credits(
        make_user(),
        "job-123",
        processing_type="service_api",
    )
    second = service.consume_job_region_credits(
        make_user(),
        "job-123",
        processing_type="service_api",
    )

    assert first["charged_count"] == 2
    assert first["credits_balance"] == 3
    assert second["charged_count"] == 0
    assert second["credits_balance"] == 3
    assert store.ledger_entries[-1]["reason"] == "ocr_success_charge"
    assert store.ledger_entries[-1]["delta"] == -2


def test_supabase_billing_store_grants_signup_bonus_for_first_profile(monkeypatch):
    """신규 profile 생성 시 무료 3크레딧과 signup bonus 원장을 함께 남긴다."""
    monkeypatch.setattr("app.billing.get_settings", lambda root_path: _build_auth_settings())
    store = SupabaseBillingStore(Path("."))
    user_client = RecordingSupabaseClient(select_rows={"profiles": []})
    admin_client = RecordingSupabaseClient()
    monkeypatch.setattr(store, "_user_client", lambda user: user_client)
    monkeypatch.setattr(store, "_billing_write_client", lambda: admin_client)

    profile = store.get_or_create_profile(make_user())

    profile_insert = next(
        entry for entry in user_client.operations if entry["method"] == "insert" and entry["table"] == "profiles"
    )
    ledger_insert = next(
        entry for entry in admin_client.operations if entry["method"] == "insert" and entry["table"] == "credit_ledger"
    )

    assert profile.credits_balance == 3
    assert profile_insert["payload"]["credits_balance"] == 3
    assert ledger_insert["payload"]["reason"] == "signup_bonus"
    assert ledger_insert["payload"]["delta"] == 3
    assert ledger_insert["payload"]["balance_after"] == 3


def test_supabase_billing_store_skips_signup_bonus_for_existing_profile(monkeypatch):
    """기존 profile이 있으면 signup bonus를 다시 적립하지 않는다."""
    monkeypatch.setattr("app.billing.get_settings", lambda root_path: _build_auth_settings())
    store = SupabaseBillingStore(Path("."))
    user_client = RecordingSupabaseClient(
        select_rows={
            "profiles": [
                {
                    "user_id": "user-123",
                    "credits_balance": 7,
                    "used_credits": 2,
                    "openai_connected": False,
                    "openai_key_masked": None,
                }
            ]
        }
    )
    admin_client = RecordingSupabaseClient()
    monkeypatch.setattr(store, "_user_client", lambda user: user_client)
    monkeypatch.setattr(store, "_billing_write_client", lambda: admin_client)

    profile = store.get_or_create_profile(make_user())

    assert profile.credits_balance == 7
    assert {entry["method"] for entry in user_client.operations} == {"select"}
    assert admin_client.operations == []


def test_supabase_billing_store_uses_admin_client_for_action_charge_writes(monkeypatch):
    monkeypatch.setattr(
        "app.billing.get_settings",
        lambda root_path: AppSettings(
            openai_api_key="sk-service-1234567890",
            openai_key_encryption_secret="encryption-secret",
            database_url=None,
            auth=AuthSettings(
                supabase_url="https://billing-test.supabase.co",
                supabase_anon_key="anon-key",
                supabase_jwt_secret=None,
                supabase_storage_bucket="ocr-assets",
                supabase_service_role_key="service-role-key",
            ),
            billing=BillingSettings(
                polar_access_token=None,
                polar_webhook_secret=None,
                polar_server="production",
                polar_product_single_id="prod_single",
                polar_product_starter_id="prod_starter",
                polar_product_pro_id="prod_pro",
            ),
        ),
    )
    store = SupabaseBillingStore(Path("."))
    user_client = RecordingSupabaseClient(
        select_rows={
            "profiles": [
                {
                    "user_id": "user-123",
                    "credits_balance": 5,
                    "used_credits": 1,
                    "openai_connected": False,
                    "openai_key_masked": None,
                }
            ],
            "ocr_jobs": [{"id": "job-123", "status": "completed", "processing_type": "service_api"}],
            "ocr_job_regions": [
                {
                    "region_key": "q1",
                    "ocr_text": "문제 1",
                    "mathml": None,
                    "explanation": "해설 1",
                    "styled_image_path": "styled-1.png",
                    "ocr_charged": False,
                    "image_charged": False,
                    "explanation_charged": False,
                }
            ],
        }
    )
    admin_client = RecordingSupabaseClient()
    monkeypatch.setattr(store, "_user_client", lambda user: user_client)
    monkeypatch.setattr(store, "_admin_client", lambda: admin_client)

    charged = store.consume_job_action_credits(
        make_user(),
        "job-123",
        ["ocr", "image_stylize", "explanation"],
        processing_type="service_api",
    )

    assert charged["charged_count"] == 3
    assert charged["credits_balance"] == 2
    assert {entry["method"] for entry in user_client.operations} == {"select"}
    assert all(entry["method"] != "select" for entry in admin_client.operations)
    assert [entry["table"] for entry in admin_client.operations if entry["method"] == "insert"] == [
        "credit_ledger",
        "credit_ledger",
        "credit_ledger",
    ]
    assert [entry["table"] for entry in admin_client.operations if entry["method"] == "update"] == [
        "profiles",
        "ocr_job_regions",
        "ocr_job_regions",
        "ocr_job_regions",
        "ocr_jobs",
    ]


def test_supabase_billing_store_uses_admin_client_for_region_charge_writes(monkeypatch):
    monkeypatch.setattr(
        "app.billing.get_settings",
        lambda root_path: AppSettings(
            openai_api_key="sk-service-1234567890",
            openai_key_encryption_secret="encryption-secret",
            database_url=None,
            auth=AuthSettings(
                supabase_url="https://billing-test.supabase.co",
                supabase_anon_key="anon-key",
                supabase_jwt_secret=None,
                supabase_storage_bucket="ocr-assets",
                supabase_service_role_key="service-role-key",
            ),
            billing=BillingSettings(
                polar_access_token=None,
                polar_webhook_secret=None,
                polar_server="production",
                polar_product_single_id="prod_single",
                polar_product_starter_id="prod_starter",
                polar_product_pro_id="prod_pro",
            ),
        ),
    )
    store = SupabaseBillingStore(Path("."))
    user_client = RecordingSupabaseClient(
        select_rows={
            "profiles": [
                {
                    "user_id": "user-123",
                    "credits_balance": 4,
                    "used_credits": 0,
                    "openai_connected": False,
                    "openai_key_masked": None,
                }
            ],
            "ocr_jobs": [{"id": "job-123", "status": "completed"}],
            "ocr_job_regions": [
                {
                    "region_key": "q1",
                    "status": "completed",
                    "ocr_text": "문제 1",
                    "explanation": "해설 1",
                    "was_charged": False,
                }
            ],
        }
    )
    admin_client = RecordingSupabaseClient()
    monkeypatch.setattr(store, "_user_client", lambda user: user_client)
    monkeypatch.setattr(store, "_admin_client", lambda: admin_client)

    charged = store.consume_job_region_credits(
        make_user(),
        "job-123",
        processing_type="service_api",
    )

    assert charged["charged_count"] == 1
    assert charged["credits_balance"] == 3
    assert {entry["method"] for entry in user_client.operations} == {"select"}
    assert all(entry["method"] != "select" for entry in admin_client.operations)
    assert [entry["table"] for entry in admin_client.operations if entry["method"] == "insert"] == ["credit_ledger"]
    assert [entry["table"] for entry in admin_client.operations if entry["method"] == "update"] == [
        "profiles",
        "ocr_job_regions",
    ]


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

    client = TestClient(app, raise_server_exceptions=False)
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

    client = TestClient(app, raise_server_exceptions=False)
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

    client = TestClient(app, raise_server_exceptions=False)
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

    client = TestClient(app, raise_server_exceptions=False)
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


def test_auto_detect_regions_uses_one_time_job_credit_methods(monkeypatch):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user
    recorded_calls: dict[str, dict] = {}

    class StubBillingService:
        """자동 분할 API가 job 단위 1회 과금 메서드를 호출하는지 기록한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            assert current_user.user_id == user.user_id
            return type(
                "ResolvedKey",
                (),
                {
                    "api_key": "sk-service-1234567890",
                    "processing_type": "service_api",
                },
            )()

        def ensure_job_auto_detect_credits_available(self, current_user: AuthenticatedUser, job_id: str) -> dict:
            recorded_calls["ensure"] = {"user_id": current_user.user_id, "job_id": job_id}
            return {"required_credits": 1, "credits_balance": 5}

        def consume_job_auto_detect_credits(self, current_user: AuthenticatedUser, job_id: str) -> dict:
            recorded_calls["consume"] = {"user_id": current_user.user_id, "job_id": job_id}
            return {"charged": True, "charged_count": 1, "credits_balance": 4}

    def fake_auto_detect_regions(*args, **kwargs):
        assert kwargs["api_key"] == "sk-service-1234567890"
        return {
            "detected_count": 2,
            "review_required": True,
            "detector_model": "gpt-test",
            "detection_version": "openai_five_choice_v1",
        }

    def fake_read_job(current_user: AuthenticatedUser, job_id: str):
        return main_module.pipeline.JobPipelineContext(
            job_id=job_id,
            file_name="sample.png",
            image_url="user-123/job-123/input/sample.png",
            image_width=120,
            image_height=160,
            processing_type="service_api",
            status="queued",
            created_at="2026-04-13T00:00:00+00:00",
            updated_at="2026-04-13T00:00:00+00:00",
            regions=[
                main_module.pipeline.RegionPipelineContext(
                    context=main_module.pipeline.RegionContext(
                        id="q1",
                        polygon=[[0, 0], [10, 0], [10, 10], [0, 10]],
                        type="mixed",
                        order=1,
                        selection_mode="auto_detected",
                        input_device="system",
                        warning_level="normal",
                        auto_detect_confidence=0.91,
                    ),
                    status="pending",
                )
            ],
        )

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "auto_detect_regions", fake_auto_detect_regions)
    monkeypatch.setattr(main_module.pipeline, "read_job", fake_read_job)
    monkeypatch.setattr(
        main_module.pipeline,
        "create_asset_url",
        lambda current_user, storage_path, expires_in=3600: f"https://signed.example/{storage_path}",
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/jobs/job-123/regions/auto-detect")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert recorded_calls["ensure"] == {"user_id": "user-123", "job_id": "job-123"}
    assert recorded_calls["consume"] == {"user_id": "user-123", "job_id": "job-123"}
    assert response.json()["detected_count"] == 2
    assert response.json()["charged_count"] == 1
    assert response.json()["regions"][0]["selection_mode"] == "auto_detected"
    assert response.json()["regions"][0]["auto_detect_confidence"] == 0.91


def test_run_pipeline_uses_action_credit_methods(monkeypatch):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user
    recorded_calls: dict[str, dict] = {}

    class StubBillingService:
        """run API가 액션 기반 과금 메서드를 호출하는지 기록한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            """서비스 API 모드의 OpenAI key 해석 결과를 돌려준다."""
            assert current_user.user_id == user.user_id
            return type(
                "ResolvedKey",
                (),
                {
                    "api_key": "sk-service-1234567890",
                    "processing_type": "service_api",
                },
            )()

        def ensure_job_action_credits_available(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """실행 전 액션 기반 선차감 검증 호출을 기록한다."""
            recorded_calls["ensure"] = {
                "user_id": current_user.user_id,
                "job_id": job_id,
                "actions": actions,
                "processing_type": processing_type,
            }
            return {"required_credits": len(actions), "credits_balance": 5}

        def consume_job_action_credits(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """실행 후 액션 기반 후차감 호출을 기록한다."""
            recorded_calls["consume"] = {
                "user_id": current_user.user_id,
                "job_id": job_id,
                "actions": actions,
                "processing_type": processing_type,
            }
            return {"charged_actions": actions, "credits_balance": 3}

    def fake_run_pipeline(*args, **kwargs):
        """파이프라인 실행 결과를 최소 응답 형식으로 대체한다."""
        assert kwargs["do_ocr"] is True
        assert kwargs["do_image_stylize"] is True
        assert kwargs["do_explanation"] is False
        return {
            "job_id": args[1],
            "status": "completed",
            "executed_actions": ["ocr", "image_stylize"],
            "completed_count": 1,
            "failed_count": 0,
            "exportable_count": 1,
        }

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "run_pipeline", fake_run_pipeline)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/jobs/job-123/run",
        json={
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": False,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert recorded_calls["ensure"] == {
        "user_id": "user-123",
        "job_id": "job-123",
        "actions": ["ocr", "image_stylize"],
        "processing_type": "service_api",
    }
    assert recorded_calls["consume"] == {
        "user_id": "user-123",
        "job_id": "job-123",
        "actions": ["ocr", "image_stylize"],
        "processing_type": "service_api",
    }
    assert response.json()["charged_count"] == 2


def test_run_pipeline_returns_schema_mismatch_detail_for_supabase_error(monkeypatch):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user

    class StubBillingService:
        """액션 과금 선검증에서 스키마 드리프트 오류를 재현한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            """서비스 API 모드의 OpenAI key를 반환한다."""
            assert current_user.user_id == user.user_id
            return type(
                "ResolvedKey",
                (),
                {
                    "api_key": "sk-service-1234567890",
                    "processing_type": "service_api",
                },
            )()

        def ensure_job_action_credits_available(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """배포 DB 스키마 누락 상황을 그대로 던진다."""
            raise SupabaseApiError('column ocr_charged does not exist in relation "ocr_job_regions"')

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/jobs/job-123/run",
        json={
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": False,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "배포 DB 스키마가 최신이 아닙니다."


def test_run_pipeline_returns_storage_failure_detail_for_supabase_error(monkeypatch):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user

    class StubBillingService:
        """후차감 단계의 Supabase 연결 실패를 재현한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            """서비스 API 모드의 OpenAI key를 반환한다."""
            assert current_user.user_id == user.user_id
            return type(
                "ResolvedKey",
                (),
                {
                    "api_key": "sk-service-1234567890",
                    "processing_type": "service_api",
                },
            )()

        def ensure_job_action_credits_available(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """선차감 검증은 정상 응답으로 둔다."""
            return {"required_credits": 2, "credits_balance": 5}

        def consume_job_action_credits(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """후차감 시 저장소 장애를 재현한다."""
            raise SupabaseApiError("temporary storage timeout")

    def fake_run_pipeline(*args, **kwargs):
        """파이프라인 실행 자체는 성공으로 둔다."""
        return {
            "job_id": args[1],
            "status": "completed",
            "executed_actions": ["ocr", "image_stylize"],
            "completed_count": 1,
            "failed_count": 0,
            "exportable_count": 1,
        }

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "run_pipeline", fake_run_pipeline)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/jobs/job-123/run",
        json={
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": False,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "서버 저장소 연결에 실패했습니다. 잠시 후 다시 시도하세요."


def test_run_pipeline_returns_billing_persistence_detail_for_rls_error(monkeypatch):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user

    class StubBillingService:
        """후차감 단계의 billing RLS 오류를 재현한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            """서비스 API 모드의 OpenAI key를 반환한다."""
            assert current_user.user_id == user.user_id
            return type(
                "ResolvedKey",
                (),
                {
                    "api_key": "sk-service-1234567890",
                    "processing_type": "service_api",
                },
            )()

        def ensure_job_action_credits_available(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """선차감 검증은 정상 응답으로 둔다."""
            return {"required_credits": 2, "credits_balance": 5}

        def consume_job_action_credits(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """후차감 시 billing persistence 오류를 재현한다."""
            raise SupabaseApiError(
                '{"code":"42501","details":null,"hint":null,"message":"new row violates row-level security policy for table \\"credit_ledger\\""}'
            )

    def fake_run_pipeline(*args, **kwargs):
        """파이프라인 실행 자체는 성공으로 둔다."""
        return {
            "job_id": args[1],
            "status": "completed",
            "executed_actions": ["ocr", "image_stylize"],
            "completed_count": 1,
            "failed_count": 0,
            "exportable_count": 1,
        }

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "run_pipeline", fake_run_pipeline)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/jobs/job-123/run",
        json={
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": False,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "서버 과금 기록 저장에 실패했습니다. 잠시 후 다시 시도하세요."


def test_run_pipeline_returns_billing_config_detail_for_missing_service_role(monkeypatch):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user

    class StubBillingService:
        """후차감 단계의 service role 설정 누락을 재현한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            """서비스 API 모드의 OpenAI key를 반환한다."""
            assert current_user.user_id == user.user_id
            return type(
                "ResolvedKey",
                (),
                {
                    "api_key": "sk-service-1234567890",
                    "processing_type": "service_api",
                },
            )()

        def ensure_job_action_credits_available(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """선차감 검증은 정상 응답으로 둔다."""
            return {"required_credits": 2, "credits_balance": 5}

        def consume_job_action_credits(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """service role 누락 설정 오류를 재현한다."""
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for billing writes")

    def fake_run_pipeline(*args, **kwargs):
        """파이프라인 실행 자체는 성공으로 둔다."""
        return {
            "job_id": args[1],
            "status": "completed",
            "executed_actions": ["ocr", "image_stylize"],
            "completed_count": 1,
            "failed_count": 0,
            "exportable_count": 1,
        }

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "run_pipeline", fake_run_pipeline)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/jobs/job-123/run",
        json={
            "do_ocr": True,
            "do_image_stylize": True,
            "do_explanation": False,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "서버 과금 설정이 완료되지 않았습니다."


def test_run_pipeline_returns_user_openai_key_detail_for_missing_secret(monkeypatch):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user

    class StubBillingService:
        """사용자 OpenAI key 복호화 설정 누락을 재현한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            """암호화 secret 누락 오류를 던진다."""
            raise ValueError("OPENAI_KEY_ENCRYPTION_SECRET is not configured")

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())

    client = TestClient(app)
    response = client.post(
        "/jobs/job-123/run",
        json={
            "do_ocr": True,
            "do_image_stylize": False,
            "do_explanation": False,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "사용자 OpenAI 키 설정이 완료되지 않았습니다."


@pytest.mark.parametrize(
    "error_message",
    [
        "NANO_BANANA_MODEL is not configured",
        "GEMINI_API_KEY is not configured",
        "Unsupported NANO_BANANA_PROVIDER: invalid-provider",
    ],
)
def test_run_pipeline_returns_image_config_detail_for_image_provider_misconfiguration(
    monkeypatch,
    error_message: str,
):
    user = make_user()
    app.dependency_overrides[require_authenticated_user] = lambda: user

    class StubBillingService:
        """이미지 생성 단계 진입 전 검증을 정상 처리한다."""

        def resolve_openai_api_key(self, current_user: AuthenticatedUser):
            """서비스 API 모드의 OpenAI key를 반환한다."""
            return type(
                "ResolvedKey",
                (),
                {
                    "api_key": "sk-service-1234567890",
                    "processing_type": "service_api",
                },
            )()

        def ensure_job_action_credits_available(
            self,
            current_user: AuthenticatedUser,
            job_id: str,
            actions: list[str],
            *,
            processing_type: str,
        ) -> dict:
            """선차감 검증은 정상 응답으로 둔다."""
            return {"required_credits": 1, "credits_balance": 5}

    def fake_run_pipeline(*args, **kwargs):
        """Nano Banana 설정 누락 예외를 직접 재현한다."""
        raise ValueError(error_message)

    monkeypatch.setattr(main_module, "_get_billing_service", lambda require_polar=False: StubBillingService())
    monkeypatch.setattr(main_module.pipeline, "run_pipeline", fake_run_pipeline)

    client = TestClient(app)
    response = client.post(
        "/jobs/job-123/run",
        json={
            "do_ocr": False,
            "do_image_stylize": True,
            "do_explanation": False,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "이미지 생성 서버 설정이 완료되지 않았습니다."


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


def test_polar_gateway_create_checkout_presets_kr_billing_country(monkeypatch):
    class FakeCheckoutsClient:
        """checkout 생성 요청 payload를 기록한다."""

        def __init__(self) -> None:
            self.request = None

        def create(self, *, request):
            """생성 요청을 저장하고 최소 응답을 돌려준다."""
            self.request = request
            return type(
                "FakeCheckout",
                (),
                {
                    "id": "chk_live_123",
                    "url": "https://polar.sh/checkout/chk_live_123",
                    "status": "open",
                },
            )()

    class FakePolarClient:
        """checkouts client만 노출하는 테스트용 Polar 클라이언트다."""

        def __init__(self) -> None:
            self.checkouts = FakeCheckoutsClient()

    fake_client = FakePolarClient()
    monkeypatch.setattr("app.billing.Polar", lambda access_token, server: fake_client)

    gateway = PolarGateway(
        access_token="polar-token",
        webhook_secret="whsec-test",
        server="production",
    )

    result = gateway.create_checkout(
        external_customer_id="user-123",
        plan=BillingPlan(
            plan_id="single",
            product_id="prod_single",
            title="Single",
            amount=100,
            currency="krw",
            credits=1,
        ),
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )

    request = fake_client.checkouts.request
    assert request is not None
    assert request.require_billing_address is True
    assert request.customer_billing_address is not None
    assert getattr(request.customer_billing_address.country, "value", request.customer_billing_address.country) == "KR"
    assert result["id"] == "chk_live_123"


def test_polar_gateway_get_checkout_returns_diagnostics(monkeypatch):
    class FakeCheckoutsClient:
        """checkout 조회 응답을 고정 값으로 반환한다."""

        def get(self, *, id: str):
            """진단 필드가 포함된 checkout 응답을 돌려준다."""
            return type(
                "FakeCheckout",
                (),
                {
                    "id": id,
                    "status": "open",
                    "payment_processor": "stripe",
                    "is_payment_required": True,
                    "is_payment_form_required": False,
                    "customer_billing_address": type(
                        "FakeAddress",
                        (),
                        {
                            "country": "KR",
                            "line1": None,
                            "line2": None,
                            "postal_code": None,
                            "city": None,
                            "state": None,
                        },
                    )(),
                    "billing_address_fields": type(
                        "FakeAddressFields",
                        (),
                        {
                            "country": "required",
                            "state": "disabled",
                            "city": "disabled",
                            "postal_code": "disabled",
                            "line1": "disabled",
                            "line2": "disabled",
                        },
                    )(),
                    "currency": "krw",
                    "amount": 100,
                    "product_id": "prod_single",
                    "product_price_id": "price_single",
                },
            )()

    class FakePolarClient:
        """checkouts client만 노출하는 테스트용 Polar 클라이언트다."""

        def __init__(self) -> None:
            self.checkouts = FakeCheckoutsClient()

    monkeypatch.setattr("app.billing.Polar", lambda access_token, server: FakePolarClient())

    gateway = PolarGateway(
        access_token="polar-token",
        webhook_secret="whsec-test",
        server="production",
    )

    checkout = gateway.get_checkout("chk_live_123")

    assert checkout["payment_processor"] == "stripe"
    assert checkout["is_payment_required"] is True
    assert checkout["is_payment_form_required"] is False
    assert checkout["customer_billing_address"] == {
        "country": "KR",
        "line1": None,
        "line2": None,
        "postal_code": None,
        "city": None,
        "state": None,
    }
    assert checkout["billing_address_fields"]["country"] == "required"
    assert checkout["product_id"] == "prod_single"
    assert checkout["product_price_id"] == "price_single"


def test_polar_gateway_get_checkout_normalizes_undefined_optional_fields(monkeypatch):
    class FakeCheckoutsClient:
        """optional 진단 필드가 undefined 인 checkout을 반환한다."""

        def get(self, *, id: str):
            """address 내부 일부 필드를 undefined 로 둔다."""
            return type(
                "FakeCheckout",
                (),
                {
                    "id": id,
                    "status": "open",
                    "payment_processor": "stripe",
                    "is_payment_required": True,
                    "is_payment_form_required": True,
                    "customer_billing_address": type(
                        "FakeAddress",
                        (),
                        {
                            "country": "KR",
                            "line1": PydanticUndefined,
                            "line2": PydanticUndefined,
                            "postal_code": PydanticUndefined,
                            "city": PydanticUndefined,
                            "state": PydanticUndefined,
                        },
                    )(),
                    "billing_address_fields": type(
                        "FakeAddressFields",
                        (),
                        {
                            "country": "required",
                            "state": PydanticUndefined,
                            "city": PydanticUndefined,
                            "postal_code": PydanticUndefined,
                            "line1": PydanticUndefined,
                            "line2": PydanticUndefined,
                        },
                    )(),
                    "currency": "krw",
                    "amount": 100,
                    "product_id": "prod_single",
                    "product_price_id": "price_single",
                },
            )()

    class FakePolarClient:
        """checkouts client만 노출하는 테스트용 Polar 클라이언트다."""

        def __init__(self) -> None:
            self.checkouts = FakeCheckoutsClient()

    monkeypatch.setattr("app.billing.Polar", lambda access_token, server: FakePolarClient())

    gateway = PolarGateway(
        access_token="polar-token",
        webhook_secret="whsec-test",
        server="production",
    )

    checkout = gateway.get_checkout("chk_live_undefined")

    assert checkout["customer_billing_address"]["line1"] is None
    assert checkout["billing_address_fields"]["state"] is None


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
