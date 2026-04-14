from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

from app.config import AppSettings, get_settings

ROOT = Path(__file__).resolve().parents[1]
Requester = Callable[..., Any]


@dataclass(frozen=True)
class SchemaPreflightCheck:
    """런타임 스키마 사전점검의 단일 결과를 표현한다."""

    key: str
    status: str
    detail: str


@dataclass(frozen=True)
class RuntimeSchemaTarget:
    """같은 테이블에서 함께 점검할 런타임 컬럼 묶음을 표현한다."""

    key: str
    table: str
    select: str
    guidance: str


RUNTIME_SCHEMA_TARGETS = (
    RuntimeSchemaTarget(
        key="schema.ocr_jobs_runtime",
        table="ocr_jobs",
        select="was_charged,charged_at,auto_detect_charged,auto_detect_charged_at",
        guidance="2026-03-19_region_action_credit_flags.sql, 2026-04-13_auto_detect_regions.sql",
    ),
    RuntimeSchemaTarget(
        key="schema.ocr_job_regions_runtime",
        table="ocr_job_regions",
        select=(
            "ocr_charged,image_charged,explanation_charged,image_crop_path,styled_image_path,"
            "styled_image_model,problem_markdown,explanation_markdown,markdown_version,raw_transcript,"
            "ordered_segments,question_type,parsed_choices,resolved_answer_index,resolved_answer_value,"
            "answer_confidence,verification_status,verification_warnings,reason_summary,selection_mode,"
            "input_device,warning_level,auto_detect_confidence"
        ),
        guidance=(
            "2026-03-19_region_action_credit_flags.sql, "
            "2026-04-13_markdown_first_hwpx_v2.sql, "
            "2026-04-13_auto_detect_regions.sql"
        ),
    ),
)


def _ok(key: str, detail: str) -> SchemaPreflightCheck:
    """성공 점검 결과를 만든다."""
    return SchemaPreflightCheck(key=key, status="ok", detail=detail)


def _warn(key: str, detail: str) -> SchemaPreflightCheck:
    """경고 점검 결과를 만든다."""
    return SchemaPreflightCheck(key=key, status="warn", detail=detail)


def _fail(key: str, detail: str) -> SchemaPreflightCheck:
    """실패 점검 결과를 만든다."""
    return SchemaPreflightCheck(key=key, status="fail", detail=detail)


def build_env_checks(settings: AppSettings) -> list[SchemaPreflightCheck]:
    """스키마 점검에 필요한 필수 환경변수를 확인한다."""
    checks: list[SchemaPreflightCheck] = []
    for key, value in (
        ("env.supabase_url", settings.auth.supabase_url),
        ("env.supabase_service_role_key", settings.auth.supabase_service_role_key),
    ):
        checks.append(_ok(key, "설정됨") if value else _fail(key, "값이 비어 있습니다. 환경변수를 채워야 합니다."))
    return checks


def check_runtime_schema_target(
    supabase_url: str,
    service_role_key: str,
    target: RuntimeSchemaTarget,
    requester: Requester = requests.get,
) -> SchemaPreflightCheck:
    """단일 런타임 컬럼 묶음이 REST 경로에서 조회 가능한지 점검한다."""
    try:
        response = requester(
            f"{supabase_url.rstrip('/')}/rest/v1/{target.table}",
            headers={"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}"},
            params={"select": target.select, "limit": "1"},
            timeout=15,
        )
    except Exception as error:
        return _fail(target.key, f"REST 확인 실패: {error}")
    if response.status_code == 200:
        return _ok(target.key, f"{target.table} 런타임 컬럼 조회가 가능합니다.")
    reason = f" ({str(response.text or '').strip()})" if str(response.text or "").strip() else ""
    return _fail(target.key, f"{target.table} 런타임 컬럼 확인에 실패했습니다{reason}. {target.guidance} 적용 여부를 점검하세요.")


def build_runtime_schema_checks(
    settings: AppSettings,
    requester: Requester = requests.get,
) -> list[SchemaPreflightCheck]:
    """현재 백엔드가 전제하는 런타임 컬럼 묶음을 점검한다."""
    supabase_url = settings.auth.supabase_url
    service_role_key = settings.auth.supabase_service_role_key
    if not supabase_url or not service_role_key:
        return [_warn("schema.runtime", "Supabase 연결 정보가 없어서 런타임 컬럼 점검을 건너뜁니다.")]
    return [
        check_runtime_schema_target(supabase_url, service_role_key, target, requester=requester)
        for target in RUNTIME_SCHEMA_TARGETS
    ]


def collect_schema_preflight_checks(
    *,
    settings: AppSettings | None = None,
    root_path: Path | None = None,
    requester: Requester = requests.get,
) -> list[SchemaPreflightCheck]:
    """환경변수와 런타임 컬럼 점검 결과를 한 번에 모은다."""
    resolved_settings = settings or get_settings(root_path or ROOT)
    return [
        *build_env_checks(resolved_settings),
        *build_runtime_schema_checks(resolved_settings, requester=requester),
    ]


def build_next_steps(checks: list[SchemaPreflightCheck]) -> list[str]:
    """현재 실패 상태를 기준으로 다음 작업을 제안한다."""
    status_by_key = {check.key: check.status for check in checks}
    steps: list[str] = []
    if any(status_by_key.get(key) == "fail" for key in ("env.supabase_url", "env.supabase_service_role_key")):
        steps.append("Cloud Run 또는 로컬 .env 에 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 를 먼저 채웁니다.")
    if any(key.startswith("schema.ocr_") and status == "fail" for key, status in status_by_key.items()):
        steps.append("Supabase SQL Editor에서 2026-03-19_region_action_credit_flags.sql, 2026-04-13_markdown_first_hwpx_v2.sql, 2026-04-13_auto_detect_regions.sql 을 순서대로 적용합니다.")
        steps.append("적용 후 py scripts/schema_preflight.py 를 다시 실행해 schema.ocr_jobs_runtime, schema.ocr_job_regions_runtime 가 모두 OK 인지 확인합니다.")
    if not steps:
        steps.append("배포 전 py scripts/schema_preflight.py 를 실행해 현재 런타임 스키마 호환성을 다시 확인합니다.")
    return steps


def has_blocking_failures(checks: list[SchemaPreflightCheck]) -> bool:
    """즉시 막히는 실패 항목이 있는지 반환한다."""
    return any(check.status == "fail" for check in checks)
