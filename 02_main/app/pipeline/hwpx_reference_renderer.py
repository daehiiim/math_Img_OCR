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


@dataclass(frozen=True)
class ParsedProblem:
    """OCR 본문에서 분리한 문제 stem/보기 값을 보관한다."""

    stem: str
    choices: tuple[str, ...] | None


@dataclass(frozen=True)
class ReferenceProfile:
    """레퍼런스 section에서 재사용할 문단 subtree를 보관한다."""

    root: Any
    first_problem: Any
    repeated_problem: Any
    problem_gap: Any
    picture: Any
    choice: Any
    choice_labels: tuple[Any, ...]
    choice_equations: tuple[Any, ...]
    choice_gap: Any
    explanation_label: Any
    explanation_blank: Any
    explanation_plain: Any
    explanation_mixed: Any
    mixed_text: Any
    mixed_equation: Any


def render_section_from_reference(
    section_path: Path,
    root_path: Path,
    job: Any,
    bindata_dir: Path,
    runtime: Any,
    context: Any,
    warnings: Any,
) -> list[dict[str, str]]:
    """레퍼런스 section0.xml을 복제해 현재 job 본문으로 다시 만든다."""
    profile = load_reference_profile(section_path)
    root = deepcopy(profile.root)
    clear_direct_paragraphs(root)
    idgen = runtime.IDGen()
    images_info: list[dict[str, str]] = []
    regions = collect_exportable_regions(job)
    for number, region in enumerate(regions, start=1):
        append_region(
            root,
            profile,
            root_path,
            region,
            number,
            bindata_dir,
            idgen,
            context.year,
            warnings,
            images_info,
        )
    write_section_xml(section_path, root)
    return images_info


def load_reference_profile(section_path: Path) -> ReferenceProfile:
    """레퍼런스 section0.xml에서 direct 문단 anchor를 추출한다."""
    root = etree.parse(str(section_path)).getroot()
    paragraphs = root.findall("hp:p", NS)
    first_problem = require_paragraph(paragraphs, lambda node: node.find(".//hp:tbl", NS) is not None)
    picture = require_paragraph(paragraphs, lambda node: node.find(".//hp:pic", NS) is not None)
    choice = require_paragraph(paragraphs, lambda node: "①" in "".join(node.xpath(".//hp:t/text()", namespaces=NS)))
    explanation_label = require_paragraph(paragraphs, lambda node: "[해설]" in "".join(node.xpath(".//hp:t/text()", namespaces=NS)))
    explanation_mixed = require_paragraph(paragraphs, lambda node: bool(node.findall(".//hp:equation", NS)))
    explanation_plain = require_paragraph(paragraphs, lambda node: node.get("paraPrIDRef") == "4" and node.get("styleIDRef") == "0" and not node.findall(".//hp:equation", NS) and bool("".join(node.xpath(".//hp:t/text()", namespaces=NS)).strip()) and "[해설]" not in "".join(node.xpath(".//hp:t/text()", namespaces=NS)))
    problem_gap = next_sibling(paragraphs, first_problem)
    choice_gap = next_sibling(paragraphs, choice)
    explanation_blank = next_sibling(paragraphs, explanation_label)
    return ReferenceProfile(
        root=root,
        first_problem=first_problem,
        repeated_problem=build_repeated_problem_template(first_problem),
        problem_gap=problem_gap,
        picture=picture,
        choice=choice,
        choice_labels=extract_choice_labels(choice),
        choice_equations=extract_choice_equations(choice),
        choice_gap=choice_gap,
        explanation_label=explanation_label,
        explanation_blank=explanation_blank,
        explanation_plain=explanation_plain,
        explanation_mixed=explanation_mixed,
        mixed_text=extract_mixed_text_template(explanation_mixed),
        mixed_equation=extract_mixed_equation_template(explanation_mixed),
    )


def collect_exportable_regions(job: Any) -> list[Any]:
    """본문이나 해설이 있는 영역만 order 기준으로 정렬해 반환한다."""
    regions = sorted(job.regions, key=lambda region: region.context.order)
    return [
        region
        for region in regions
        if (region.extractor.ocr_text or "").strip() or (region.extractor.explanation or "").strip()
    ]


