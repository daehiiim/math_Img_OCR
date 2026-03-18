from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

from app.config import get_settings
from app.pipeline.schema import JobPipelineContext, RegionPipelineContext

BACKEND_ROOT = Path(__file__).resolve().parents[2]
HWPX_SKILL_NAME = "hwpxskill-math"
REQUIRED_RUNTIME_ITEMS = (
    Path("scripts/xml_primitives.py"),
    Path("scripts/exam_helpers.py"),
    Path("scripts/hwpx_utils.py"),
    Path("templates/base/Contents/header.xml"),
    Path("templates/base/Contents/content.hpf"),
    Path("templates/base/Contents/section0.xml"),
    Path("templates/base/mimetype"),
)


@dataclass(frozen=True)
class HwpxRuntime:
    """HWPX export에 필요한 런타임 모듈과 템플릿 경로를 묶는다."""

    skill_dir: Path
    base_dir: Path
    xml_primitives: ModuleType
    exam_helpers: ModuleType
    hwpx_utils: ModuleType


def export_hwpx(root_path: Path, job: JobPipelineContext, export_dir: Path) -> Path:
    """OCR 결과를 HWPX 파일로 내보내고 구조 검증까지 수행한다."""
    runtime = _resolve_hwpx_runtime()
    export_dir.mkdir(parents=True, exist_ok=True)
    hwpx_path = export_dir / f"{job.job_id}.hwpx"

    with tempfile.TemporaryDirectory() as tmpdir_str:
        work_dir = Path(tmpdir_str) / "build"
        shutil.copytree(runtime.base_dir, work_dir)
        images_info = _build_hwpx_worktree(root_path, job, work_dir, runtime)
        runtime.hwpx_utils.pack_hwpx(work_dir, hwpx_path)

    errors = runtime.hwpx_utils.validate_hwpx(hwpx_path)
    if errors:
        raise ValueError(f"HWPX Validation failed: {errors}")
    return hwpx_path


def _build_hwpx_worktree(
    root_path: Path,
    job: JobPipelineContext,
    work_dir: Path,
    runtime: HwpxRuntime,
) -> list[dict[str, str]]:
    """임시 템플릿 디렉터리에 본문과 메타데이터를 반영한다."""
    section_path = work_dir / "Contents" / "section0.xml"
    bindata_dir = work_dir / "Contents" / "BinData"
    bindata_dir.mkdir(parents=True, exist_ok=True)
    images_info = _generate_section0_xml(root_path, job, section_path, bindata_dir, runtime)
    content_hpf = work_dir / "Contents" / "content.hpf"
    runtime.hwpx_utils.update_metadata(content_hpf, f"MathOCR_{job.job_id}", "MathOCR")
    _inject_images_to_manifest(content_hpf, images_info)
    _update_header_xml(work_dir / "Contents" / "header.xml", images_info)
    return images_info


def _resolve_hwpx_runtime() -> HwpxRuntime:
    """사용 가능한 HWPX runtime bundle을 찾아 로드한다."""
    checked_candidates: list[tuple[Path, list[str]]] = []
    found_existing_candidate = False

    for skill_dir in _build_hwpx_skill_candidates():
        missing_items = _find_missing_runtime_items(skill_dir)
        checked_candidates.append((skill_dir, missing_items))
        found_existing_candidate = found_existing_candidate or skill_dir.exists()
        if not missing_items:
            return _load_hwpx_runtime(skill_dir)

    message = _build_runtime_error_message(checked_candidates)
    if found_existing_candidate:
        raise RuntimeError(message)
    raise FileNotFoundError(message)


