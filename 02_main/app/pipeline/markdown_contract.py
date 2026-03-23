from __future__ import annotations

import re

MARKDOWN_VERSION = "mathocr_markdown_bridge_v1"
MATH_TAG_PATTERN = re.compile(r"<math>(.*?)</math>", re.DOTALL)


def _replace_math_tag(match: re.Match[str]) -> str:
    """기존 `<math>` 수식 태그를 Markdown 인라인 수식으로 바꾼다."""
    formula = str(match.group(1) or "").strip()
    return f"${formula}$" if formula else ""


def _normalize_markdown_lines(value: str) -> str | None:
    """줄 끝 공백만 정리한 뒤 빈 문자열이면 None을 반환한다."""
    normalized = "\n".join(line.rstrip() for line in value.splitlines()).strip()
    return normalized or None


def bridge_legacy_markup_to_markdown(value: str | None) -> str | None:
    """기존 HWP 친화 텍스트를 제한 Markdown 브리지 형식으로 변환한다."""
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    return _normalize_markdown_lines(MATH_TAG_PATTERN.sub(_replace_math_tag, raw_value))


def has_markdown_output(problem_markdown: str | None, explanation_markdown: str | None) -> bool:
    """문제 또는 해설 Markdown 중 하나라도 있으면 출력 가능으로 본다."""
    return bool(str(problem_markdown or "").strip() or str(explanation_markdown or "").strip())