def append_region(
    root: Any,
    profile: ReferenceProfile,
    root_path: Path,
    region: Any,
    number: int,
    bindata_dir: Path,
    idgen: Any,
    year: str,
    warnings: Any,
    images_info: list[dict[str, str]],
) -> None:
    """문항 하나를 problem/picture/choice/explanation subtree로 붙인다."""
    parsed = parse_problem_text(region.extractor.ocr_text or "")
    root.append(build_problem_paragraph(profile, parsed.stem, number, year, idgen))
    root.append(clone_static_paragraph(profile.problem_gap, idgen))
    append_picture_paragraph(root, profile.picture, root_path, bindata_dir, region, idgen, warnings, images_info)
    append_choice_paragraph(root, profile, parsed.choices, idgen)
    root.append(clone_static_paragraph(profile.choice_gap, idgen))
    append_explanation_paragraphs(root, profile, region.extractor.explanation or "", idgen)


def build_problem_paragraph(
    profile: ReferenceProfile,
    stem: str,
    number: int,
    year: str,
    idgen: Any,
) -> Any:
    """첫 문항/반복 문항에 맞는 문제 문단을 복제해 채운다."""
    template = profile.first_problem if number == 1 else profile.repeated_problem
    paragraph = clone_dynamic_paragraph(template, idgen)
    replace_year_text(paragraph, year)
    runs = paragraph.findall("hp:run", NS)
    number_run = runs[2] if number == 1 else runs[0]
    text_run = runs[3] if number == 1 else runs[1]
    fill_text_run(number_run, f"{number}.")
    fill_mixed_run(text_run, stem, profile.mixed_text, profile.mixed_equation, idgen)
    return paragraph


def append_picture_paragraph(
    root: Any,
    template: Any,
    root_path: Path,
    bindata_dir: Path,
    region: Any,
    idgen: Any,
    warnings: Any,
    images_info: list[dict[str, str]],
) -> None:
    """이미지가 있으면 그림 문단을 복제해 BinData 참조를 바꿔 붙인다."""
    image_info = copy_region_image(root_path, bindata_dir, region, len(images_info) + 2, warnings)
    if image_info is None:
        return
    paragraph = clone_static_paragraph(template, idgen)
    picture = paragraph.find(".//hp:pic", NS)
    image = paragraph.find(".//hc:img", NS)
    picture.set("id", idgen.next())
    picture.set("instid", idgen.next())
    picture.set("zOrder", idgen.next())
    image.set("binaryItemIDRef", image_info["id"])
    images_info.append(image_info)
    root.append(paragraph)


def append_choice_paragraph(
    root: Any,
    profile: ReferenceProfile,
    choices: tuple[str, ...] | None,
    idgen: Any,
) -> None:
    """5지선다 파싱이 성공했을 때만 choice 문단을 붙인다."""
    if choices is None:
        return
    paragraph = clone_dynamic_paragraph(profile.choice, idgen)
    run = paragraph.find("hp:run", NS)
    clear_children(run)
    for index, choice in enumerate(choices):
        run.append(build_choice_label(profile.choice_labels[index], CHOICE_MARKERS[index]))
        run.append(build_choice_equation(profile.choice_equations[index], choice, idgen))
    root.append(paragraph)


def append_explanation_paragraphs(
    root: Any,
    profile: ReferenceProfile,
    explanation: str,
    idgen: Any,
) -> None:
    """해설이 있을 때 label/blank/body 문단을 순서대로 붙인다."""
    if not explanation.strip():
        return
    root.append(clone_static_paragraph(profile.explanation_label, idgen))
    root.append(clone_static_paragraph(profile.explanation_blank, idgen))
    for line in explanation.splitlines():
        if not line.strip():
            root.append(clone_static_paragraph(profile.explanation_blank, idgen))
            continue
        root.append(build_explanation_paragraph(profile, line.strip(), idgen))


def build_explanation_paragraph(profile: ReferenceProfile, line: str, idgen: Any) -> Any:
    """해설 줄을 plain/mixed paragraph 중 하나로 만들어 반환한다."""
    if has_math_tag(line):
        paragraph = clone_dynamic_paragraph(profile.explanation_mixed, idgen)
        run = paragraph.find("hp:run", NS)
        fill_mixed_run(run, line, profile.mixed_text, profile.mixed_equation, idgen)
        return paragraph
    paragraph = clone_dynamic_paragraph(profile.explanation_plain, idgen)
    run = paragraph.find("hp:run", NS)
    fill_text_run(run, line)
    return paragraph


