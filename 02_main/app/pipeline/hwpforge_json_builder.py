from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from app.pipeline.hwpx_reference_renderer import (
    collect_exportable_regions,
    copy_region_image,
    has_math_tag,
    normalize_export_text,
    parse_problem_text,
    split_math_text,
)


@dataclass(frozen=True)
class JsonTemplateProfile:
    """HwpForge sample JSON에서 재사용할 문단/런 템플릿을 모은다."""

    first_problem: dict[str, Any]
    problem_gap: dict[str, Any]
    image: dict[str, Any]
    choice: dict[str, Any]
    choice_gap: dict[str, Any]
    explanation_label: dict[str, Any]
    explanation_blank: dict[str, Any]
    explanation_plain: dict[str, Any]
    explanation_mixed: dict[str, Any]
    choice_label_runs: tuple[dict[str, Any], ...]
    choice_equation_runs: tuple[dict[str, Any], ...]
    mixed_text_run: dict[str, Any]
    mixed_equation_runs: tuple[dict[str, Any], ...]


def build_hwpforge_export_ir(
    root_path: Path,
    job: Any,
    bindata_dir: Path,
    year: str,
    warnings: Any,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """job을 HwpForge helper 입력용 JSON IR과 이미지 manifest로 바꾼다."""
    images_info: list[dict[str, str]] = []
    regions_payload: list[dict[str, Any]] = []
    for number, region in enumerate(collect_exportable_regions(job), start=1):
        image_info = _copy_region_image(root_path, bindata_dir, region, len(images_info) + 2, warnings)
        if image_info is not None:
            images_info.append(image_info)
        parsed = parse_problem_text(_get_problem_source(region))
        regions_payload.append(
            {
                "number": number,
                "stem": parsed.stem,
                "choices": list(parsed.choices) if parsed.choices is not None else None,
                "image": _build_image_payload(image_info),
                "explanation_lines": _get_explanation_lines(region),
            }
        )
    return {"year": year, "regions": regions_payload}, images_info


def _get_problem_source(region: Any) -> str:
    """Markdown 우선순위로 problem 본문을 legacy markup 문자열로 반환한다."""
    if region.extractor.problem_markdown:
        return _restore_legacy_math_markup(region.extractor.problem_markdown)
    return region.extractor.ocr_text or ""


def _get_explanation_lines(region: Any) -> list[str]:
    """Markdown 우선순위로 explanation 줄 배열을 legacy markup 기준으로 반환한다."""
    if region.extractor.explanation_markdown:
        restored = _restore_legacy_math_markup(region.extractor.explanation_markdown)
        return restored.splitlines()
    return (region.extractor.explanation or "").splitlines()


def _restore_legacy_math_markup(value: str) -> str:
    """Markdown `$...$` 수식을 기존 `<math>...</math>` 형태로 되돌린다."""
    restored = re.sub(r"\$\$(.+?)\$\$", _replace_math_block, value, flags=re.DOTALL)
    return re.sub(r"\$(.+?)\$", _replace_math_inline, restored, flags=re.DOTALL)


def _replace_math_block(match: re.Match[str]) -> str:
    """block 수식을 legacy markup으로 치환한다."""
    return _wrap_math_tag(match.group(1))


def _replace_math_inline(match: re.Match[str]) -> str:
    """inline 수식을 legacy markup으로 치환한다."""
    return _wrap_math_tag(match.group(1))


def _wrap_math_tag(raw_value: str) -> str:
    """수식 문자열을 정리한 뒤 `<math>` wrapper로 감싼다."""
    value = str(raw_value or "").strip()
    return f"<math>{value}</math>" if value else ""


def build_exported_document_from_template(
    template_document: dict[str, Any],
    export_ir: dict[str, Any],
) -> dict[str, Any]:
    """sample ExportedDocument를 현재 export IR 본문으로 다시 만든다."""
    exported_document = deepcopy(template_document)
    profile = _build_template_profile(exported_document)
    paragraphs: list[dict[str, Any]] = []
    for region in export_ir["regions"]:
        paragraphs.extend(_build_region_paragraphs(profile, region, export_ir["year"]))
    exported_document["document"]["sections"][0]["paragraphs"] = paragraphs
    return exported_document


def _copy_region_image(
    root_path: Path,
    bindata_dir: Path,
    region: Any,
    index: int,
    warnings: Any,
) -> dict[str, str] | None:
    """기존 renderer와 같은 우선순위로 이미지를 BinData에 복사한다."""
    return copy_region_image(root_path, bindata_dir, region, index, warnings)


def _build_image_payload(image_info: dict[str, str] | None) -> dict[str, str] | None:
    """helper가 바로 쓸 수 있는 이미지 식별자 payload를 만든다."""
    if image_info is None:
        return None
    return {"bindata_id": image_info["id"], "ext": image_info["ext"]}


def _build_template_profile(template_document: dict[str, Any]) -> JsonTemplateProfile:
    """sample JSON 문단에서 재사용할 템플릿들을 추출한다."""
    paragraphs = template_document["document"]["sections"][0]["paragraphs"]
    choice_runs = paragraphs[3]["runs"]
    mixed_runs = paragraphs[8]["runs"] + paragraphs[9]["runs"]
    return JsonTemplateProfile(
        first_problem=deepcopy(paragraphs[0]),
        problem_gap=deepcopy(paragraphs[1]),
        image=deepcopy(paragraphs[2]),
        choice=deepcopy(paragraphs[3]),
        choice_gap=deepcopy(paragraphs[4]),
        explanation_label=deepcopy(paragraphs[5]),
        explanation_blank=deepcopy(paragraphs[6]),
        explanation_plain=deepcopy(paragraphs[7]),
        explanation_mixed=deepcopy(paragraphs[8]),
        choice_label_runs=tuple(deepcopy(run) for run in choice_runs if "Text" in run["content"]),
        choice_equation_runs=tuple(deepcopy(run) for run in choice_runs if _is_equation_run(run)),
        mixed_text_run=deepcopy(next(run for run in mixed_runs if "Text" in run["content"])),
        mixed_equation_runs=tuple(deepcopy(run) for run in mixed_runs if _is_equation_run(run)),
    )


def _build_region_paragraphs(
    profile: JsonTemplateProfile,
    region: dict[str, Any],
    year: str,
) -> list[dict[str, Any]]:
    """영역 하나를 문항 순서에 맞는 문단 배열로 만든다."""
    paragraphs = [
        _build_problem_paragraph(profile, region["number"], region["stem"], year),
        _clone_paragraph(profile.problem_gap),
    ]
    if region["image"] is not None:
        paragraphs.append(_build_image_paragraph(profile, region["image"]))
    if region["choices"] is not None:
        paragraphs.append(_build_choice_paragraph(profile, region["choices"]))
        paragraphs.append(_clone_paragraph(profile.choice_gap))
    paragraphs.extend(_build_explanation_paragraphs(profile, region["explanation_lines"]))
    return paragraphs


def _build_problem_paragraph(
    profile: JsonTemplateProfile,
    number: int,
    stem: str,
    year: str,
) -> dict[str, Any]:
    """첫 문제/반복 문제에 맞는 problem 문단을 만든다."""
    paragraph = _clone_paragraph(profile.first_problem if number == 1 else _build_repeated_problem(profile))
    if number == 1:
        _replace_year_text(paragraph, year)
        paragraph["runs"][3]["content"]["Text"] = f"{number}."
        paragraph["runs"][4]["content"]["Text"] = stem
        return paragraph
    paragraph["runs"][0]["content"]["Text"] = f"{number}."
    paragraph["runs"][1]["content"]["Text"] = stem
    return paragraph


def _build_repeated_problem(profile: JsonTemplateProfile) -> dict[str, Any]:
    """첫 문제 템플릿에서 제목 scaffold를 뺀 반복용 문단을 만든다."""
    paragraph = _clone_paragraph(profile.first_problem)
    paragraph["runs"] = [deepcopy(paragraph["runs"][3]), deepcopy(paragraph["runs"][4])]
    return paragraph


def _build_image_paragraph(profile: JsonTemplateProfile, image: dict[str, str]) -> dict[str, Any]:
    """이미지 BinData 식별자를 현재 region 값으로 치환한다."""
    paragraph = _clone_paragraph(profile.image)
    image_node = paragraph["runs"][0]["content"]["Image"]
    bindata_id = image["bindata_id"]
    image_node["path"] = f"BinData/{bindata_id}"
    image_node["format"] = {"Unknown": bindata_id}
    return paragraph


def _build_choice_paragraph(
    profile: JsonTemplateProfile,
    choices: list[str],
) -> dict[str, Any]:
    """보기 5개를 label/equation run으로 다시 채운다."""
    paragraph = _clone_paragraph(profile.choice)
    paragraph["runs"] = []
    for index, choice in enumerate(choices):
        paragraph["runs"].append(_build_choice_label_run(profile.choice_label_runs[index], index))
        paragraph["runs"].append(_build_equation_run(profile.choice_equation_runs[index], choice))
    return paragraph


def _build_choice_label_run(template_run: dict[str, Any], index: int) -> dict[str, Any]:
    """보기 번호 텍스트를 현재 index에 맞게 바꾼다."""
    run = _clone_run(template_run)
    run["content"]["Text"] = f"{chr(9312 + index)} " if index == 0 else f"\t{chr(9312 + index)} "
    return run


def _build_explanation_paragraphs(
    profile: JsonTemplateProfile,
    lines: list[str],
) -> list[dict[str, Any]]:
    """해설 본문 줄 배열을 label/blank/body 문단으로 변환한다."""
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return []
    paragraphs = [_clone_paragraph(profile.explanation_label), _clone_paragraph(profile.explanation_blank)]
    for line in lines:
        if not line.strip():
            paragraphs.append(_clone_paragraph(profile.explanation_blank))
            continue
        paragraphs.append(_build_explanation_paragraph(profile, line))
    return paragraphs


def _build_explanation_paragraph(
    profile: JsonTemplateProfile,
    raw_line: str,
) -> dict[str, Any]:
    """plain/mixed 여부에 따라 해설 문단 하나를 만든다."""
    normalized_line = normalize_export_text(raw_line.strip())
    if has_math_tag(normalized_line):
        return _build_mixed_paragraph(profile, normalized_line)
    paragraph = _clone_paragraph(profile.explanation_plain)
    paragraph["runs"] = [_build_text_run(paragraph["runs"][0], normalized_line)]
    return paragraph


def _build_mixed_paragraph(
    profile: JsonTemplateProfile,
    normalized_line: str,
) -> dict[str, Any]:
    """텍스트와 inline 수식이 섞인 해설 문단을 만든다."""
    paragraph = _clone_paragraph(profile.explanation_mixed)
    paragraph["runs"] = []
    equation_index = 0
    for is_math, part in split_math_text(normalized_line):
        if not part:
            continue
        if is_math:
            paragraph["runs"].append(_build_equation_run(profile.mixed_equation_runs[equation_index % len(profile.mixed_equation_runs)], part))
            equation_index += 1
            continue
        paragraph["runs"].append(_build_text_run(profile.mixed_text_run, part))
    return paragraph


def _build_text_run(template_run: dict[str, Any], text: str) -> dict[str, Any]:
    """텍스트 run 템플릿을 복제해 본문 문자열만 교체한다."""
    run = _clone_run(template_run)
    run["content"]["Text"] = text
    return run


def _build_equation_run(template_run: dict[str, Any], script: str) -> dict[str, Any]:
    """수식 run 템플릿을 복제해 equation script만 교체한다."""
    run = _clone_run(template_run)
    run["content"]["Control"]["Equation"]["script"] = script
    return run


def _replace_year_text(paragraph: dict[str, Any], year: str) -> None:
    """제목 표 안의 학년도 문자열을 현재 render context 값으로 바꾼다."""
    for run in paragraph["runs"]:
        content = run["content"]
        if "Table" in content:
            _replace_year_text_in_table(content["Table"], year)


def _replace_year_text_in_table(table: dict[str, Any], year: str) -> None:
    """표 내부 문단의 학년도 텍스트를 재귀적으로 치환한다."""
    for row in table["rows"]:
        for cell in row["cells"]:
            for paragraph in cell["paragraphs"]:
                for run in paragraph["runs"]:
                    if "Text" in run["content"]:
                        run["content"]["Text"] = run["content"]["Text"].replace("2026학년도", f"{year}학년도")


def _is_equation_run(run: dict[str, Any]) -> bool:
    """run content가 Equation control인지 판별한다."""
    control = run["content"].get("Control")
    return isinstance(control, dict) and "Equation" in control


def _clone_paragraph(paragraph: dict[str, Any]) -> dict[str, Any]:
    """문단 템플릿을 안전하게 복제한다."""
    return deepcopy(paragraph)


def _clone_run(run: dict[str, Any]) -> dict[str, Any]:
    """run 템플릿을 안전하게 복제한다."""
    return deepcopy(run)
