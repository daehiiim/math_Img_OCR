from __future__ import annotations

import re
import shutil
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree

HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"
NS = {"hp": HP_NS, "hc": HC_NS}
CHOICE_MARKERS = ("①", "②", "③", "④", "⑤")
TEMPLATE_ERROR_CODES = {
    "profile": "reference subtree 손상",
    "copy": "블록 복제 실패",
    "style": "style anchor mismatch",
}


@dataclass(frozen=True)
class ReferenceParagraphProfile:
    """레퍼런스 section0.xml에서 재사용할 문단 템플릿을 보관한다."""

    root: Any
    first_problem: Any
    title_paragraphs: tuple[Any, ...]
    problem_gap: Any
    image: Any
    choice: Any
    choice_gap: Any
    explanation_label: Any
    explanation_blank: Any
    explanation_body: Any
    repeated_problem: Any


@dataclass(frozen=True)
class ParsedProblemText:
    """OCR 본문을 문제 줄과 보기 줄로 분리한 결과를 보관한다."""

    stem: str
    choices: tuple[str, ...] | None


def render_section_from_reference(
    section_path: Path,
    root_path: Path,
    job: Any,
    bindata_dir: Path,
    runtime: Any,
    context: Any,
    warnings: Any,
) -> list[dict[str, str]]:
    """레퍼런스 section0.xml을 복제해 현재 job 본문으로 다시 렌더링한다."""
    profile = load_reference_profile(section_path)
    root = deepcopy(profile.root)
    _clear_root_paragraphs(root)
    idgen = runtime.IDGen()
    images_info: list[dict[str, str]] = []
    regions = collect_exportable_regions(job)
    if not regions:
        _append_header_only(root, profile, context.year)
        write_section_xml(section_path, root)
        return images_info

    append_first_region(root, profile, root_path, regions[0], 1, bindata_dir, runtime, idgen, context.year, warnings, images_info)
    for number, region in enumerate(regions[1:], start=2):
        append_repeated_region(root, profile, root_path, region, number, bindata_dir, runtime, idgen, warnings, images_info)
    write_section_xml(section_path, root)
    return images_info


def load_reference_profile(section_path: Path) -> ReferenceParagraphProfile:
    """레퍼런스 section0.xml에서 블록 복제에 필요한 문단들을 추출한다."""
    root = etree.parse(str(section_path)).getroot()
    paragraphs = root.findall("hp:p", NS)
    first_problem = require_paragraph(paragraphs, lambda node: node.find(".//hp:tbl", NS) is not None, "first_problem")
    title_paragraphs = tuple(paragraphs[1:5])
    problem_gap = require_paragraph(paragraphs, lambda node: node.get("paraPrIDRef") == "29" and node.find(".//hp:pic", NS) is None and "".join(node.xpath(".//hp:t/text()", namespaces=NS)).strip() == "", "problem_gap")
    image = require_paragraph(paragraphs, lambda node: node.find(".//hp:pic", NS) is not None, "image")
    choice = require_paragraph(paragraphs, lambda node: "①" in "".join(node.xpath(".//hp:t/text()", namespaces=NS)), "choice")
    choice_gap = next_sibling_paragraph(paragraphs, choice, "choice_gap")
    explanation_label = require_paragraph(paragraphs, lambda node: "[해설]" in "".join(node.xpath(".//hp:t/text()", namespaces=NS)), "explanation_label")
    explanation_blank = next_sibling_paragraph(paragraphs, explanation_label, "explanation_blank")
    explanation_body = require_paragraph(paragraphs, lambda node: node.get("paraPrIDRef") == "4" and node.get("styleIDRef") == "0" and bool(node.xpath(".//hp:t/text() | .//hp:equation/hp:script/text()", namespaces=NS)), "explanation_body")
    repeated_problem = build_repeated_problem_template(first_problem)
    return ReferenceParagraphProfile(root, first_problem, title_paragraphs, problem_gap, image, choice, choice_gap, explanation_label, explanation_blank, explanation_body, repeated_problem)