def _build_hwpx_skill_candidates() -> list[Path]:
    """우선순위에 맞춰 중복 없는 HWPX runtime 후보 경로를 만든다."""
    raw_candidates: list[Path] = []
    configured_dir = _get_configured_hwpx_skill_dir()
    if configured_dir:
        raw_candidates.append(Path(configured_dir))
    raw_candidates.append(BACKEND_ROOT / "vendor" / HWPX_SKILL_NAME)
    codex_home = _get_codex_home()
    if codex_home is not None:
        raw_candidates.append(codex_home / "skills" / HWPX_SKILL_NAME)
    raw_candidates.append(_get_user_home() / ".codex" / "skills" / HWPX_SKILL_NAME)
    return _deduplicate_paths(_normalize_candidate(path) for path in raw_candidates)


def _get_configured_hwpx_skill_dir() -> str | None:
    """설정 파일 또는 환경변수에 정의된 HWPX runtime override를 읽는다."""
    return get_settings(BACKEND_ROOT).hwpx_skill_dir


def _get_codex_home() -> Path | None:
    """CODEX_HOME 환경변수가 있으면 Path로 반환한다."""
    raw_value = os.getenv("CODEX_HOME")
    if raw_value is None or not raw_value.strip():
        return None
    return Path(raw_value.strip()).expanduser()


def _get_user_home() -> Path:
    """사용자 홈 디렉터리를 반환한다."""
    return Path.home()


def _normalize_candidate(path: Path) -> Path:
    """후보 경로를 절대 경로로 정규화한다."""
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (BACKEND_ROOT / expanded).resolve()


def _deduplicate_paths(paths: list[Path]) -> list[Path]:
    """경로 순서를 유지한 채 중복 후보를 제거한다."""
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        unique_paths.append(path)
        seen.add(path)
    return unique_paths


def _find_missing_runtime_items(skill_dir: Path) -> list[str]:
    """주어진 runtime 경로에서 필수 파일 누락 목록을 계산한다."""
    missing_items: list[str] = []
    for rel_path in REQUIRED_RUNTIME_ITEMS:
        if not (skill_dir / rel_path).exists():
            missing_items.append(rel_path.as_posix())
    return missing_items


def _build_runtime_error_message(checked: list[tuple[Path, list[str]]]) -> str:
    """확인한 경로와 누락 파일을 포함한 사용자용 오류 메시지를 만든다."""
    checked_parts = [_format_checked_path(path, missing) for path, missing in checked]
    missing_items = sorted({item for _, missing in checked for item in missing})
    return (
        "HWPX export runtime not found. "
        f"checked: {'; '.join(checked_parts)} "
        f"missing: {', '.join(missing_items)}"
    )


def _format_checked_path(path: Path, missing_items: list[str]) -> str:
    """후보 경로별 상태를 사람이 읽기 쉬운 문자열로 만든다."""
    if not missing_items:
        return f"{path} (ok)"
    return f"{path} (missing: {', '.join(missing_items)})"


@lru_cache(maxsize=None)
def _load_hwpx_runtime(skill_dir: Path) -> HwpxRuntime:
    """선택된 runtime bundle에서 필요한 파이썬 모듈을 지연 로드한다."""
    scripts_dir = skill_dir / "scripts"
    xml_primitives = _load_runtime_module("xml_primitives", scripts_dir / "xml_primitives.py")
    exam_helpers = _load_runtime_module("exam_helpers", scripts_dir / "exam_helpers.py")
    hwpx_utils = _load_runtime_module("hwpx_utils", scripts_dir / "hwpx_utils.py")
    return HwpxRuntime(
        skill_dir=skill_dir,
        base_dir=skill_dir / "templates" / "base",
        xml_primitives=xml_primitives,
        exam_helpers=exam_helpers,
        hwpx_utils=hwpx_utils,
    )


def _load_runtime_module(module_name: str, module_path: Path) -> ModuleType:
    """지정된 파일 경로에서 runtime 모듈을 강제로 다시 로드한다."""
    loaded_module = sys.modules.get(module_name)
    if _is_matching_module(loaded_module, module_path):
        return loaded_module

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load HWPX runtime module: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _is_matching_module(module: ModuleType | None, module_path: Path) -> bool:
    """이미 로드된 모듈이 같은 파일을 가리키는지 확인한다."""
    if module is None:
        return False
    loaded_path = getattr(module, "__file__", None)
    if loaded_path is None:
        return False
    return Path(loaded_path).resolve() == module_path.resolve()


