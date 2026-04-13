from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import requests

from app.pipeline.extractor import (
    _extract_json_object,
    _get_openai_api_key,
    _get_openai_base_url,
    _read_chat_content,
)

DETECTOR_MODEL = "gpt-5.2"
DETECTION_VERSION = "openai_five_choice_v1"
MIN_REGION_AREA_RATIO = 0.01
LOW_CONFIDENCE_THRESHOLD = 0.62
GIANT_REGION_AREA_RATIO = 0.82
OVERLAP_IOU_THRESHOLD = 0.6


@dataclass(frozen=True)
class DetectedRegionCandidate:
    """자동 분할이 반환한 후보 영역 한 개를 표현한다."""

    bbox: tuple[int, int, int, int]
    order: int
    confidence: float
    detected_question_number: str | None
    includes_choices: bool
    includes_figure: bool


@dataclass(frozen=True)
class AutoDetectRegionsResult:
    """자동 분할 결과와 검토 필요 여부를 함께 반환한다."""

    regions: list[DetectedRegionCandidate]
    review_required: bool
    detector_model: str
    detection_version: str
    openai_request_id: str | None


def _build_image_url(image_bytes: bytes) -> str:
    """원본 이미지 바이트를 data URL 문자열로 만든다."""
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{image_b64}"


def _build_detector_prompt() -> str:
    """5지선다 기출문제 전용 자동 분할 프롬프트를 반환한다."""
    return (
        "고등/중등 수학 기출문제 페이지에서 문항 단위를 찾으세요. "
        "각 영역은 문제 번호, 문제 본문, 5지선다 보기, 해당 문항에 귀속된 그림을 모두 포함해야 합니다. "
        "제목, 학교명, 페이지 번호, 정답표, 해설, 여백, 장식 요소는 제외하세요. "
        "반드시 JSON object만 반환하세요. 형식은 "
        '{"regions":[{"bbox":[0,0,100,100],"order":1,"confidence":0.91,'
        '"detected_question_number":"1","includes_choices":true,"includes_figure":false}],'
        '"review_required":false}. '
        "bbox는 [left, top, right, bottom] 순서의 정수입니다."
    )


def _request_detector(
    root_path,
    image_bytes: bytes,
    *,
    api_key: str | None,
) -> tuple[dict[str, Any], str | None]:
    """OpenAI 비전 모델에 자동 분할 요청을 보내고 JSON을 반환한다."""
    resolved_api_key = api_key or _get_openai_api_key(root_path)
    payload = {
        "model": DETECTOR_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Return strict JSON object only."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _build_detector_prompt()},
                    {"type": "image_url", "image_url": {"url": _build_image_url(image_bytes), "detail": "low"}},
                ],
            },
        ],
    }
    response = requests.post(
        f"{_get_openai_base_url(root_path).rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {resolved_api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        raise ValueError(f"OpenAI region detect API error {response.status_code}: {response.text[:400]}")
    request_id = response.headers.get("x-request-id") or response.headers.get("request-id")
    return _extract_json_object(_read_chat_content(response.json())), request_id


def _clamp(value: Any, minimum: int, maximum: int) -> int:
    """좌표 값을 정수 범위 안으로 보정한다."""
    try:
        normalized = int(round(float(value)))
    except (TypeError, ValueError):
        normalized = minimum
    return max(minimum, min(normalized, maximum))


def _normalize_bbox(raw_bbox: Any, image_width: int, image_height: int) -> tuple[int, int, int, int] | None:
    """모델 bbox를 이미지 범위 안의 유효한 정수 사각형으로 정리한다."""
    if not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
        return None
    left = _clamp(raw_bbox[0], 0, max(0, image_width - 1))
    top = _clamp(raw_bbox[1], 0, max(0, image_height - 1))
    right = _clamp(raw_bbox[2], 1, max(1, image_width))
    bottom = _clamp(raw_bbox[3], 1, max(1, image_height))
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _expand_bbox(bbox: tuple[int, int, int, int], image_width: int, image_height: int) -> tuple[int, int, int, int]:
    """문항 경계가 너무 빡빡하지 않도록 소폭 패딩을 더한다."""
    left, top, right, bottom = bbox
    pad_x = max(8, int((right - left) * 0.04))
    pad_y = max(8, int((bottom - top) * 0.04))
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(image_width, right + pad_x),
        min(image_height, bottom + pad_y),
    )


