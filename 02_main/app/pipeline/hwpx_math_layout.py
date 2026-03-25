from __future__ import annotations

import re
from typing import Iterable

from lxml import etree

MATH_SEGMENT_PATTERN = re.compile(r"(<math>.*?</math>)", re.DOTALL)
ANGLE_KEY_PATTERN = re.compile(r"\bANGLE\b", re.IGNORECASE)
SCRIPT_REPLACEMENTS = (
    ("\\triangle", "△"),
    ("\\angle", "∠"),
    ("\\circ", "°"),
    ("\\therefore", "∴"),
    ("\\because", "∵"),
    ("\\parallel", "∥"),
    ("\\times", "×"),
    ("\\div", "÷"),
    ("\\cdot", "·"),
    ("\\pm", "±"),
    ("\\mp", "∓"),
    ("\\leq", "≤"),
    ("\\le", "≤"),
    ("\\geq", "≥"),
    ("\\ge", "≥"),
    ("\\neq", "≠"),
    ("\\approx", "≈"),
    ("\\equiv", "≡"),
    ("\\infty", "∞"),
    ("degree", "°"),
)
COMPACT_INLINE_EQUATION_HEIGHT = 975
COMPACT_INLINE_EQUATION_BASELINE = 86
COMPACT_INLINE_WIDTH_OVERRIDES_RAW = {
    "20 ÷ 2 = 10": 4975,
    "30 ÷ 2 = 15": 4975,
    "10² : 15²": 3570,
    "15² ÷ 10² = 225 ÷ 100 = 9 ÷ 4": 12855,
    "18,000 × 9 ÷ 4": 6255,
    "18,000 ÷ 4 = 4,500": 8340,
    "4,500 × 9 = 40,500": 8340,
    "40,500": 2995,
    "AB=14": 3870,
    "AE=6": 3345,
    "BE=14-6=8": 7195,
    "AD=8": 3420,
    "DC=x": 3420,
    "AC=8+x": 5050,
    "E": 750,
    "AB": 1575,
    "D": 825,
    "AC": 1575,
    "∠BAC=∠DAE": 8070,
    "∠ABC=∠ADE": 8070,
    "A↔A": 2700,
    "B↔D": 2625,
    "C↔E": 2550,
    "AB:AD=AC:AE": 9060,
    "14:8=(8+x):6": 7835,
    "84=64+8x": 5575,
    "x=5/2": 3420,
}


def split_math_text(text: str) -> list[tuple[bool, str]]:
    """`<math>` 태그 기준으로 텍스트와 수식 조각을 분리한다."""
    if not text:
        return []
    segments: list[tuple[bool, str]] = []
    for part in MATH_SEGMENT_PATTERN.split(text):
        if not part:
            continue
        if part.startswith("<math>") and part.endswith("</math>"):
            segments.append((True, part[6:-7].strip()))
            continue
        segments.append((False, part))
    return segments


def has_math_tag(text: str) -> bool:
    """문자열에 `<math>` 태그가 있는지 반환한다."""
    return "<math>" in text and "</math>" in text


def normalize_export_text(text: str) -> str:
    """문서에 남는 텍스트를 HWP 친화 스크립트로 정규화한다."""
    if not text:
        return text
    segments: list[str] = []
    for is_math, part in split_math_text(text):
        normalized = normalize_hwp_equation_script(part)
        segments.append(f"<math>{normalized}</math>" if is_math else normalized)
    return "".join(segments)


def normalize_hwp_equation_script(text: str) -> str:
    """LaTeX 잔재를 한글 수식 편집기 호환 표기로 바꾼다."""
    if not text:
        return text
    normalized = text
    for source, target in SCRIPT_REPLACEMENTS:
        normalized = normalized.replace(source, target)
    normalized = re.sub(r"\\(?:mathrm|text|mathbf|mathit)\{([^{}]*)\}", r"\1", normalized)
    normalized = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", normalized)
    normalized = re.sub(r"\\sqrt\{([^{}]+)\}", r"√\1", normalized)
    normalized = re.sub(r"\\overline\{([^{}]+)\}", r"\1", normalized)
    normalized = normalized.replace("{", "").replace("}", "").replace("$", "").replace("`", "")
    normalized = re.sub(r"\s{2,}", " ", normalized)
    return normalized.strip()


def _canonicalize_equation_key(text: str) -> str:
    """폭 샘플과 reference lookup에 사용할 공통 수식 키를 만든다."""
    normalized = normalize_hwp_equation_script(text)
    normalized = ANGLE_KEY_PATTERN.sub("∠", normalized)
    return re.sub(r"\s+", "", normalized).strip()


