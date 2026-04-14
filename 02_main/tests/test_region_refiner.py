from io import BytesIO
from pathlib import Path
import sys

from PIL import Image, ImageDraw

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.region_detector import DetectedRegionCandidate
from app.pipeline.region_refiner import refine_detected_regions


def _encode_png(image: Image.Image) -> bytes:
    """Pillow 이미지를 PNG 바이트로 직렬화한다."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _draw_bar(draw: ImageDraw.ImageDraw, left: int, top: int, right: int, bottom: int) -> tuple[int, int, int, int]:
    """검은색 잉크 막대를 그리고 실제 경계를 반환한다."""
    draw.rectangle((left, top, right, bottom), fill="black")
    return left, top, right, bottom


def _draw_problem_block(
    draw: ImageDraw.ImageDraw,
    *,
    left: int,
    top: int,
    width: int,
    numbered: bool = False,
    paragraph_lines: int = 3,
    formula: bool = False,
    choices: bool = False,
    answer_blank: bool = False,
    figure: bool = False,
) -> tuple[int, int, int, int]:
    """문항 단위 synthetic 잉크 블록을 그리고 실제 bbox를 반환한다."""
    bounds: list[tuple[int, int, int, int]] = []
    current_top = top
    text_left = left
    line_left_offset = 0

    if numbered:
        bounds.append(_draw_bar(draw, left, current_top, left + 16, current_top + 18))
        text_left = left + 28
        line_left_offset = 6

    for index in range(paragraph_lines):
        line_top = current_top + index * 18
        line_right = left + width - (18 if index % 2 == 0 else 42)
        bounds.append(_draw_bar(draw, text_left + line_left_offset, line_top, line_right, line_top + 8))
    current_top += paragraph_lines * 18 + 8

    if formula:
        bounds.append(_draw_bar(draw, left + 36, current_top, left + width - 36, current_top + 24))
        current_top += 38

    if figure:
        bounds.append(_draw_bar(draw, left + width - 86, current_top - 6, left + width - 22, current_top + 42))
        current_top += 52

    if choices:
        for index in range(5):
            line_top = current_top + index * 16
            bounds.append(_draw_bar(draw, left + 18, line_top, left + width - 24, line_top + 7))
        current_top += 5 * 16 + 8

    if answer_blank:
        bounds.append(_draw_bar(draw, left + 24, current_top, left + width - 54, current_top + 3))
        current_top += 18

    actual_left = min(bound[0] for bound in bounds)
    actual_top = min(bound[1] for bound in bounds)
    actual_right = max(bound[2] for bound in bounds)
    actual_bottom = max(bound[3] for bound in bounds)
    return actual_left, actual_top, actual_right, actual_bottom


def _build_candidate(
    bbox: tuple[int, int, int, int],
    *,
    order: int,
    confidence: float = 0.9,
    detected_question_number: str | None = None,
    includes_choices: bool = False,
    includes_figure: bool = False,
    boundary_basis: tuple[str, ...] = (),
) -> DetectedRegionCandidate:
    """테스트용 coarse 후보를 만든다."""
    return DetectedRegionCandidate(
        bbox=bbox,
        order=order,
        confidence=confidence,
        detected_question_number=detected_question_number,
        includes_choices=includes_choices,
        includes_figure=includes_figure,
        boundary_basis=boundary_basis,
    )


def _contains_bbox(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    """최종 bbox가 실제 잉크 bbox를 완전히 포함하는지 검사한다."""
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _overlap_ratio(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    """두 bbox의 최소 면적 대비 겹침 비율을 계산한다."""
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return 0.0
    intersection = (right - left) * (bottom - top)
    first_area = max(1, (first[2] - first[0]) * (first[3] - first[1]))
    second_area = max(1, (second[2] - second[0]) * (second[3] - second[1]))
    return intersection / min(first_area, second_area)


def test_refine_detected_regions_splits_numbered_two_column_page_without_overlap():
    """번호형 2열 페이지는 같은 열 문항끼리 겹침 없이 보정해야 한다."""
    image = Image.new("RGB", (560, 760), "white")
    draw = ImageDraw.Draw(image)
    left_top = _draw_problem_block(draw, left=34, top=52, width=210, numbered=True, paragraph_lines=3, choices=True)
    left_bottom = _draw_problem_block(draw, left=34, top=312, width=210, numbered=True, paragraph_lines=3, choices=True)
    right_top = _draw_problem_block(draw, left=304, top=58, width=210, numbered=True, paragraph_lines=2, formula=True, choices=True)
    right_bottom = _draw_problem_block(draw, left=304, top=332, width=210, numbered=True, paragraph_lines=2, figure=True, choices=True)
    page_bytes = _encode_png(image)

    result = refine_detected_regions(
        page_bytes,
        image_width=560,
        image_height=760,
        candidates=[
            _build_candidate((12, 36, 266, 346), order=1, detected_question_number="1", includes_choices=True, boundary_basis=("number_anchor", "choices")),
            _build_candidate((10, 274, 270, 580), order=2, detected_question_number="2", includes_choices=True, boundary_basis=("number_anchor", "choices")),
            _build_candidate((282, 30, 542, 328), order=3, detected_question_number="3", includes_choices=True, boundary_basis=("number_anchor", "formula_block", "choices")),
            _build_candidate((282, 296, 546, 636), order=4, detected_question_number="4", includes_choices=True, includes_figure=True, boundary_basis=("number_anchor", "figure", "choices")),
        ],
        detector_review_required=False,
    )

    assert len(result.regions) == 4
    assert _contains_bbox(result.regions[0].bbox, left_top)
    assert _contains_bbox(result.regions[1].bbox, left_bottom)
    assert _contains_bbox(result.regions[2].bbox, right_top)
    assert _contains_bbox(result.regions[3].bbox, right_bottom)
    assert _overlap_ratio(result.regions[0].bbox, result.regions[1].bbox) <= 0.05
    assert _overlap_ratio(result.regions[2].bbox, result.regions[3].bbox) <= 0.05
    assert all(region.warning_level == "normal" for region in result.regions)


def test_refine_detected_regions_expands_numberless_descriptive_problem():
    """번호 없는 서술형 문제도 지문과 수식 블록을 하나의 읽기 단위로 감싸야 한다."""
    image = Image.new("RGB", (420, 520), "white")
    draw = ImageDraw.Draw(image)
    actual_bbox = _draw_problem_block(draw, left=42, top=84, width=300, paragraph_lines=4, formula=True)
    page_bytes = _encode_png(image)

    result = refine_detected_regions(
        page_bytes,
        image_width=420,
        image_height=520,
        candidates=[
            _build_candidate((64, 92, 312, 162), order=1, confidence=0.87, boundary_basis=("paragraph_block", "formula_block")),
        ],
        detector_review_required=False,
    )

    assert len(result.regions) == 1
    assert _contains_bbox(result.regions[0].bbox, actual_bbox)
    assert result.regions[0].warning_level == "normal"
    assert result.regions[0].confidence >= 0.62


def test_refine_detected_regions_keeps_formula_only_problem():
    """수식만 있는 문제는 번호와 이미지가 없어도 별도 문항으로 남겨야 한다."""
    image = Image.new("RGB", (360, 420), "white")
    draw = ImageDraw.Draw(image)
    actual_bbox = _draw_problem_block(draw, left=78, top=118, width=200, paragraph_lines=0, formula=True)
    page_bytes = _encode_png(image)

    result = refine_detected_regions(
        page_bytes,
        image_width=360,
        image_height=420,
        candidates=[
            _build_candidate((112, 126, 250, 154), order=1, confidence=0.82, boundary_basis=("formula_block",)),
        ],
        detector_review_required=False,
    )

    assert len(result.regions) == 1
    assert _contains_bbox(result.regions[0].bbox, actual_bbox)
    assert "content_missing" not in result.regions[0].risk_flags
    assert result.regions[0].warning_level == "normal"


def test_refine_detected_regions_includes_choice_tail_without_figure():
    """도형 없는 객관식도 보기 끝까지 하단 경계를 확장해야 한다."""
    image = Image.new("RGB", (420, 560), "white")
    draw = ImageDraw.Draw(image)
    actual_bbox = _draw_problem_block(draw, left=36, top=72, width=310, paragraph_lines=2, choices=True)
    page_bytes = _encode_png(image)

    result = refine_detected_regions(
        page_bytes,
        image_width=420,
        image_height=560,
        candidates=[
            _build_candidate((30, 60, 344, 154), order=1, confidence=0.86, includes_choices=True, boundary_basis=("paragraph_block", "choices")),
        ],
        detector_review_required=False,
    )

    assert len(result.regions) == 1
    assert _contains_bbox(result.regions[0].bbox, actual_bbox)
    assert result.regions[0].bbox[3] >= actual_bbox[3]


def test_refine_detected_regions_includes_answer_blank_area():
    """답안칸이나 밑줄은 텍스트 아래쪽 경계에 포함되어야 한다."""
    image = Image.new("RGB", (420, 500), "white")
    draw = ImageDraw.Draw(image)
    actual_bbox = _draw_problem_block(draw, left=40, top=94, width=290, paragraph_lines=3, answer_blank=True)
    page_bytes = _encode_png(image)

    result = refine_detected_regions(
        page_bytes,
        image_width=420,
        image_height=500,
        candidates=[
            _build_candidate((44, 90, 316, 152), order=1, confidence=0.88, boundary_basis=("paragraph_block", "answer_blank")),
        ],
        detector_review_required=False,
    )

    assert len(result.regions) == 1
    assert _contains_bbox(result.regions[0].bbox, actual_bbox)
    assert result.regions[0].warning_level == "normal"


def test_refine_detected_regions_marks_high_risk_when_spacing_is_too_narrow():
    """문항 간 간격이 거의 없으면 분리하되 high_risk로 표시해야 한다."""
    image = Image.new("RGB", (420, 520), "white")
    draw = ImageDraw.Draw(image)
    upper_bbox = _draw_problem_block(draw, left=42, top=74, width=300, paragraph_lines=3, choices=True)
    lower_bbox = _draw_problem_block(draw, left=42, top=236, width=300, paragraph_lines=3, choices=True)
    _draw_bar(draw, 42, upper_bbox[3] + 2, 340, lower_bbox[1] - 2)
    page_bytes = _encode_png(image)

    result = refine_detected_regions(
        page_bytes,
        image_width=420,
        image_height=520,
        candidates=[
            _build_candidate((34, 60, 352, 286), order=1, confidence=0.79, includes_choices=True, boundary_basis=("paragraph_block", "choices")),
            _build_candidate((34, 210, 352, 444), order=2, confidence=0.78, includes_choices=True, boundary_basis=("paragraph_block", "choices")),
        ],
        detector_review_required=False,
    )

    assert len(result.regions) == 2
    assert _contains_bbox(result.regions[0].bbox, upper_bbox)
    assert _contains_bbox(result.regions[1].bbox, lower_bbox)
    assert _overlap_ratio(result.regions[0].bbox, result.regions[1].bbox) <= 0.05
    assert result.review_required is True
    assert any(region.warning_level == "high_risk" for region in result.regions)