def _bbox_area(bbox: tuple[int, int, int, int]) -> int:
    """사각형 넓이를 계산한다."""
    return max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])


def _is_large_enough(bbox: tuple[int, int, int, int], image_width: int, image_height: int) -> bool:
    """너무 작은 후보 영역은 문항이 아닌 것으로 본다."""
    image_area = max(1, image_width * image_height)
    return _bbox_area(bbox) / image_area >= MIN_REGION_AREA_RATIO


def _compute_iou(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    """중복 후보 제거를 위해 IoU를 계산한다."""
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = _bbox_area((left, top, right, bottom))
    if intersection <= 0:
        return 0.0
    union = _bbox_area(first) + _bbox_area(second) - intersection
    return intersection / max(1, union)


def _parse_confidence(value: Any) -> float:
    """모델 confidence를 0~1 범위 실수로 정규화한다."""
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(normalized, 1.0))


def _build_candidate(raw_region: Any, image_width: int, image_height: int, fallback_order: int) -> DetectedRegionCandidate | None:
    """원시 JSON 후보를 검증 가능한 후보 객체로 변환한다."""
    if not isinstance(raw_region, dict):
        return None
    normalized_bbox = _normalize_bbox(raw_region.get("bbox"), image_width, image_height)
    if normalized_bbox is None:
        return None
    expanded_bbox = _expand_bbox(normalized_bbox, image_width, image_height)
    if not _is_large_enough(expanded_bbox, image_width, image_height):
        return None
    return DetectedRegionCandidate(
        bbox=expanded_bbox,
        order=max(1, int(raw_region.get("order") or fallback_order + 1)),
        confidence=_parse_confidence(raw_region.get("confidence")),
        detected_question_number=str(raw_region.get("detected_question_number") or "").strip() or None,
        includes_choices=bool(raw_region.get("includes_choices")),
        includes_figure=bool(raw_region.get("includes_figure")),
    )


def _dedupe_candidates(candidates: list[DetectedRegionCandidate]) -> list[DetectedRegionCandidate]:
    """겹침이 큰 후보는 confidence가 더 높은 쪽만 남긴다."""
    resolved: list[DetectedRegionCandidate] = []
    for candidate in sorted(candidates, key=lambda item: (-item.confidence, item.order)):
        if any(_compute_iou(candidate.bbox, existing.bbox) >= OVERLAP_IOU_THRESHOLD for existing in resolved):
            continue
        resolved.append(candidate)
    return sorted(resolved, key=lambda item: (item.order, item.bbox[1], item.bbox[0]))


def _has_giant_single_region(candidates: list[DetectedRegionCandidate], image_width: int, image_height: int) -> bool:
    """페이지 대부분을 덮는 거대 단일 박스인지 판별한다."""
    if len(candidates) != 1:
        return False
    image_area = max(1, image_width * image_height)
    return _bbox_area(candidates[0].bbox) / image_area >= GIANT_REGION_AREA_RATIO


def _needs_review(parsed: dict[str, Any], candidates: list[DetectedRegionCandidate], image_width: int, image_height: int) -> bool:
    """자동 분할 결과를 바로 실행해도 되는지 보수적으로 판단한다."""
    if bool(parsed.get("review_required")):
        return True
    if not candidates or _has_giant_single_region(candidates, image_width, image_height):
        return True
    return any(candidate.confidence < LOW_CONFIDENCE_THRESHOLD for candidate in candidates)


def detect_problem_regions_with_gpt(
    root_path,
    image_bytes: bytes,
    *,
    image_width: int,
    image_height: int,
    api_key: str | None = None,
) -> AutoDetectRegionsResult:
    """원본 페이지 이미지에서 문항 단위 후보 영역을 자동 분할한다."""
    parsed, request_id = _request_detector(root_path, image_bytes, api_key=api_key)
    raw_regions = parsed.get("regions") if isinstance(parsed.get("regions"), list) else []
    candidates = [
        candidate
        for index, raw_region in enumerate(raw_regions)
        if (candidate := _build_candidate(raw_region, image_width, image_height, index)) is not None
    ]
    resolved_candidates = _dedupe_candidates(candidates)
    return AutoDetectRegionsResult(
        regions=resolved_candidates,
        review_required=_needs_review(parsed, resolved_candidates, image_width, image_height),
        detector_model=DETECTOR_MODEL,
        detection_version=DETECTION_VERSION,
        openai_request_id=request_id,
    )
