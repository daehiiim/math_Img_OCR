from __future__ import annotations

from typing import Any

from app.supabase import SupabaseApiError

OPTIONAL_REGION_COLUMN_NAMES = (
    "problem_markdown",
    "explanation_markdown",
    "markdown_version",
    "raw_transcript",
    "ordered_segments",
    "question_type",
    "parsed_choices",
    "resolved_answer_index",
    "resolved_answer_value",
    "answer_confidence",
    "verification_status",
    "verification_warnings",
    "reason_summary",
)
OPTIONAL_REGION_METADATA_COLUMN_NAMES = (
    "selection_mode",
    "input_device",
    "warning_level",
    "auto_detect_confidence",
)

_markdown_output_columns_available: bool | None = None
_region_metadata_columns_available: bool | None = None


def should_use_markdown_output_columns() -> bool:
    """현재 프로세스가 Markdown 산출 컬럼을 시도해도 되는지 반환한다."""
    return _markdown_output_columns_available is not False


def remember_markdown_output_columns_available(is_available: bool) -> None:
    """관측된 Markdown 산출 컬럼 지원 여부를 프로세스 전역에 기억한다."""
    global _markdown_output_columns_available
    _markdown_output_columns_available = is_available


def should_use_region_metadata_columns() -> bool:
    """현재 프로세스가 region 메타 컬럼을 시도해도 되는지 반환한다."""
    return _region_metadata_columns_available is not False


def remember_region_metadata_columns_available(is_available: bool) -> None:
    """관측된 region 메타 컬럼 지원 여부를 프로세스 전역에 기억한다."""
    global _region_metadata_columns_available
    _region_metadata_columns_available = is_available


def is_markdown_output_schema_error(error: Exception) -> bool:
    """확장 region 컬럼이 없는 구스키마 오류인지 판별한다."""
    if not isinstance(error, SupabaseApiError):
        return False
    normalized = str(error).lower()
    return any(column in normalized for column in OPTIONAL_REGION_COLUMN_NAMES)


def strip_markdown_output_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """구스키마 저장용 payload에서 확장 region 필드를 제거한다."""
    return {
        key: value
        for key, value in payload.items()
        if key not in OPTIONAL_REGION_COLUMN_NAMES
    }


def is_region_metadata_schema_error(error: Exception) -> bool:
    """region 메타 컬럼이 없는 구스키마 오류인지 판별한다."""
    if not isinstance(error, SupabaseApiError):
        return False
    normalized = str(error).lower()
    return any(column in normalized for column in OPTIONAL_REGION_METADATA_COLUMN_NAMES)


def strip_region_metadata_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """구스키마 저장용 payload에서 region 메타 필드를 제거한다."""
    return {
        key: value
        for key, value in payload.items()
        if key not in OPTIONAL_REGION_METADATA_COLUMN_NAMES
    }