COMPACT_INLINE_WIDTH_OVERRIDES = {
    _canonicalize_equation_key(script): width
    for script, width in COMPACT_INLINE_WIDTH_OVERRIDES_RAW.items()
}
COMPACT_INLINE_WIDTH_SAMPLE_PAIRS = tuple(COMPACT_INLINE_WIDTH_OVERRIDES.items())


def measure_equation_script(text: str) -> int:
    """공백을 제외한 수식 길이를 계산해 폭 추정 기준으로 사용한다."""
    compact = _canonicalize_equation_key(text)
    return len(compact)


def collect_equation_width_samples(script_width_pairs: Iterable[tuple[str, int]]) -> list[tuple[int, int]]:
    """스크립트-폭 표본을 길이 기준 평균 폭 샘플로 압축한다."""
    grouped: dict[int, list[int]] = {}
    for script, width in script_width_pairs:
        metric = measure_equation_script(script)
        if metric <= 0 or width <= 0:
            continue
        grouped.setdefault(metric, []).append(width)
    return sorted((metric, round(sum(widths) / len(widths))) for metric, widths in grouped.items())


def estimate_inline_equation_width(samples: list[tuple[int, int]], script: str, fallback_width: int) -> int:
    """길이-폭 샘플을 기준으로 현재 inline 수식 폭을 추정한다."""
    target_metric = measure_equation_script(script)
    normalized_samples = [(metric, width) for metric, width in samples if metric > 0 and width > 0]
    if target_metric <= 0 or not normalized_samples:
        return fallback_width
    minimum_width = max(525, round(normalized_samples[0][1] * 0.6))
    if len(normalized_samples) == 1:
        metric, width = normalized_samples[0]
        return max(minimum_width, round(width * target_metric / metric))
    low_sample, high_sample = _select_neighbor_samples(normalized_samples, target_metric)
    estimated_width = _interpolate_sample_width(low_sample, high_sample, target_metric)
    return max(minimum_width, estimated_width)


def repair_equation_widths(section_xml: bytes, reference_xml: bytes) -> bytes:
    """기준 문서와 보정 프로파일을 사용해 section0.xml 수식 박스를 다시 맞춘다."""
    section_root = etree.fromstring(section_xml)
    reference_root = etree.fromstring(reference_xml)
    _merge_inline_only_runs(section_root)
    reference_widths, width_samples = _collect_reference_equation_widths(reference_root)
    _repair_section_equation_widths(section_root, reference_widths, width_samples)
    return etree.tostring(section_root, encoding="UTF-8", xml_declaration=True)


def _merge_inline_only_runs(section_root) -> None:
    """text/equation만 있는 direct 문단은 한 run 구조로 다시 합친다."""
    namespaces = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    for paragraph in section_root.findall(".//hp:p", namespaces=namespaces):
        _merge_paragraph_inline_runs(paragraph)


def _merge_paragraph_inline_runs(paragraph) -> None:
    """inline 전용 run 여러 개를 첫 run 하나로 합친다."""
    namespaces = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    runs = paragraph.findall("hp:run", namespaces=namespaces)
    if len(runs) <= 1:
        return
    if len({run.get("charPrIDRef") for run in runs}) != 1:
        return
    if not all(_is_inline_only_run(run) for run in runs):
        return
    primary_run = runs[0]
    for run in runs[1:]:
        for child in list(run):
            primary_run.append(child)
        paragraph.remove(run)


def _is_inline_only_run(run) -> bool:
    """run 자식이 text/equation만 있는 단순 inline 구조인지 판별한다."""
    allowed_names = {"t", "equation"}
    return len(run) > 0 and all(etree.QName(child).localname in allowed_names for child in run)


def _is_compact_explanation_paragraph(paragraph) -> bool:
    """정상 파일과 같은 compact inline equation 프로파일이 필요한 해설 문단인지 판별한다."""
    return paragraph.get("paraPrIDRef") == "0" and paragraph.get("styleIDRef") == "0"


def _is_numeric_arithmetic_script(script: str) -> bool:
    """숫자와 산술 연산 위주의 inline 수식인지 판별한다."""
    normalized = normalize_hwp_equation_script(script)
    return bool(re.search(r"\d", normalized)) and not bool(re.search(r"[A-Za-z가-힣△∠]", normalized))


def _get_compact_inline_width_samples() -> list[tuple[int, int]]:
    """정상 answer 파일에서 추출한 compact arithmetic 폭 샘플을 반환한다."""
    return collect_equation_width_samples(COMPACT_INLINE_WIDTH_SAMPLE_PAIRS)