def collect_exportable_regions(job: Any) -> list[Any]:
    """본문 또는 해설이 있는 영역만 order 기준으로 정렬해 반환한다."""
    ordered_regions = sorted(job.regions, key=lambda region: region.context.order)
    return [
        region
        for region in ordered_regions
        if (region.extractor.ocr_text or "").strip() or (region.extractor.explanation or "").strip()
    ]


def append_first_region(
    root: Any,
    profile: ReferenceParagraphProfile,
    root_path: Path,
    region: Any,
    number: int,
    bindata_dir: Path,
    runtime: Any,
    idgen: Any,
    year: str,
    warnings: Any,
    images_info: list[dict[str, str]],
) -> None:
    """첫 문제 블록은 제목 scaffold를 포함한 기준 문단으로 만든다."""
    parsed = parse_problem_text(region.extractor.ocr_text or "")
    root.append(build_first_problem_paragraph(profile.first_problem, number, parsed.stem, year, runtime, idgen))
    for paragraph in clone_title_paragraphs(profile.title_paragraphs, year):
        root.append(paragraph)
    root.append(clone_paragraph(profile.problem_gap, idgen))
    append_region_body(root, profile, root_path, region, parsed, bindata_dir, runtime, idgen, warnings, images_info)


def append_repeated_region(
    root: Any,
    profile: ReferenceParagraphProfile,
    root_path: Path,
    region: Any,
    number: int,
    bindata_dir: Path,
    runtime: Any,
    idgen: Any,
    warnings: Any,
    images_info: list[dict[str, str]],
) -> None:
    """추가 문제 블록은 제목 scaffold 없이 기준 문제 문단을 복제한다."""
    parsed = parse_problem_text(region.extractor.ocr_text or "")
    root.append(build_problem_paragraph(profile.repeated_problem, number, parsed.stem, runtime, idgen))
    append_region_body(root, profile, root_path, region, parsed, bindata_dir, runtime, idgen, warnings, images_info)


def append_region_body(
    root: Any,
    profile: ReferenceParagraphProfile,
    root_path: Path,
    region: Any,
    parsed: ParsedProblemText,
    bindata_dir: Path,
    runtime: Any,
    idgen: Any,
    warnings: Any,
    images_info: list[dict[str, str]],
) -> None:
    """문제 stem 다음의 이미지, 보기, 해설 블록을 순서대로 붙인다."""
    image_info = copy_region_image(root_path, bindata_dir, region, len(images_info) + 2, warnings)
    if image_info is not None:
        images_info.append(image_info)
        root.append(build_picture_paragraph(profile.image, image_info["id"], idgen))
    if parsed.choices is not None:
        root.append(build_choice_paragraph(profile.choice, parsed.choices, runtime, idgen))
    root.append(clone_paragraph(profile.choice_gap, idgen))
    append_explanation_block(root, profile, region.extractor.explanation or "", runtime, idgen)


def append_explanation_block(
    root: Any,
    profile: ReferenceParagraphProfile,
    explanation: str,
    runtime: Any,
    idgen: Any,
) -> None:
    """해설이 있으면 label과 본문 문단을 레퍼런스 스타일로 붙인다."""
    if not explanation.strip():
        return
    root.append(clone_paragraph(profile.explanation_label, idgen))
    root.append(clone_paragraph(profile.explanation_blank, idgen))
    for line in explanation.splitlines():
        if line.strip():
            root.append(build_text_paragraph(profile.explanation_body, line.strip(), runtime, idgen))
            continue
        root.append(clone_paragraph(profile.explanation_blank, idgen))


def _append_header_only(root: Any, profile: ReferenceParagraphProfile, year: str) -> None:
    """내보낼 문항이 없을 때는 제목 영역만 유지한다."""
    root.append(build_first_problem_paragraph(profile.first_problem, 1, "", year, DummyRuntime(), DummyIdGen()))
    for paragraph in clone_title_paragraphs(profile.title_paragraphs, year):
        root.append(paragraph)


