from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO

from PIL import Image, ImageOps

from app.pipeline.region_detector import DetectedRegionCandidate
from app.pipeline.schema import WarningLevel

LOW_CONFIDENCE_THRESHOLD = 0.62
OVERLAP_RATIO_THRESHOLD = 0.05


@dataclass(frozen=True)
class RefinedRegionCandidate:
    """보정 완료된 최종 문항 후보를 표현한다."""

    bbox: tuple[int, int, int, int]
    order: int
    confidence: float
    detected_question_number: str | None
    includes_choices: bool
    includes_figure: bool
    warning_level: WarningLevel
    risk_flags: tuple[str, ...] = ()
    boundary_basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class RefinedAutoDetectResult:
    """보정된 문항 후보와 전체 검토 필요 여부를 반환한다."""

    regions: list[RefinedRegionCandidate]
    review_required: bool


@dataclass
class _WorkingCandidate:
    """보정 중간 상태를 추적하는 내부 후보다."""

    source: DetectedRegionCandidate
    search_bbox: tuple[int, int, int, int]
    snapped_bbox: tuple[int, int, int, int]
    content_bbox: tuple[int, int, int, int]
    content_found: bool
    boundary_basis: tuple[str, ...]
    anchor_top: int
    valley_scores: list[float] = field(default_factory=list)
    final_bbox: tuple[int, int, int, int] | None = None
    overlap_penalty: float = 0.0
    forced_overlap_resolution: bool = False
    confidence: float = 0.0
    warning_level: WarningLevel = "normal"
    risk_flags: tuple[str, ...] = ()


def _clamp(value: int, minimum: int, maximum: int) -> int:
    """정수 좌표를 안전한 범위로 제한한다."""
    return max(minimum, min(value, maximum))


def _normalize_image(image_bytes: bytes) -> Image.Image:
    """입력 이미지를 EXIF 기준으로 정규화한 grayscale 이미지로 연다."""
    with Image.open(BytesIO(image_bytes)) as image:
        normalized = ImageOps.exif_transpose(image).convert("L")
    return normalized


def _build_ink_mask(image: Image.Image) -> Image.Image:
    """문항 경계 추적에 쓸 흑백 잉크 마스크를 만든다."""
    inverted = ImageOps.invert(image)
    return inverted.point(lambda value: 255 if value > 14 else 0)


def _basis_bonus(boundary_basis: tuple[str, ...], source: DetectedRegionCandidate) -> tuple[int, int]:
    """보기·수식·답안칸이 있는 후보는 탐색 범위를 더 넉넉히 잡는다."""
    bottom_bonus = 0
    top_bonus = 0
    if "number_anchor" in boundary_basis or source.detected_question_number:
        top_bonus += 10
    if source.includes_choices or "choices" in boundary_basis:
        bottom_bonus += 24
    if "answer_blank" in boundary_basis:
        bottom_bonus += 24
    if "formula_block" in boundary_basis:
        bottom_bonus += 18
    if source.includes_figure or "figure" in boundary_basis or "table" in boundary_basis:
        bottom_bonus += 20
    return top_bonus, bottom_bonus


def _expand_search_bbox(
    bbox: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
    boundary_basis: tuple[str, ...],
    source: DetectedRegionCandidate,
) -> tuple[int, int, int, int]:
    """후보 주변 탐색 범위를 계획된 규칙대로 넉넉하게 확장한다."""
    left, top, right, bottom = bbox
    width = max(1, right - left)
    height = max(1, bottom - top)
    pad_x = max(16, int(round(width * 0.06)))
    pad_y = max(16, int(round(height * 0.06)))
    top_bonus, bottom_bonus = _basis_bonus(boundary_basis, source)
    return (
        _clamp(left - pad_x, 0, image_width - 1),
        _clamp(top - pad_y - top_bonus, 0, image_height - 1),
        _clamp(right + pad_x, 1, image_width),
        _clamp(bottom + pad_y + bottom_bonus, 1, image_height),
    )