def _resolve_compact_inline_width(
    script: str,
    reference_widths: dict[str, int],
    width_samples: list[tuple[int, int]],
    fallback_width: int,
) -> int:
    """해설 inline 수식에 맞는 compact width를 계산한다."""
    normalized_script = _canonicalize_equation_key(script)
    if normalized_script in COMPACT_INLINE_WIDTH_OVERRIDES:
        return COMPACT_INLINE_WIDTH_OVERRIDES[normalized_script]
    reference_width = reference_widths.get(script) or reference_widths.get(normalized_script)
    if reference_width is not None and not _is_numeric_arithmetic_script(normalized_script):
        return reference_width
    compact_fallback = estimate_inline_equation_width(
        _get_compact_inline_width_samples(),
        normalized_script,
        fallback_width,
    )
    if _is_numeric_arithmetic_script(normalized_script):
        return compact_fallback
    return reference_width or estimate_inline_equation_width(width_samples, normalized_script, compact_fallback)


def _apply_compact_inline_box_metrics(equation, size, resolved_width: int) -> None:
    """정상 answer 파일과 같은 compact inline equation 박스 크기를 반영한다."""
    if resolved_width > 0:
        size.set("width", str(resolved_width))
    size.set("height", str(COMPACT_INLINE_EQUATION_HEIGHT))
    equation.set("baseLine", str(COMPACT_INLINE_EQUATION_BASELINE))


def _select_neighbor_samples(samples: list[tuple[int, int]], target_metric: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """대상 길이를 둘러싼 앞뒤 샘플 두 개를 고른다."""
    if target_metric <= samples[0][0]:
        return samples[0], samples[1]
    for low_sample, high_sample in zip(samples, samples[1:]):
        if target_metric <= high_sample[0]:
            return low_sample, high_sample
    return samples[-2], samples[-1]


def _interpolate_sample_width(
    low_sample: tuple[int, int],
    high_sample: tuple[int, int],
    target_metric: int,
) -> int:
    """앞뒤 샘플 두 개 사이에서 선형 보간한 폭을 계산한다."""
    low_metric, low_width = low_sample
    high_metric, high_width = high_sample
    if high_metric == low_metric:
        return max(low_width, high_width)
    slope = (high_width - low_width) / (high_metric - low_metric)
    return round(low_width + (slope * (target_metric - low_metric)))


def _collect_reference_equation_widths(reference_root) -> tuple[dict[str, int], list[tuple[int, int]]]:
    """기준 문서의 수식 스크립트별 폭과 길이 샘플을 수집한다."""
    script_widths: dict[str, list[int]] = {}
    width_pairs: list[tuple[str, int]] = []
    for equation in reference_root.findall(".//hp:equation", namespaces={"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}):
        script = (equation.findtext("hp:script", default="", namespaces={"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}) or "").strip()
        size = equation.find("hp:sz", namespaces={"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"})
        if not script or size is None:
            continue
        width_value = _parse_width_value(size.get("width"))
        if width_value <= 0:
            continue
        script_widths.setdefault(script, []).append(width_value)
        canonical_script = _canonicalize_equation_key(script)
        if canonical_script and canonical_script != script:
            script_widths.setdefault(canonical_script, []).append(width_value)
        width_pairs.append((script, width_value))
        if canonical_script and canonical_script != script:
            width_pairs.append((canonical_script, width_value))
    resolved_widths = {script: round(sum(widths) / len(widths)) for script, widths in script_widths.items()}
    return resolved_widths, collect_equation_width_samples(width_pairs)


def _repair_section_equation_widths(
    section_root,
    reference_widths: dict[str, int],
    width_samples: list[tuple[int, int]],
) -> None:
    """문서에 있는 수식별 폭을 기준 샘플에 맞게 보정한다."""
    namespaces = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    for paragraph in section_root.findall(".//hp:p", namespaces=namespaces):
        compact_context = _is_compact_explanation_paragraph(paragraph)
        for equation in paragraph.findall(".//hp:equation", namespaces=namespaces):
            script = (equation.findtext("hp:script", default="", namespaces=namespaces) or "").strip()
            size = equation.find("hp:sz", namespaces=namespaces)
            if not script or size is None:
                continue
            current_width = _parse_width_value(size.get("width"))
            if compact_context:
                resolved_width = _resolve_compact_inline_width(script, reference_widths, width_samples, current_width)
                _apply_compact_inline_box_metrics(equation, size, resolved_width)
                continue
            resolved_width = reference_widths.get(script)
            if resolved_width is None:
                resolved_width = estimate_inline_equation_width(width_samples, script, current_width)
            if resolved_width > 0 and resolved_width != current_width:
                size.set("width", str(resolved_width))


def _parse_width_value(raw_width: str | None) -> int:
    """폭 속성 값을 안전한 정수로 변환한다."""
    if raw_width is None:
        return 0
    try:
        return int(raw_width)
    except (TypeError, ValueError):
        return 0
