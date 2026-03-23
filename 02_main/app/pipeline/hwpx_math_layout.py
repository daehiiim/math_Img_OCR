from __future__ import annotations

import re
from typing import Iterable

MATH_SEGMENT_PATTERN = re.compile(r"(<math>.*?</math>)", re.DOTALL)
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


def measure_equation_script(text: str) -> int:
    """공백을 제외한 수식 길이를 계산해 폭 추정 기준으로 사용한다."""
    compact = re.sub(r"\s+", "", normalize_hwp_equation_script(text))
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