def build_first_problem_paragraph(template: Any, number: int, stem: str, year: str, runtime: Any, idgen: Any) -> Any:
    """첫 문제 문단의 제목 scaffold는 유지하고 번호/본문만 바꾼다."""
    paragraph = clone_paragraph(template, idgen)
    replace_year_in_element(paragraph, year)
    runs = paragraph.findall("hp:run", NS)
    if len(runs) < 4:
        raise ValueError(TEMPLATE_ERROR_CODES["copy"])
    fill_run_text(runs[2], f"{number}.")
    fill_run_with_math(runs[3], stem, runtime, idgen)
    return paragraph


def build_problem_paragraph(template: Any, number: int, stem: str, runtime: Any, idgen: Any) -> Any:
    """반복 문제 문단에 번호와 본문을 채운다."""
    paragraph = clone_paragraph(template, idgen)
    runs = paragraph.findall("hp:run", NS)
    if len(runs) < 2:
        raise ValueError(TEMPLATE_ERROR_CODES["copy"])
    fill_run_text(runs[0], f"{number}.")
    fill_run_with_math(runs[1], stem, runtime, idgen)
    return paragraph


def build_picture_paragraph(template: Any, bindata_id: str, idgen: Any) -> Any:
    """레퍼런스 그림 문단을 복제하고 binaryItemIDRef만 교체한다."""
    paragraph = clone_paragraph(template, idgen)
    picture = paragraph.find(".//hp:pic", NS)
    image = paragraph.find(".//hc:img", NS)
    if picture is None or image is None:
        raise ValueError(TEMPLATE_ERROR_CODES["profile"])
    picture.set("id", idgen.next())
    picture.set("instid", idgen.next())
    picture.set("zOrder", idgen.next())
    image.set("binaryItemIDRef", bindata_id)
    return paragraph


def build_choice_paragraph(template: Any, choices: tuple[str, ...], runtime: Any, idgen: Any) -> Any:
    """레퍼런스 보기 문단을 복제해 OCR에서 파싱한 선택지를 채운다."""
    paragraph = clone_paragraph(template, idgen)
    clear_children_by_name(paragraph, "run")
    for index, value in enumerate(choices):
        paragraph.append(make_text_run("0", f"{CHOICE_MARKERS[index]} "))
        for run in build_inline_runs(value, "0", runtime, idgen):
            paragraph.append(run)
        if index < len(choices) - 1:
            paragraph.append(make_tab_run("0", "4083" if index == 0 else "3000"))
    return paragraph


def build_text_paragraph(template: Any, text: str, runtime: Any, idgen: Any) -> Any:
    """레퍼런스 본문 문단을 복제해 텍스트와 수식을 채운다."""
    paragraph = clone_paragraph(template, idgen)
    clear_children_by_name(paragraph, "run")
    for run in build_inline_runs(text, "10", runtime, idgen):
        paragraph.append(run)
    return paragraph


def clone_title_paragraphs(paragraphs: tuple[Any, ...], year: str) -> list[Any]:
    """상단 연도/과목 문단을 깊은 복제하고 연도만 교체한다."""
    cloned = [deepcopy(paragraph) for paragraph in paragraphs]
    for paragraph in cloned:
        replace_year_in_element(paragraph, year)
    return cloned


def build_repeated_problem_template(first_problem: Any) -> Any:
    """첫 문제 문단에서 제목 scaffold를 제거한 반복용 문제 문단을 만든다."""
    paragraph = deepcopy(first_problem)
    runs = paragraph.findall("hp:run", NS)
    for run in runs[:2]:
        paragraph.remove(run)
    drop_linesegarray(paragraph)
    return paragraph


def parse_problem_text(ocr_text: str) -> ParsedProblemText:
    """OCR 본문에서 보기 줄을 분리하고 나머지를 stem으로 합친다."""
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    choice_lines = [line for line in lines if any(marker in line for marker in CHOICE_MARKERS)]
    stem_lines = [line for line in lines if line not in choice_lines]
    choices = parse_choices(" ".join(choice_lines)) if choice_lines else None
    return ParsedProblemText(stem=" ".join(stem_lines).strip(), choices=choices)