def parse_problem_text(ocr_text: str) -> ParsedProblem:
    """OCR 본문에서 보기 줄을 분리하고 나머지는 stem으로 합친다."""
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    choice_lines = [line for line in lines if any(marker in line for marker in CHOICE_MARKERS)]
    stem_lines = [line for line in lines if line not in choice_lines]
    choice_text = " ".join(choice_lines)
    return ParsedProblem(stem=" ".join(stem_lines).strip(), choices=parse_choices(choice_text))


def parse_choices(choice_text: str) -> tuple[str, ...] | None:
    """①~⑤가 모두 있는 줄만 5개 보기로 복원한다."""
    if not choice_text or not all(marker in choice_text for marker in CHOICE_MARKERS):
        return None
    positions = [choice_text.index(marker) for marker in CHOICE_MARKERS]
    values: list[str] = []
    for index, marker in enumerate(CHOICE_MARKERS):
        start = positions[index] + len(marker)
        end = positions[index + 1] if index < len(CHOICE_MARKERS) - 1 else len(choice_text)
        values.append(choice_text[start:end].strip())
    return tuple(values) if all(values) else None


def build_choice_label(template: Any, marker: str) -> Any:
    """레퍼런스 label node를 복제해 선택지 마커만 교체한다."""
    node = deepcopy(template)
    tab = node.find("hp:tab", NS)
    if tab is None:
        node.text = f"{marker} "
        return node
    node.text = None
    tab.tail = f"{marker} "
    return node


def build_choice_equation(template: Any, script: str, idgen: Any) -> Any:
    """레퍼런스 choice equation node를 복제해 script와 id만 바꾼다."""
    equation = deepcopy(template)
    equation.set("id", idgen.next())
    equation.set("zOrder", idgen.next())
    equation.find("hp:script", NS).text = script
    return equation


def fill_mixed_run(run: Any, text: str, text_template: Any, equation_template: Any, idgen: Any) -> None:
    """하나의 run 안에 text/equation child를 섞어 다시 채운다."""
    clear_children(run)
    for is_math, part in split_math_text(text):
        if not part:
            continue
        if is_math:
            run.append(build_inline_equation(equation_template, part, idgen))
            continue
        run.append(build_text_node(text_template, part))


def fill_text_run(run: Any, text: str) -> None:
    """run 안의 자식을 비우고 plain text 하나만 넣는다."""
    clear_children(run)
    text_node = etree.SubElement(run, qname("t"))
    text_node.text = text


def build_inline_equation(template: Any, script: str, idgen: Any) -> Any:
    """레퍼런스 inline equation을 복제해 script와 id를 교체한다."""
    equation = deepcopy(template)
    equation.set("id", idgen.next())
    equation.set("zOrder", idgen.next())
    equation.find("hp:script", NS).text = script
    return equation


def build_text_node(template: Any, text: str) -> Any:
    """레퍼런스 text node를 복제해 텍스트만 바꾼다."""
    node = deepcopy(template)
    for child in list(node):
        node.remove(child)
    node.text = text
    return node


def split_math_text(text: str) -> list[tuple[bool, str]]:
    """`<math>` 태그 기준으로 텍스트와 수식 조각을 분리한다."""
    parts = re.split(r"(<math>.*?</math>)", text, flags=re.DOTALL)
    segments: list[tuple[bool, str]] = []
    for part in parts:
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


def clone_dynamic_paragraph(paragraph: Any, idgen: Any) -> Any:
    """동적 문단을 복제하고 linesegarray를 제거한다."""
    cloned = deepcopy(paragraph)
    cloned.set("id", idgen.next())
    remove_linesegarray(cloned)
    return cloned


def clone_static_paragraph(paragraph: Any, idgen: Any) -> Any:
    """정적 문단을 복제하고 문단 id만 새로 부여한다."""
    cloned = deepcopy(paragraph)
    cloned.set("id", idgen.next())
    return cloned


def build_repeated_problem_template(first_problem: Any) -> Any:
    """첫 문제 문단에서 title scaffold를 제거한 반복용 템플릿을 만든다."""
    paragraph = deepcopy(first_problem)
    runs = paragraph.findall("hp:run", NS)
    paragraph.remove(runs[0])
    paragraph.remove(runs[1])
    remove_linesegarray(paragraph)
    return paragraph