def _parse_math_text_to_runs(
    runtime: HwpxRuntime,
    id_generator,
    text: str,
    default_char_pr: int,
    base_unit: int = 1000,
) -> list[str]:
    """문자열을 일반 텍스트와 수식 run 목록으로 분해한다."""
    runs: list[str] = []
    if not text:
        return runs

    parts = re.split(r"(<math>.*?</math>)", text, flags=re.DOTALL)
    make_equation_run = runtime.xml_primitives._make_equation_run
    for part in parts:
        if not part:
            continue
        if part.startswith("<math>") and part.endswith("</math>"):
            math_script = part[6:-7].strip()
            runs.append(make_equation_run(id_generator, math_script, default_char_pr, base_unit))
            continue
        safe_text = escape(part)
        runs.append(f'<hp:run charPrIDRef="{default_char_pr}"><hp:t>{safe_text}</hp:t></hp:run>')
    return runs


def _generate_section0_xml(
    root_path: Path,
    job: JobPipelineContext,
    output_path: Path,
    bindata_dir: Path,
    runtime: HwpxRuntime,
) -> list[dict[str, str]]:
    """문제 영역을 section0.xml로 렌더링하고 이미지 목록을 반환한다."""
    xml_primitives = runtime.xml_primitives
    images_info: list[dict[str, str]] = []
    id_generator = xml_primitives.IDGen()
    paragraphs = _build_document_paragraphs(root_path, job, bindata_dir, runtime, id_generator, images_info)
    xml_content = _wrap_section_xml(paragraphs, xml_primitives.SEC_NAMESPACES)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_content, encoding="utf-8")
    return images_info


def _build_document_paragraphs(
    root_path: Path,
    job: JobPipelineContext,
    bindata_dir: Path,
    runtime: HwpxRuntime,
    id_generator,
    images_info: list[dict[str, str]],
) -> list[str]:
    """문서 전체 문단 목록을 머리말과 문제 본문으로 조합한다."""
    paragraphs = _build_document_header(runtime, id_generator, job.job_id)
    for region in sorted(job.regions, key=lambda item: item.context.order):
        paragraphs.extend(
            _build_region_paragraphs(root_path, region, bindata_dir, runtime, id_generator, images_info)
        )
    return paragraphs


def _build_document_header(runtime: HwpxRuntime, id_generator, job_id: str) -> list[str]:
    """문서 시작부에 들어가는 제목과 여백 문단을 만든다."""
    style = runtime.xml_primitives.STYLE
    make_empty_para = runtime.xml_primitives.make_empty_para
    make_multi_run_para = runtime.xml_primitives._make_multi_run_para
    return [
        runtime.exam_helpers.make_secpr_para(id_generator, col_count=2, same_gap=2268),
        make_multi_run_para(
            id_generator,
            [f'<hp:run charPrIDRef="{style["CHAR_EXAM_TITLE"]}"><hp:t>수학 분석 ({job_id})</hp:t></hp:run>'],
            para_pr=style["PARA_EXAM_TITLE"],
        ),
        make_empty_para(id_generator, para_pr=style["PARA_HR"], char_pr=0),
        make_empty_para(id_generator),
    ]


def _build_region_paragraphs(
    root_path: Path,
    region: RegionPipelineContext,
    bindata_dir: Path,
    runtime: HwpxRuntime,
    id_generator,
    images_info: list[dict[str, str]],
) -> list[str]:
    """영역 하나를 이미지, 문제 본문, 해설 문단으로 렌더링한다."""
    paragraphs: list[str] = []
    paragraphs.extend(_build_image_paragraphs(root_path, region, bindata_dir, runtime, id_generator, images_info))
    paragraphs.extend(_build_problem_paragraphs(runtime, region, id_generator))
    paragraphs.extend(_build_explanation_paragraphs(runtime, region, id_generator))
    paragraphs.extend(_build_region_separator(runtime, id_generator))
    return paragraphs