def parse_choices(choice_line: str) -> tuple[str, ...] | None:
    """①~⑤ 패턴이 완성된 줄만 5지선다 보기로 복원한다."""
    if not all(marker in choice_line for marker in CHOICE_MARKERS):
        return None
    positions = [choice_line.index(marker) for marker in CHOICE_MARKERS]
    values: list[str] = []
    for index, marker in enumerate(CHOICE_MARKERS):
        start = positions[index] + len(marker)
        end = positions[index + 1] if index < len(CHOICE_MARKERS) - 1 else len(choice_line)
        values.append(choice_line[start:end].strip())
    return tuple(values) if all(values) else None


def copy_region_image(root_path: Path, bindata_dir: Path, region: Any, index: int, warnings: Any) -> dict[str, str] | None:
    """영역 이미지를 BinData로 복사하고 manifest/header 갱신 정보를 만든다."""
    image_rel = resolve_region_image_path(region)
    if image_rel is None:
        return None
    source = root_path / image_rel
    if not source.exists():
        warnings.add("missing_region_image", f"region={region.context.id} path={image_rel}")
        return None
    extension = (source.suffix[1:].lower() or "png")
    bindata_id = f"image{index}"
    filename = f"{bindata_id}.{extension}"
    shutil.copy2(source, bindata_dir / filename)
    return {"id": bindata_id, "filename": filename, "ext": extension}


def resolve_region_image_path(region: Any) -> str | None:
    """영역에서 사용 가능한 이미지 경로를 우선순위대로 선택한다."""
    return (
        region.figure.styled_image_url
        or region.figure.image_crop_url
        or region.figure.png_rendered_url
        or region.figure.crop_url
    )


