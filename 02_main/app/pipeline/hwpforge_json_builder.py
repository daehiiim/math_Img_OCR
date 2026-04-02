from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from app.pipeline.hwpx_math_layout import (
    collect_equation_width_samples,
    estimate_inline_equation_width,
    has_math_tag,
    measure_equation_script,
    normalize_export_text,
    split_math_text,
)
from app.pipeline.hwpx_reference_renderer import collect_exportable_regions, copy_region_image, parse_problem_text

PARAGRAPH_LAYOUT_CACHE_KEYS = ("linesegarray", "hp:linesegarray", "line_segment_array")


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
    problem_text_run: dict[str, Any]
    choice_label_runs: tuple[dict[str, Any], ...]
    mixed_text_run: dict[str, Any]
    equation_template_runs: tuple[dict[str, Any], ...]
    equation_width_samples: tuple[tuple[int, int], ...]


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
    equation_runs = tuple(deepcopy(run) for run in choice_runs + mixed_runs if _is_equation_run(run))
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
        problem_text_run=deepcopy(paragraphs[0]["runs"][4]),
        choice_label_runs=tuple(deepcopy(run) for run in choice_runs if "Text" in run["content"]),
        mixed_text_run=deepcopy(next(run for run in mixed_runs if "Text" in run["content"])),
        equation_template_runs=equation_runs,
        equation_width_samples=tuple(
            collect_equation_width_samples(
                (_read_equation_script(run), _read_equation_width(run)) for run in equation_runs
            )
        ),
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
    body_index = 4 if number == 1 else 1
    number_index = body_index - 1
    if number == 1:
        _replace_year_text(paragraph, year)
    paragraph["runs"][number_index]["content"]["Text"] = f"{number}."
    paragraph["runs"] = paragraph["runs"][:body_index] + _build_mixed_runs(
        profile,
        stem,
        profile.problem_text_run,
        profile.problem_text_run["char_shape_id"],
    )
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
    char_shape_id = profile.choice_label_runs[0]["char_shape_id"]
    for index, choice in enumerate(choices):
        paragraph["runs"].append(_build_choice_label_run(profile.choice_label_runs[index], index))
        paragraph["runs"].append(_build_equation_run(profile, choice, char_shape_id))
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
    paragraph["runs"] = _build_mixed_runs(
        profile,
        normalized_line,
        profile.mixed_text_run,
        profile.mixed_text_run["char_shape_id"],
    )
    return paragraph


def _build_mixed_runs(
    profile: JsonTemplateProfile,
    normalized_text: str,
    text_template: dict[str, Any],
    char_shape_id: int,
) -> list[dict[str, Any]]:
    """segment 순서를 유지하며 text/equation run 배열을 만든다."""
    runs: list[dict[str, Any]] = []
    for is_math, part in split_math_text(normalized_text):
        if not part:
            continue
        if is_math:
            runs.append(_build_equation_run(profile, part, char_shape_id))
            continue
        runs.append(_build_text_run(text_template, part))
    return runs or [_build_text_run(text_template, "")]


def _build_text_run(template_run: dict[str, Any], text: str) -> dict[str, Any]:
    """텍스트 run 템플릿을 복제해 본문 문자열만 교체한다."""
    run = _clone_run(template_run)
    run["content"]["Text"] = text
    return run


def _build_equation_run(profile: JsonTemplateProfile, script: str, char_shape_id: int) -> dict[str, Any]:
    """공통 템플릿과 폭 계산 규칙으로 equation run을 만든다."""
    run = _clone_run(_select_equation_run_template(profile.equation_template_runs, script))
    run["char_shape_id"] = char_shape_id
    equation = run["content"]["Control"]["Equation"]
    equation["script"] = script
    estimated_width = estimate_inline_equation_width(
        list(profile.equation_width_samples),
        script,
        int(equation.get("width", 0) or 0),
    )
    if estimated_width > 0:
        equation["width"] = estimated_width
    return run


def _select_equation_run_template(
    template_runs: tuple[dict[str, Any], ...],
    script: str,
) -> dict[str, Any]:
    """대상 script 길이와 가장 가까운 equation 템플릿 run을 고른다."""
    target_metric = measure_equation_script(script)
    return min(
        template_runs,
        key=lambda run: (
            abs(measure_equation_script(_read_equation_script(run)) - target_metric),
            _read_equation_width(run),
        ),
    )


def _read_equation_script(run: dict[str, Any]) -> str:
    """JSON equation run의 script 문자열을 읽어 온다."""
    return run["content"]["Control"]["Equation"].get("script", "")


def _read_equation_width(run: dict[str, Any]) -> int:
    """JSON equation run의 width 값을 정수로 반환한다."""
    return int(run["content"]["Control"]["Equation"].get("width", 0) or 0)


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
    """문단 템플릿을 안전하게 복제하고 stale layout cache를 제거한다."""
    cloned = deepcopy(paragraph)
    _strip_paragraph_layout_cache(cloned)
    return cloned


def _clone_run(run: dict[str, Any]) -> dict[str, Any]:
    """run 템플릿을 안전하게 복제한다."""
    return deepcopy(run)


def _strip_paragraph_layout_cache(node: Any) -> None:
    """문단 dict 내부에 남은 linesegarray layout cache를 재귀적으로 제거한다."""
    if isinstance(node, dict):
        for cache_key in PARAGRAPH_LAYOUT_CACHE_KEYS:
            node.pop(cache_key, None)
        for value in node.values():
            _strip_paragraph_layout_cache(value)
        return
    if isinstance(node, list):
        for item in node:
            _strip_paragraph_layout_cache(item)
