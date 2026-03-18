import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import AppSettings, AuthSettings, BillingSettings
from app.polar_preflight import (
    PreflightCheck,
    build_next_steps,
    build_env_checks,
    check_billing_catalog,
    check_polar_products,
    check_supabase_payment_columns,
    collect_preflight_checks,
)


class StubResponse:
    def __init__(self, status_code: int, text: str = "", json_body=None) -> None:
        self.status_code = status_code
        self.text = text
        self._json_body = [] if json_body is None else json_body

    def json(self):
        return self._json_body


def make_settings(**billing_overrides) -> AppSettings:
    return AppSettings(
        openai_api_key=None,
        openai_key_encryption_secret=None,
        database_url=None,
        auth=AuthSettings(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
            supabase_jwt_secret="jwt-secret",
            supabase_storage_bucket="ocr-assets",
            supabase_service_role_key="service-role-key",
        ),
        billing=BillingSettings(
            polar_access_token=billing_overrides.get("polar_access_token", "polar-token"),
            polar_webhook_secret=billing_overrides.get("polar_webhook_secret", "whsec-123"),
            polar_server=billing_overrides.get("polar_server", "sandbox"),
            polar_product_single_id=billing_overrides.get("polar_product_single_id", "prod_single"),
            polar_product_starter_id=billing_overrides.get("polar_product_starter_id", "prod_starter"),
            polar_product_pro_id=billing_overrides.get("polar_product_pro_id", "prod_pro"),
        ),
    )


def test_build_env_checks_marks_missing_values_as_fail():
    settings = make_settings(
        polar_access_token=None,
        polar_webhook_secret=None,
        polar_product_single_id=None,
    )

    checks = build_env_checks(settings)

    statuses = {check.key: check.status for check in checks}
    assert statuses["env.polar_access_token"] == "fail"
    assert statuses["env.polar_webhook_secret"] == "fail"
    assert statuses["env.polar_product_single_id"] == "fail"
    assert statuses["env.supabase_service_role_key"] == "ok"


def test_build_env_checks_requires_sandbox_server_for_sandbox_flow():
    settings = make_settings(polar_server="production")

    checks = build_env_checks(settings)

    polar_server_check = next(check for check in checks if check.key == "env.polar_server")
    assert polar_server_check.status == "fail"
    assert "sandbox" in polar_server_check.detail


def test_build_env_checks_requires_production_server_for_live_flow():
    settings = make_settings(polar_server="sandbox")

    checks = build_env_checks(settings, billing_mode="production")

    polar_server_check = next(check for check in checks if check.key == "env.polar_server")
    assert polar_server_check.status == "fail"
    assert "production" in polar_server_check.detail


def test_check_supabase_payment_columns_reports_ok_on_success():
    def requester(url: str, *, headers: dict, params: dict, timeout: int):
        assert url == "https://example.supabase.co/rest/v1/payment_events"
        assert headers["apikey"] == "service-role-key"
        assert params["select"] == "provider,provider_event_id,provider_order_id,provider_checkout_id,provider_customer_id,currency"
        return StubResponse(200, json_body=[])

    check = check_supabase_payment_columns(
        "https://example.supabase.co",
        "service-role-key",
        requester=requester,
    )

    assert check.status == "ok"


def test_check_supabase_payment_columns_reports_fail_on_missing_columns():
    def requester(url: str, *, headers: dict, params: dict, timeout: int):
        return StubResponse(400, text="column provider_order_id does not exist")

    check = check_supabase_payment_columns(
        "https://example.supabase.co",
        "service-role-key",
        requester=requester,
    )

    assert check.status == "fail"
    assert "2026-03-16_polar_billing_upgrade.sql" in check.detail


def test_check_billing_catalog_reports_ok_on_success():
    def requester(url: str, *, timeout: int):
        assert url == "http://localhost:8000/billing/catalog"
        return StubResponse(
            200,
            json_body={
                "plans": [
                    {"plan_id": "single"},
                    {"plan_id": "starter"},
                    {"plan_id": "pro"},
                ]
            },
        )

    check = check_billing_catalog("http://localhost:8000", requester=requester)

    assert check.status == "ok"


