import importlib
import sys
from pathlib import Path

from lxml import etree

sys.path.append(str(Path(__file__).resolve().parents[1]))

NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}


def load_math_layout_module():
    """수식 레이아웃 모듈을 매 테스트마다 새로 import한다."""
    sys.modules.pop("app.pipeline.hwpx_math_layout", None)
    return importlib.import_module("app.pipeline.hwpx_math_layout")


def build_section_xml(paragraphs: str) -> bytes:
    """테스트용 section XML 바이트를 구성한다."""
    return (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<hs:sec xmlns:hs='http://www.hancom.co.kr/hwpml/2011/section' "
        "xmlns:hp='http://www.hancom.co.kr/hwpml/2011/paragraph'>"
        f"{paragraphs}"
        "</hs:sec>"
    ).encode("utf-8")


def build_equation(script: str, width: int, height: int = 1125, baseline: int = 85) -> str:
    """테스트용 inline equation XML 문자열을 만든다."""
    return (
        f"<hp:equation id='1' zOrder='0' numberingType='EQUATION' textWrap='TOP_AND_BOTTOM' "
        f"textFlow='BOTH_SIDES' lock='0' dropcapstyle='None' version='Equation Version 60' "
        f"baseLine='{baseline}' textColor='#000000' baseUnit='1000' lineMode='CHAR' font='HYhwpEQ'>"
        f"<hp:sz width='{width}' widthRelTo='ABSOLUTE' height='{height}' heightRelTo='ABSOLUTE' protect='0'/>"
        "<hp:pos treatAsChar='1' affectLSpacing='0' flowWithText='1' allowOverlap='0' holdAnchorAndSO='0' "
        "vertRelTo='PARA' horzRelTo='PARA' vertAlign='TOP' horzAlign='LEFT' vertOffset='0' horzOffset='0'/>"
        "<hp:outMargin left='56' right='56' top='0' bottom='0'/>"
        "<hp:shapeComment>수식입니다.</hp:shapeComment>"
        f"<hp:script>{script}</hp:script>"
        "</hp:equation>"
    )


def test_repair_equation_widths_matches_compact_angle_answer_width():
    """각도식은 style guide 길이 대신 한글 정상 저장본의 compact 폭을 따라야 한다."""
    module = load_math_layout_module()
    section_xml = build_section_xml(
        "<hp:p id='1' paraPrIDRef='0' styleIDRef='0'>"
        "<hp:run charPrIDRef='5'>"
        f"{build_equation('∠ABC=∠ADE', 4644)}"
        "</hp:run>"
        "</hp:p>"
    )
    reference_xml = build_section_xml(
        "<hp:p id='1' paraPrIDRef='0' styleIDRef='0'>"
        "<hp:run charPrIDRef='5'>"
        f"{build_equation('ANGLE  ABC`=` ANGLE  ADE', 8386)}"
        "</hp:run>"
        "</hp:p>"
    )

    repaired = module.repair_equation_widths(section_xml, reference_xml)
    equation = etree.fromstring(repaired).find(".//hp:equation", NS)
    size = equation.find("hp:sz", NS)

    assert size.get("width") == "8070"
    assert size.get("height") == "975"
    assert equation.get("baseLine") == "86"


def test_repair_equation_widths_uses_compact_reference_samples_for_short_algebra():
    """짧은 대수식도 한글 정상 저장본 기준 compact 폭으로 보정돼야 한다."""
    module = load_math_layout_module()
    section_xml = build_section_xml(
        "<hp:p id='1' paraPrIDRef='0' styleIDRef='0'>"
        "<hp:run charPrIDRef='5'>"
        f"{build_equation('AB=14', 2306)}"
        "</hp:run>"
        "</hp:p>"
    )
    reference_xml = build_section_xml(
        "<hp:p id='1' paraPrIDRef='0' styleIDRef='0'>"
        "<hp:run charPrIDRef='5'>"
        f"{build_equation('ANGLE  ABC`=` ANGLE  ADE', 8386)}"
        "</hp:run>"
        "</hp:p>"
    )

    repaired = module.repair_equation_widths(section_xml, reference_xml)
    equation = etree.fromstring(repaired).find(".//hp:equation", NS)
    size = equation.find("hp:sz", NS)

    assert size.get("width") == "3870"
    assert size.get("height") == "975"
    assert equation.get("baseLine") == "86"


def test_repair_equation_widths_merges_inline_only_runs_into_single_run():
    """direct writer가 쪼갠 inline run은 한 문단 한 run 구조로 다시 합쳐야 한다."""
    module = load_math_layout_module()
    section_xml = build_section_xml(
        "<hp:p id='1' paraPrIDRef='0' styleIDRef='0'>"
        "<hp:run charPrIDRef='5'><hp:t>점 E는 AB 위에 있고</hp:t></hp:run>"
        f"<hp:run charPrIDRef='5'>{build_equation('AB=14', 2306)}</hp:run>"
        "<hp:run charPrIDRef='5'><hp:t>,</hp:t></hp:run>"
        f"<hp:run charPrIDRef='5'>{build_equation('AE=6', 2306)}</hp:run>"
        "<hp:run charPrIDRef='5'><hp:t>이므로</hp:t></hp:run>"
        "</hp:p>"
    )
    reference_xml = build_section_xml(
        "<hp:p id='1' paraPrIDRef='0' styleIDRef='0'>"
        "<hp:run charPrIDRef='5'><hp:t>기준 문단</hp:t></hp:run>"
        "</hp:p>"
    )

    repaired = module.repair_equation_widths(section_xml, reference_xml)
    paragraph = etree.fromstring(repaired).find(".//hp:p", NS)
    runs = paragraph.findall("hp:run", NS)

    assert len(runs) == 1
    assert [child.tag.rsplit('}', 1)[-1] for child in runs[0]] == [
        "t",
        "equation",
        "t",
        "equation",
        "t",
    ]