def _build_image_paragraphs(
    root_path: Path,
    region: RegionPipelineContext,
    bindata_dir: Path,
    runtime: HwpxRuntime,
    id_generator,
    images_info: list[dict[str, str]],
) -> list[str]:
    """영역 이미지가 있으면 BinData와 그림 문단을 추가한다."""
    image_url = region.figure.png_rendered_url or region.figure.crop_url
    if not image_url:
        return []

    source_path = root_path / image_url
    if not source_path.exists():
        return []

    style = runtime.xml_primitives.STYLE
    image_info = _copy_bindata_image(source_path, bindata_dir, region.context.id)
    images_info.append(image_info)
    return [
        runtime.exam_helpers.make_picture_para(
            id_generator,
            image_info["id"],
            width_hu=25000,
            height_hu=15000,
            para_pr=style["PARA_EQ"],
            char_pr=0,
        ),
        runtime.xml_primitives.make_empty_para(id_generator),
    ]


def _copy_bindata_image(source_path: Path, bindata_dir: Path, region_id: str) -> dict[str, str]:
    """원본 이미지를 BinData 디렉터리로 복사하고 메타정보를 만든다."""
    extension = source_path.suffix[1:].lower() or "png"
    clean_uuid = uuid.uuid4().hex
    bindata_filename = f"img_{region_id}_{clean_uuid}.{extension}"
    destination_path = bindata_dir / bindata_filename
    shutil.copy2(source_path, destination_path)
    return {
        "id": f"BIN_{region_id}_{clean_uuid}",
        "filename": bindata_filename,
        "ext": extension,
    }


def _build_problem_paragraphs(runtime: HwpxRuntime, region: RegionPipelineContext, id_generator) -> list[str]:
    """OCR 문제 본문을 여러 문단으로 변환한다."""
    ocr_text = (region.extractor.ocr_text or "").strip()
    if not ocr_text:
        return []

    style = runtime.xml_primitives.STYLE
    make_multi_run_para = runtime.xml_primitives._make_multi_run_para
    paragraphs: list[str] = []
    for index, line in enumerate(_split_nonempty_lines(ocr_text)):
        runs = _build_problem_line_runs(runtime, id_generator, region.context.order, line, index, style)
        paragraphs.append(make_multi_run_para(id_generator, runs, para_pr=style["PARA_BODY"]))
    return paragraphs


def _build_problem_line_runs(
    runtime: HwpxRuntime,
    id_generator,
    order: int,
    line: str,
    index: int,
    style: dict[str, int],
) -> list[str]:
    """문제 한 줄을 번호와 수식 혼합 run 목록으로 만든다."""
    runs: list[str] = []
    if index == 0:
        runs.append(f'<hp:run charPrIDRef="{style["CHAR_EXAM_NUM"]}"><hp:t>{order}. </hp:t></hp:run>')
    runs.extend(_parse_math_text_to_runs(runtime, id_generator, line, style["CHAR_BODY"]))
    return runs


def _build_explanation_paragraphs(runtime: HwpxRuntime, region: RegionPipelineContext, id_generator) -> list[str]:
    """해설 텍스트가 있으면 제목과 본문 문단을 생성한다."""
    explanation = (region.extractor.explanation or "").strip()
    if not explanation:
        return []

    style = runtime.xml_primitives.STYLE
    make_empty_para = runtime.xml_primitives.make_empty_para
    make_multi_run_para = runtime.xml_primitives._make_multi_run_para
    make_text_para = runtime.xml_primitives.make_text_para
    paragraphs = [
        make_empty_para(id_generator),
        make_text_para(id_generator, "[해설]", para_pr=style["PARA_CHOICE"], char_pr=style["CHAR_SUBTITLE"]),
    ]
    for line in _split_nonempty_lines(explanation):
        runs = _parse_math_text_to_runs(runtime, id_generator, line, style["CHAR_CHOICE"])
        paragraphs.append(make_multi_run_para(id_generator, runs, para_pr=style["PARA_CHOICE"]))
    return paragraphs