def write_section_xml(section_path: Path, root: Any) -> None:
    """완성된 section 트리를 UTF-8 XML 파일로 기록한다."""
    tree = etree.ElementTree(root)
    tree.write(str(section_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)


def clone_paragraph(paragraph: Any, idgen: Any) -> Any:
    """문단을 깊은 복제하고 linesegarray를 제거해 동적 내용에 맞게 만든다."""
    cloned = deepcopy(paragraph)
    cloned.set("id", idgen.next())
    drop_linesegarray(cloned)
    return cloned


def clear_children_by_name(paragraph: Any, local_name: str) -> None:
    """문단 아래에서 특정 local-name을 가진 자식들을 제거한다."""
    for child in list(paragraph):
        if etree.QName(child).localname == local_name:
            paragraph.remove(child)


def drop_linesegarray(paragraph: Any) -> None:
    """한글이 다시 계산할 수 있도록 linesegarray를 제거한다."""
    clear_children_by_name(paragraph, "linesegarray")


def replace_year_in_element(element: Any, year: str) -> None:
    """요소 트리 안의 학년도 텍스트를 현재 연도로 교체한다."""
    for text_node in element.xpath(".//hp:t", namespaces=NS):
        if text_node.text:
            text_node.text = re.sub(r"\d{4}학년도", f"{year}학년도", text_node.text)


def fill_run_text(run: Any, text: str) -> None:
    """run 안의 기존 내용을 비우고 plain text 하나만 넣는다."""
    for child in list(run):
        run.remove(child)
    text_node = etree.SubElement(run, qname("t"))
    text_node.text = text


def fill_run_with_math(run: Any, text: str, runtime: Any, idgen: Any) -> None:
    """run 안에 텍스트와 <math> 수식을 섞어 다시 채운다."""
    for child in list(run):
        run.remove(child)
    char_pr = run.get("charPrIDRef", "0")
    append_math_children(run, text, char_pr, runtime, idgen)


def append_math_children(run: Any, text: str, char_pr: str, runtime: Any, idgen: Any) -> None:
    """하나의 run 안에 일반 텍스트와 수식 요소를 순서대로 추가한다."""
    added = False
    for is_math, part in split_math_text(text):
        if not part:
            continue
        if is_math:
            equation_run = parse_run_fragment(runtime.make_equation_run(idgen, part, int(char_pr), 1100))
            for child in equation_run:
                run.append(deepcopy(child))
            added = True
            continue
        text_node = etree.SubElement(run, qname("t"))
        text_node.text = part
        added = True
    if not added:
        etree.SubElement(run, qname("t"))


def build_inline_runs(text: str, char_pr: str, runtime: Any, idgen: Any) -> list[Any]:
    """텍스트와 수식을 run 리스트로 나눠 만들어 반환한다."""
    runs: list[Any] = []
    for is_math, part in split_math_text(text):
        if not part:
            continue
        if is_math:
            runs.append(parse_run_fragment(runtime.make_equation_run(idgen, part, int(char_pr), 1100)))
            continue
        runs.append(make_text_run(char_pr, part))
    return runs or [make_text_run(char_pr, "")]


def split_math_text(text: str) -> list[tuple[bool, str]]:
    """`<math>` 태그를 기준으로 일반 텍스트와 수식 조각을 분리한다."""
    parts = re.split(r"(<math>.*?</math>)", text, flags=re.DOTALL)
    return [
        (part.startswith("<math>") and part.endswith("</math>"), part[6:-7].strip() if part.startswith("<math>") else part)
        for part in parts
        if part
    ]


def make_text_run(char_pr: str, text: str) -> Any:
    """plain text 하나만 담는 run 요소를 만든다."""
    run = etree.Element(qname("run"))
    run.set("charPrIDRef", char_pr)
    text_node = etree.SubElement(run, qname("t"))
    text_node.text = text
    return run


def make_tab_run(char_pr: str, width: str) -> Any:
    """보기 줄 간격을 맞추는 tab run을 만든다."""
    run = etree.Element(qname("run"))
    run.set("charPrIDRef", char_pr)
    etree.SubElement(run, qname("tab"), width=width, leader="0", type="1")
    return run


def require_paragraph(paragraphs: list[Any], matcher: Any, name: str) -> Any:
    """조건에 맞는 기준 문단을 찾지 못하면 치명 오류를 발생시킨다."""
    for paragraph in paragraphs:
        if matcher(paragraph):
            return paragraph
    raise ValueError(f"{TEMPLATE_ERROR_CODES['profile']}: {name}")


def next_sibling_paragraph(paragraphs: list[Any], paragraph: Any, name: str) -> Any:
    """기준 문단 다음의 형제 문단을 찾아 반환한다."""
    index = paragraphs.index(paragraph)
    if index + 1 >= len(paragraphs):
        raise ValueError(f"{TEMPLATE_ERROR_CODES['profile']}: {name}")
    return paragraphs[index + 1]


def _clear_root_paragraphs(root: Any) -> None:
    """section 루트 바로 아래의 문단을 모두 제거한다."""
    for child in list(root):
        if etree.QName(child).localname == "p":
            root.remove(child)


def qname(local_name: str) -> str:
    """paragraph namespace를 가진 QName 문자열을 만든다."""
    return f"{{{HP_NS}}}{local_name}"


def parse_run_fragment(xml: str) -> Any:
    """namespace 선언이 없는 run fragment를 lxml 요소로 파싱한다."""
    normalized = xml.replace("<hp:run ", f'<hp:run xmlns:hp="{HP_NS}" ', 1)
    return etree.fromstring(normalized)


class DummyIdGen:
    """문항이 없는 문서에서 최소 복제를 위해 쓰는 임시 id 생성기다."""

    def next(self) -> str:
        """항상 같은 dummy id를 반환한다."""
        return "0"


class DummyRuntime:
    """문항이 없는 문서에서는 수식 run 생성이 필요 없다."""

    def make_equation_run(self, idgen: Any, script: str, char_pr: int, base_unit: int) -> str:
        """호출되면 빈 run XML을 반환한다."""
        return f'<hp:run xmlns:hp="{HP_NS}" charPrIDRef="{char_pr}"><hp:t/></hp:run>'