def _translate_local_bbox(
    search_bbox: tuple[int, int, int, int],
    local_bbox: tuple[int, int, int, int] | None,
) -> tuple[int, int, int, int] | None:
    """crop 기준 bbox를 페이지 절대 좌표 bbox로 변환한다."""
    if local_bbox is None:
        return None
    left, top, right, bottom = search_bbox
    return left + local_bbox[0], top + local_bbox[1], left + local_bbox[2], top + local_bbox[3]


def _snap_to_ink(mask: Image.Image, search_bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    """탐색 범위 안에서 실제 잉크가 있는 최소 bbox를 찾는다."""
    local_bbox = mask.crop(search_bbox).getbbox()
    return _translate_local_bbox(search_bbox, local_bbox)


def _build_working_candidate(
    mask: Image.Image,
    candidate: DetectedRegionCandidate,
    image_width: int,
    image_height: int,
) -> _WorkingCandidate:
    """coarse 후보를 잉크 스냅 가능한 내부 후보로 변환한다."""
    search_bbox = _expand_search_bbox(
        candidate.bbox,
        image_width,
        image_height,
        candidate.boundary_basis,
        candidate,
    )
    snapped_content = _snap_to_ink(mask, search_bbox)
    content_bbox = snapped_content or candidate.bbox
    content_found = snapped_content is not None
    return _WorkingCandidate(
        source=candidate,
        search_bbox=search_bbox,
        snapped_bbox=content_bbox,
        content_bbox=content_bbox,
        content_found=content_found,
        boundary_basis=candidate.boundary_basis,
        anchor_top=_find_anchor_top(mask, search_bbox, candidate.bbox),
    )


def _bbox_width(bbox: tuple[int, int, int, int]) -> int:
    """bbox 가로 길이를 계산한다."""
    return max(1, bbox[2] - bbox[0])


def _bbox_height(bbox: tuple[int, int, int, int]) -> int:
    """bbox 세로 길이를 계산한다."""
    return max(1, bbox[3] - bbox[1])


def _horizontal_overlap(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    """두 bbox의 가로 겹침 비율을 계산한다."""
    intersection = max(0, min(first[2], second[2]) - max(first[0], second[0]))
    return intersection / min(_bbox_width(first), _bbox_width(second))


def _column_matches(span: tuple[int, int], candidate_bbox: tuple[int, int, int, int]) -> bool:
    """후보가 기존 열 범위와 같은 열인지 판정한다."""
    candidate_span = (candidate_bbox[0], candidate_bbox[2])
    overlap = max(0, min(span[1], candidate_span[1]) - max(span[0], candidate_span[0]))
    if overlap / min(max(1, span[1] - span[0]), _bbox_width(candidate_bbox)) >= 0.25:
        return True
    span_center = (span[0] + span[1]) / 2
    candidate_center = (candidate_bbox[0] + candidate_bbox[2]) / 2
    return abs(span_center - candidate_center) <= max(48, _bbox_width(candidate_bbox) * 0.6)


def _group_candidates_by_column(candidates: list[_WorkingCandidate]) -> list[list[_WorkingCandidate]]:
    """가로 위치를 기준으로 후보를 열 단위로 묶는다."""
    columns: list[dict[str, object]] = []
    for candidate in sorted(candidates, key=lambda item: (item.snapped_bbox[0], item.snapped_bbox[1])):
        matched_column = next((column for column in columns if _column_matches(column["span"], candidate.snapped_bbox)), None)
        if matched_column is None:
            columns.append({"span": (candidate.snapped_bbox[0], candidate.snapped_bbox[2]), "items": [candidate]})
            continue
        current_span = matched_column["span"]
        matched_column["span"] = (
            min(current_span[0], candidate.snapped_bbox[0]),
            max(current_span[1], candidate.snapped_bbox[2]),
        )
        matched_column["items"].append(candidate)
    return [sorted(column["items"], key=lambda item: item.snapped_bbox[1]) for column in columns]


def _row_ink_counts(mask: Image.Image, left: int, right: int, top: int, bottom: int) -> list[int]:
    """특정 세로 구간의 행별 잉크량을 계산한다."""
    crop = mask.crop((left, top, right, bottom))
    pixels = crop.load()
    counts: list[int] = []
    for y in range(crop.height):
        row_total = 0
        for x in range(crop.width):
            if pixels[x, y]:
                row_total += 1
        counts.append(row_total)
    return counts


def _find_anchor_top(
    mask: Image.Image,
    search_bbox: tuple[int, int, int, int],
    source_bbox: tuple[int, int, int, int],
) -> int:
    """coarse 상단 부근에서 첫 번째 의미 있는 잉크 줄을 찾는다."""
    band_height = max(32, _bbox_height(source_bbox) // 2)
    top = max(search_bbox[1], source_bbox[1])
    bottom = min(search_bbox[3], source_bbox[1] + band_height)
    counts = _row_ink_counts(mask, search_bbox[0], search_bbox[2], top, bottom)
    threshold = max(6, int(_bbox_width(search_bbox) * 0.02))
    for index, count in enumerate(counts):
        if count >= threshold:
            return top + index
    return source_bbox[1]


def _boundary_search_range(upper: _WorkingCandidate, lower: _WorkingCandidate) -> tuple[int, int]:
    """coarse bbox 기준으로 valley 탐색 y 범위를 좁힌다."""
    upper_source = upper.source.bbox
    lower_source = lower.source.bbox
    upper_band = max(20, _bbox_height(upper_source) // 5)
    lower_band = max(20, _bbox_height(lower_source) // 5)
    start = max(upper_source[1] + 1, upper_source[3] - upper_band)
    end = min(lower_source[3] - 1, lower_source[1] + lower_band)
    if end <= start:
        midpoint = (upper_source[3] + lower_source[1]) // 2
        return midpoint, midpoint + 1
    return start, end


def _pick_boundary(mask: Image.Image, upper: _WorkingCandidate, lower: _WorkingCandidate) -> tuple[int, float]:
    """두 후보 사이의 whitespace valley와 경계 명확도를 찾는다."""
    left = min(upper.search_bbox[0], lower.search_bbox[0])
    right = max(upper.search_bbox[2], lower.search_bbox[2])
    start, end = _boundary_search_range(upper, lower)
    counts = _row_ink_counts(mask, left, right, start, end)
    if not counts:
        return max(upper.snapped_bbox[1] + 1, min((upper.snapped_bbox[3] + lower.snapped_bbox[1]) // 2, lower.snapped_bbox[3] - 1)), 0.0
    valley_value = min(counts)
    valley_index = counts.index(valley_value)
    average = sum(counts) / max(1, len(counts))
    clarity = max(0.0, min(1.0, 1.0 - (valley_value / max(average, 1.0))))
    return start + valley_index, clarity


def _apply_column_boundaries(mask: Image.Image, columns: list[list[_WorkingCandidate]]) -> None:
    """같은 열 인접 후보끼리 valley 기준 상하 경계를 조정한다."""
    for column in columns:
        for index in range(len(column) - 1):
            upper = column[index]
            lower = column[index + 1]
            boundary, clarity = _pick_boundary(mask, upper, lower)
            upper_left, upper_top, upper_right, upper_bottom = upper.snapped_bbox
            lower_left, lower_top, lower_right, lower_bottom = lower.snapped_bbox
            safe_boundary = min(boundary, lower.anchor_top - 1)
            upper.snapped_bbox = (upper_left, upper_top, upper_right, max(upper_top + 1, min(upper_bottom, safe_boundary)))
            lowered_top = lower_top if clarity < 0.18 else min(lower.anchor_top, min(lower_bottom - 1, max(lower_top, safe_boundary + 1)))
            lower.snapped_bbox = (lower_left, lowered_top, lower_right, lower_bottom)
            upper.valley_scores.append(clarity)
            lower.valley_scores.append(clarity)


def _content_density(mask: Image.Image, bbox: tuple[int, int, int, int]) -> float:
    """최종 bbox 내부 실제 잉크 밀도를 계산한다."""
    crop = mask.crop(bbox)
    ink_bbox = crop.getbbox()
    if ink_bbox is None:
        return 0.0
    ink_area = max(1, (ink_bbox[2] - ink_bbox[0]) * (ink_bbox[3] - ink_bbox[1]))
    total_area = max(1, crop.width * crop.height)
    return min(1.0, (ink_area / total_area) * 4.0)


def _final_padding(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
    """최종 저장 직전 약간 넉넉한 패딩 값을 계산한다."""
    pad_x = min(24, max(8, int(round(_bbox_width(bbox) * 0.02))))
    pad_y = min(24, max(8, int(round(_bbox_height(bbox) * 0.02))))
    return pad_x, pad_y


def _apply_final_padding(
    bbox: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    """최종 bbox에 안전 패딩을 더하고 페이지 범위로 clamp 한다."""
    pad_x, pad_y = _final_padding(bbox)
    return (
        _clamp(bbox[0] - pad_x, 0, image_width - 1),
        _clamp(bbox[1] - pad_y, 0, image_height - 1),
        _clamp(bbox[2] + pad_x, 1, image_width),
        _clamp(bbox[3] + pad_y, 1, image_height),
    )


def _finalize_bbox(mask: Image.Image, candidate: _WorkingCandidate, image_width: int, image_height: int) -> tuple[int, int, int, int]:
    """경계 조정 후 다시 잉크 스냅을 수행하고 최종 패딩을 적용한다."""
    snap_box = (
        _clamp(candidate.search_bbox[0], 0, image_width - 1),
        _clamp(candidate.snapped_bbox[1], 0, image_height - 1),
        _clamp(candidate.search_bbox[2], 1, image_width),
        _clamp(candidate.snapped_bbox[3], 1, image_height),
    )
    ink_bbox = _snap_to_ink(mask, snap_box) or candidate.snapped_bbox
    return _apply_final_padding(ink_bbox, image_width, image_height)


def _resolve_final_overlaps(columns: list[list[_WorkingCandidate]]) -> None:
    """최종 패딩 이후 남은 같은 열 겹침을 저장 직전에 줄인다."""
    for column in columns:
        for index in range(len(column) - 1):
            upper = column[index]
            lower = column[index + 1]
            if upper.final_bbox is None or lower.final_bbox is None:
                continue
            if upper.final_bbox[3] < lower.final_bbox[1]:
                continue
            upper.valley_scores.append(0.0)
            lower.valley_scores.append(0.0)
            upper.forced_overlap_resolution = True
            lower.forced_overlap_resolution = True
            boundary = (upper.final_bbox[3] + lower.final_bbox[1]) // 2
            upper.final_bbox = (
                upper.final_bbox[0],
                upper.final_bbox[1],
                upper.final_bbox[2],
                max(upper.final_bbox[1] + 1, boundary),
            )
            lower.final_bbox = (
                lower.final_bbox[0],
                min(lower.anchor_top, max(lower.final_bbox[1], boundary + 1)),
                lower.final_bbox[2],
                lower.final_bbox[3],
            )


def _shift_ratio(source_bbox: tuple[int, int, int, int], final_bbox: tuple[int, int, int, int]) -> float:
    """coarse bbox 대비 이동량 비율을 계산한다."""
    width = _bbox_width(source_bbox)
    height = _bbox_height(source_bbox)
    horizontal = (abs(source_bbox[0] - final_bbox[0]) + abs(source_bbox[2] - final_bbox[2])) / (2 * width)
    vertical = (abs(source_bbox[1] - final_bbox[1]) + abs(source_bbox[3] - final_bbox[3])) / (2 * height)
    return max(0.0, min(1.0, (horizontal + vertical) / 2))


def _bbox_overlap_ratio(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    """최소 면적 대비 bbox 겹침 비율을 계산한다."""
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return 0.0
    intersection = (right - left) * (bottom - top)
    first_area = max(1, _bbox_width(first) * _bbox_height(first))
    second_area = max(1, _bbox_width(second) * _bbox_height(second))
    return intersection / min(first_area, second_area)


def _apply_overlap_penalty(candidates: list[_WorkingCandidate]) -> None:
    """최종 bbox끼리 겹치는 경우 penalty를 기록한다."""
    for candidate in candidates:
        candidate.overlap_penalty = 0.0
    for index, candidate in enumerate(candidates):
        for other in candidates[index + 1 :]:
            overlap = _bbox_overlap_ratio(candidate.final_bbox or candidate.snapped_bbox, other.final_bbox or other.snapped_bbox)
            if overlap <= 0:
                continue
            candidate.overlap_penalty = max(candidate.overlap_penalty, overlap)
            other.overlap_penalty = max(other.overlap_penalty, overlap)


def _mean_valley_score(candidate: _WorkingCandidate) -> float:
    """후보가 가진 valley 명확도 평균을 계산한다."""
    if not candidate.valley_scores:
        return 1.0
    return sum(candidate.valley_scores) / len(candidate.valley_scores)


def _build_risk_flags(candidate: _WorkingCandidate, detector_review_required: bool) -> tuple[str, ...]:
    """구조 이상 징후를 사용자 검토용 risk flag로 정리한다."""
    flags: list[str] = []
    final_bbox = candidate.final_bbox or candidate.snapped_bbox
    shift_ratio = _shift_ratio(candidate.source.bbox, final_bbox)
    valley_score = _mean_valley_score(candidate)
    if not candidate.content_found:
        flags.append("content_missing")
    if shift_ratio > 0.38:
        flags.append("large_refine_shift")
    if valley_score < 0.18:
        flags.append("weak_boundary")
    if candidate.forced_overlap_resolution:
        flags.append("resolved_overlap")
    if candidate.overlap_penalty > OVERLAP_RATIO_THRESHOLD:
        flags.append("overlap")
    if detector_review_required and not flags:
        flags.append("detector_review")
    return tuple(flags)


def _score_candidate(mask: Image.Image, candidate: _WorkingCandidate) -> float:
    """coarse confidence와 보정 신호를 합친 최종 confidence를 계산한다."""
    final_bbox = candidate.final_bbox or candidate.snapped_bbox
    stability = 1.0 - _shift_ratio(candidate.source.bbox, final_bbox)
    valley_score = _mean_valley_score(candidate)
    snap_score = 1.0 if candidate.content_found else 0.25
    density_score = _content_density(mask, final_bbox)
    raw_score = (
        candidate.source.confidence * 0.42
        + stability * 0.2
        + valley_score * 0.16
        + snap_score * 0.12
        + density_score * 0.1
        - candidate.overlap_penalty * 0.24
    )
    return max(0.0, min(raw_score, 1.0))


def _finalize_candidate(mask: Image.Image, candidate: _WorkingCandidate, detector_review_required: bool) -> RefinedRegionCandidate:
    """최종 bbox, confidence, risk flag를 확정한다."""
    candidate.risk_flags = _build_risk_flags(candidate, detector_review_required)
    candidate.confidence = _score_candidate(mask, candidate)
    candidate.warning_level = "high_risk" if candidate.risk_flags or candidate.confidence < LOW_CONFIDENCE_THRESHOLD else "normal"
    return RefinedRegionCandidate(
        bbox=candidate.final_bbox or candidate.snapped_bbox,
        order=candidate.source.order,
        confidence=candidate.confidence,
        detected_question_number=candidate.source.detected_question_number,
        includes_choices=candidate.source.includes_choices,
        includes_figure=candidate.source.includes_figure,
        warning_level=candidate.warning_level,
        risk_flags=candidate.risk_flags,
        boundary_basis=candidate.boundary_basis,
    )


def refine_detected_regions(
    image_bytes: bytes,
    *,
    image_width: int,
    image_height: int,
    candidates: list[DetectedRegionCandidate],
    detector_review_required: bool,
) -> RefinedAutoDetectResult:
    """coarse 문항 후보를 reading-unit 기준 최종 bbox로 보정한다."""
    if not candidates:
        return RefinedAutoDetectResult(regions=[], review_required=True)

    mask = _build_ink_mask(_normalize_image(image_bytes))
    working = [_build_working_candidate(mask, candidate, image_width, image_height) for candidate in candidates]
    columns = _group_candidates_by_column(working)
    _apply_column_boundaries(mask, columns)
    for candidate in working:
        candidate.final_bbox = _finalize_bbox(mask, candidate, image_width, image_height)
    _resolve_final_overlaps(columns)
    _apply_overlap_penalty(working)
    refined = [_finalize_candidate(mask, candidate, detector_review_required) for candidate in working]
    review_required = detector_review_required or any(region.warning_level == "high_risk" for region in refined)
    return RefinedAutoDetectResult(regions=sorted(refined, key=lambda item: (item.order, item.bbox[1], item.bbox[0])), review_required=review_required)
