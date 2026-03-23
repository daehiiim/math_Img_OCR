from __future__ import annotations

from typing import Any

from app.supabase import SupabaseApiError

MARKDOWN_OUTPUT_COLUMN_NAMES = (
    "problem_markdown",
    "explanation_markdown",
    "markdown_version",
)

_markdown_output_columns_available: bool | None = None


def should_use_markdown_output_columns() -> bool:
    """현재 프로세스가 Markdown 산출 컬럼을 시도해도 되는지 반환한다."""
    return _markdown_output_columns_available is not False


def remember_markdown_output_columns_available(is_available: bool) -> None:
    """관측된 Markdown 산출 컬럼 지원 여부를 프로세스 전역에 기억한다."""
    global _markdown_output_columns_available
    _markdown_output_columns_available = is_available


def is_markdown_output_schema_error(error: Exception) -> bool:
    """Markdown 산출 컬럼이 없는 구스키마 오류인지 판별한다."""
    if not isinstance(error, SupabaseApiError):
        return False
    normalized = str(error).lower()
    return any(column in normalized for column in MARKDOWN_OUTPUT_COLUMN_NAMES)


def strip_markdown_output_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """구스키마 저장용 payload에서 Markdown 산출 필드를 제거한다."""
    return {
        key: value
        for key, value in payload.items()
        if key not in MARKDOWN_OUTPUT_COLUMN_NAMES
    }