def remove_linesegarray(paragraph: Any) -> None:
    """문단 아래의 linesegarray를 제거한다."""
    for child in list(paragraph):
        if etree.QName(child).localname == "linesegarray":
            paragraph.remove(child)


def clear_children(node: Any) -> None:
    """요소의 모든 자식을 제거한다."""
    for child in list(node):
        node.remove(child)


def replace_year_text(element: Any, year: str) -> None:
    """요소 안의 학년도 문자열을 현재 연도로 바꾼다."""
    for text_node in element.xpath(".//hp:t", namespaces=NS):
        if text_node.text:
            text_node.text = re.sub(r"\d{4}학년도", f"{year}학년도", text_node.text)
        for child in text_node:
            if child.tail:
                child.tail = re.sub(r"\d{4}학년도", f"{year}학년도", child.tail)


def extract_choice_labels(choice_paragraph: Any) -> tuple[Any, ...]:
    """choice 문단의 label text node 템플릿 5개를 추출한다."""
    run = choice_paragraph.find("hp:run", NS)
    return tuple(child for child in run if etree.QName(child).localname == "t")


def extract_choice_equations(choice_paragraph: Any) -> tuple[Any, ...]:
    """choice 문단의 equation 템플릿 5개를 추출한다."""
    run = choice_paragraph.find("hp:run", NS)
    return tuple(child for child in run if etree.QName(child).localname == "equation")


def extract_mixed_text_template(paragraph: Any) -> Any:
    """mixed 문단에서 plain text 템플릿 하나를 추출한다."""
    run = paragraph.find("hp:run", NS)
    return next(child for child in run if etree.QName(child).localname == "t")


def extract_mixed_equation_template(paragraph: Any) -> Any:
    """mixed 문단에서 inline equation 템플릿 하나를 추출한다."""
    run = paragraph.find("hp:run", NS)
    return next(child for child in run if etree.QName(child).localname == "equation")


def copy_region_image(
    root_path: Path,
    bindata_dir: Path,
    region: Any,
    index: int,
    warnings: Any,
) -> dict[str, str] | None:
    """영역 이미지를 root BinData로 복사하고 manifest 정보를 만든다."""
    image_rel = resolve_region_image_path(region)
    if image_rel is None:
        return None
    source = root_path / image_rel
    if not source.exists():
        warnings.add("missing_region_image", f"region={region.context.id} path={image_rel}")
        return None
    extension = source.suffix[1:].lower() or "png"
    bindata_id = f"image{index}"
    filename = f"{bindata_id}.{extension}"
    shutil.copy2(source, bindata_dir / filename)
    return {"id": bindata_id, "filename": filename, "ext": extension}


def resolve_region_image_path(region: Any) -> str | None:
    """영역에서 사용 가능한 이미지 경로를 우선순위대로 찾는다."""
    return (
        region.figure.styled_image_url
        or region.figure.image_crop_url
        or region.figure.png_rendered_url
        or region.figure.crop_url
    )


def clear_direct_paragraphs(root: Any) -> None:
    """section 루트 직계 문단을 모두 제거한다."""
    for child in list(root):
        if etree.QName(child).localname == "p":
            root.remove(child)


def write_section_xml(section_path: Path, root: Any) -> None:
    """완성된 section XML을 UTF-8로 저장한다."""
    tree = etree.ElementTree(root)
    tree.write(str(section_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)


def require_paragraph(paragraphs: list[Any], matcher: Any) -> Any:
    """조건에 맞는 문단을 찾고 없으면 예외를 발생시킨다."""
    for paragraph in paragraphs:
        if matcher(paragraph):
            return paragraph
    raise ValueError("reference subtree 손상")


def next_sibling(paragraphs: list[Any], paragraph: Any) -> Any:
    """기준 문단의 다음 direct 형제 문단을 반환한다."""
    index = paragraphs.index(paragraph)
    if index + 1 >= len(paragraphs):
        raise ValueError("reference subtree 손상")
    return paragraphs[index + 1]


def qname(local_name: str) -> str:
    """paragraph namespace QName 문자열을 만든다."""
    return f"{{{HP_NS}}}{local_name}"
