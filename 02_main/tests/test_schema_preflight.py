import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import AppSettings, AuthSettings, BillingSettings
from app.schema_preflight import (
    build_next_steps,
    build_runtime_schema_checks,
    collect_schema_preflight_checks,
    has_blocking_failures,
)


class StubResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def make_settings() -> AppSettings:
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
            polar_access_token=None,
            polar_webhook_secret=None,
            polar_server=None,
            polar_product_single_id=None,
            polar_product_starter_id=None,
            polar_product_pro_id=None,
        ),
    )


def test_build_runtime_schema_checks_reports_fail_for_missing_auto_detect_columns():
    def requester(url: str, *, headers: dict, params: dict, timeout: int):
        if "ocr_jobs" in url:
            return StubResponse(400, text="column auto_detect_charged does not exist")
        return StubResponse(200)

    checks = build_runtime_schema_checks(
        make_settings(),
        requester=requester,
    )

    job_check = next(check for check in checks if check.key == "schema.ocr_jobs_runtime")
    assert job_check.status == "fail"
    assert "2026-04-13_auto_detect_regions.sql" in job_check.detail


def test_collect_schema_preflight_checks_includes_env_and_runtime_checks():
    checks = collect_schema_preflight_checks(
        settings=make_settings(),
        requester=lambda *args, **kwargs: StubResponse(200),
    )

    keys = {check.key for check in checks}
    assert "env.supabase_url" in keys
    assert "schema.ocr_jobs_runtime" in keys
    assert "schema.ocr_job_regions_runtime" in keys


def test_build_next_steps_points_to_runtime_migrations_when_schema_check_fails():
    checks = collect_schema_preflight_checks(
        settings=make_settings(),
        requester=lambda *args, **kwargs: StubResponse(400, text="column selection_mode does not exist"),
    )

    steps = build_next_steps(checks)

    assert steps == [
        "Supabase SQL Editor에서 2026-04-13_markdown_first_hwpx_v2.sql, 2026-03-19_region_action_credit_flags.sql, 2026-04-13_auto_detect_regions.sql 을 순서대로 적용합니다.",
        "적용 후 py scripts/schema_preflight.py 를 다시 실행해 schema.ocr_jobs_runtime, schema.ocr_job_regions_runtime 가 모두 OK 인지 확인합니다.",
    ]
    assert has_blocking_failures(checks) is True
