from __future__ import annotations

import re
from typing import Any

from app.pipeline.hwpx_math_layout import normalize_hwp_equation_script

MARKDOWN_VERSION = "mathocr_markdown_latex_v2"
LEGACY_MATH_TAG_PATTERN = re.compile(r"<math>(.*?)</math>", re.DOTALL)
DISPLAY_MATH_PATTERN = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
INLINE_MATH_PATTERN = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)


def _normalize_markdown_lines(value: str) -> str | None:
    """줄 끝 공백만 정리한 뒤 비어 있으면 `None`을 반환한다."""
    normalized = "\n".join(line.rstrip() for line in value.splitlines()).strip()
    return normalized or None


def _normalize_segment_order(raw_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """ordered segment를 source order 기준으로 안정적으로 정렬한다."""
    return sorted(raw_segments, key=lambda segment: int(segment.get("source_order", 0)))


def _wrap_markdown_math(formula: str) -> str:
    """LaTeX 수식을 Markdown 수식 구문으로 감싼다."""
    normalized_formula = str(formula or "").strip()
    if not normalized_formula:
        return ""
    if "\n" in normalized_formula:
        return f"$$\n{normalized_formula}\n$$"
    return f"${normalized_formula}$"


def _replace_legacy_math_tag(match: re.Match[str]) -> str:
    """기존 `<math>` 수식 태그를 Markdown 수식으로 바꾼다."""
    return _wrap_markdown_math(str(match.group(1) or ""))


def ordered_segments_to_markdown(raw_segments: list[dict[str, Any]] | None) -> str | None:
    """ordered segment 목록을 평문 보존형 Markdown 문자열로 직렬화한다."""
    if not raw_segments:
        return None
    markdown = "".join(
        _wrap_markdown_math(str(segment.get("content") or ""))
        if segment.get("type") == "math"
        else str(segment.get("content") or "")
        for segment in _normalize_segment_order(raw_segments)
    )
    return _normalize_markdown_lines(markdown)


def bridge_legacy_markup_to_markdown(value: str | None) -> str | None:
    """기존 `<math>` 기반 텍스트를 Markdown+LaTeX 표기로 변환한다."""
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    return _normalize_markdown_lines(LEGACY_MATH_TAG_PATTERN.sub(_replace_legacy_math_tag, raw_value))


def _wrap_hwp_math_tag(formula: str) -> str:
    """Markdown 수식을 export용 HWP 친화 `<math>` 태그로 감싼다."""
    normalized_formula = normalize_hwp_equation_script(str(formula or "").strip())
    return f"<math>{normalized_formula}</math>" if normalized_formula else ""


def _replace_display_markdown_math(match: re.Match[str]) -> str:
    """display Markdown 수식을 HWP legacy markup으로 변환한다."""
    return _wrap_hwp_math_tag(match.group(1))


def _replace_inline_markdown_math(match: re.Match[str]) -> str:
    """inline Markdown 수식을 HWP legacy markup으로 변환한다."""
    return _wrap_hwp_math_tag(match.group(1))


def markdown_to_hwp_legacy_markup(value: str | None) -> str | None:
    """Markdown+LaTeX 본문을 export 전용 `<math>` 기반 텍스트로 되돌린다."""
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    restored = DISPLAY_MATH_PATTERN.sub(_replace_display_markdown_math, raw_value)
    restored = INLINE_MATH_PATTERN.sub(_replace_inline_markdown_math, restored)
    return _normalize_markdown_lines(restored)


def has_markdown_output(problem_markdown: str | None, explanation_markdown: str | None) -> bool:
    """문제 또는 해설 Markdown 중 하나라도 있으면 출력 가능으로 본다."""
    return bool(str(problem_markdown or "").strip() or str(explanation_markdown or "").strip())