def test_check_polar_products_reports_ok_for_valid_live_products():
    products = {
        "prod_single": {
            "id": "prod_single",
            "title": "Single",
            "amount": 1000,
            "currency": "krw",
            "metadata": {"plan_id": "single", "credits": "1"},
        },
        "prod_starter": {
            "id": "prod_starter",
            "title": "Starter",
            "amount": 19000,
            "currency": "krw",
            "metadata": {"plan_id": "starter", "credits": "100"},
        },
        "prod_pro": {
            "id": "prod_pro",
            "title": "Pro",
            "amount": 29000,
            "currency": "krw",
            "metadata": {"plan_id": "pro", "credits": "200"},
        },
    }

    checks = check_polar_products(
        make_settings(polar_server="production"),
        product_reader=lambda product_id: products[product_id],
    )

    assert [check.status for check in checks] == ["ok", "ok", "ok"]


def test_check_polar_products_reports_token_mismatch_from_production_reader():
    checks = check_polar_products(
        make_settings(polar_server="production"),
        product_reader=lambda product_id: (_ for _ in ()).throw(
            ValueError("POLAR_ACCESS_TOKEN does not match POLAR_SERVER")
        ),
    )

    assert checks[0].status == "fail"
    assert "POLAR_ACCESS_TOKEN does not match POLAR_SERVER" in checks[0].detail


def test_check_polar_products_reports_missing_metadata_and_currency_mismatch():
    products = {
        "prod_single": {
            "id": "prod_single",
            "title": "Single",
            "amount": 1000,
            "currency": "krw",
            "metadata": {"credits": "1"},
        },
        "prod_starter": {
            "id": "prod_starter",
            "title": "Starter",
            "amount": 19000,
            "currency": "usd",
            "metadata": {"plan_id": "starter", "credits": "100"},
        },
        "prod_pro": {
            "id": "prod_pro",
            "title": "Pro",
            "amount": 29000,
            "currency": "krw",
            "metadata": {"plan_id": "pro", "credits": "200"},
        },
    }

    checks = check_polar_products(
        make_settings(polar_server="production"),
        product_reader=lambda product_id: products[product_id],
    )

    assert checks[0].status == "fail"
    assert "missing plan_id metadata" in checks[0].detail
    assert checks[1].status == "fail"
    assert "product currency mismatch" in checks[1].detail


def test_collect_preflight_checks_warns_when_tunnel_binary_is_missing():
    checks = collect_preflight_checks(
        settings=make_settings(),
        requester=lambda *args, **kwargs: StubResponse(200, json_body=[]),
        which=lambda binary: None,
        api_base_url="http://localhost:8000",
    )

    tunnel_check = next(check for check in checks if check.key == "tool.tunnel")
    assert tunnel_check.status == "warn"
    assert "polar" in tunnel_check.detail


def test_collect_preflight_checks_accepts_polar_cli_as_tunnel_tool():
    checks = collect_preflight_checks(
        settings=make_settings(),
        requester=lambda *args, **kwargs: StubResponse(200, json_body=[]),
        which=lambda binary: "C:/tools/polar.exe" if binary == "polar" else None,
        api_base_url="http://localhost:8000",
    )

    tunnel_check = next(check for check in checks if check.key == "tool.tunnel")
    assert tunnel_check.status == "ok"
    assert "polar CLI" in tunnel_check.detail


def test_build_next_steps_only_mentions_current_blockers():
    checks = [
        PreflightCheck(key="env.supabase_service_role_key", status="ok", detail="설정됨"),
        PreflightCheck(key="env.supabase_jwt_secret", status="ok", detail="설정됨"),
        PreflightCheck(key="env.polar_access_token", status="fail", detail="값이 비어 있습니다."),
        PreflightCheck(key="env.polar_webhook_secret", status="fail", detail="값이 비어 있습니다."),
        PreflightCheck(key="env.polar_product_single_id", status="fail", detail="값이 비어 있습니다."),
        PreflightCheck(key="env.polar_product_starter_id", status="fail", detail="값이 비어 있습니다."),
        PreflightCheck(key="env.polar_product_pro_id", status="fail", detail="값이 비어 있습니다."),
        PreflightCheck(key="tool.tunnel", status="warn", detail="ngrok 없음"),
        PreflightCheck(key="supabase.payment_events_columns", status="ok", detail="조회 가능"),
    ]

    steps = build_next_steps(checks)

    assert steps == [
        "https://sandbox.polar.sh 에 로그인하고 sandbox 전용 Access Token, 상품 3개, webhook secret을 준비합니다.",
        "ngrok, polar CLI, cloudflared 중 하나를 준비해 localhost:8000 을 외부 HTTPS로 노출합니다.",
    ]