def _build_region_separator(runtime: HwpxRuntime, id_generator) -> list[str]:
    """문제 사이의 공백과 구분선을 만든다."""
    style = runtime.xml_primitives.STYLE
    make_empty_para = runtime.xml_primitives.make_empty_para
    return [
        make_empty_para(id_generator),
        make_empty_para(id_generator, para_pr=style["PARA_HR"], char_pr=0),
        make_empty_para(id_generator),
    ]


def _wrap_section_xml(paragraphs: list[str], section_namespaces: str) -> str:
    """문단 목록을 section0.xml 전체 문서 문자열로 감싼다."""
    body_xml = "\n".join(paragraphs)
    return f"<?xml version='1.0' encoding='UTF-8'?>\n<hs:sec {section_namespaces}>\n  {body_xml}\n</hs:sec>"


def _split_nonempty_lines(text: str) -> list[str]:
    """빈 줄을 제거한 텍스트 줄 목록을 반환한다."""
    return [line for line in text.split("\n") if line.strip()]


def _inject_images_to_manifest(content_hpf: Path, images_info: list[dict[str, str]]) -> None:
    """content.hpf manifest에 BinData 이미지를 추가한다."""
    ET.register_namespace("opf", "http://www.idpf.org/2007/opf/")
    tree = ET.parse(str(content_hpf))
    root = tree.getroot()
    namespace = {"opf": "http://www.idpf.org/2007/opf/"}
    manifest = root.find(".//opf:manifest", namespace)

    if manifest is not None:
        for image in images_info:
            item = ET.SubElement(manifest, "{http://www.idpf.org/2007/opf/}item")
            item.set("id", image["id"])
            item.set("href", f"Contents/BinData/{image['filename']}")
            item.set("media-type", f"image/{image['ext']}")
            item.set("isEmbeded", "1")

    with open(str(content_hpf), "wb") as file:
        tree.write(file, encoding="UTF-8", xml_declaration=True)


def _update_header_xml(header_xml_path: Path, images_info: list[dict[str, str]]) -> None:
    """header.xml의 binDataList에 이미지 참조를 추가한다."""
    ET.register_namespace("hh", "http://www.hancom.co.kr/hwpml/2011/head")
    tree = ET.parse(str(header_xml_path))
    root = tree.getroot()
    namespace = {"hh": "http://www.hancom.co.kr/hwpml/2011/head"}
    bindata_list = root.find(".//hh:binDataList", namespace)

    if bindata_list is None:
        bindata_list = _create_bindata_list(root, namespace)
        if bindata_list is None:
            return

    current_count = int(bindata_list.get("itemCnt", "0"))
    bindata_list.set("itemCnt", str(current_count + len(images_info)))
    for image in images_info:
        _append_bindata_item(bindata_list, image)

    with open(str(header_xml_path), "wb") as file:
        tree.write(file, encoding="UTF-8", xml_declaration=True)


def _create_bindata_list(root: ET.Element, namespace: dict[str, str]) -> ET.Element | None:
    """header.xml에 binDataList가 없을 때 refList 아래에 새로 만든다."""
    ref_list = root.find(".//hh:refList", namespace)
    if ref_list is None:
        return None
    bindata_list = ET.SubElement(ref_list, "{http://www.hancom.co.kr/hwpml/2011/head}binDataList")
    bindata_list.set("itemCnt", "0")
    return bindata_list


def _append_bindata_item(bindata_list: ET.Element, image: dict[str, str]) -> None:
    """binDataList에 이미지 하나를 추가한다."""
    item = ET.SubElement(bindata_list, "{http://www.hancom.co.kr/hwpml/2011/head}binData")
    item.set("id", image["id"])
    item.set("extension", image["ext"])
    item.set("type", "BINA")
    item.set("format", image["ext"].upper())
