from __future__ import annotations

import importlib
import os
import re
import shutil
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from app.config import get_settings
from app.pipeline.schema import JobPipelineContext

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SKILL_NAME = "hwpxskill-math"
REQUIRED_RUNTIME_FILES = (
    Path("scripts/xml_primitives.py"),
    Path("scripts/exam_helpers.py"),
    Path("scripts/hwpx_utils.py"),
    Path("templates/base/Contents/header.xml"),
    Path("templates/base/Contents/content.hpf"),
    Path("templates/base/Contents/section0.xml"),
    Path("templates/base/mimetype"),
)
RUNTIME_MODULE_NAMES = ("xml_primitives", "exam_helpers", "hwpx_utils")


@dataclass(frozen=True)
class HwpxRuntimePaths:
    """HWPX export 런타임에서 필요한 경로 묶음을 보관한다."""

    skill_dir: Path
    scripts_dir: Path
    template_dir: Path


@dataclass(frozen=True)
class HwpxRuntimeModules:
    """lazy import로 불러온 HWPX helper 심볼을 묶어 전달한다."""

    IDGen: Any
    STYLE: dict[str, int]
    SEC_NAMESPACES: str
    make_empty_para: Any
    make_text_para: Any
    make_picture_para: Any
    make_secpr_para: Any
    make_multi_run_para: Any
    make_equation_run: Any
    update_metadata: Any
    pack_hwpx: Any
    validate_hwpx: Any


def _get_codex_home() -> Path | None:
    """CODEX_HOME 환경변수를 Path 객체로 정규화한다."""
    raw_value = os.getenv("CODEX_HOME")
    if raw_value is None or not raw_value.strip():
        return None
    return Path(raw_value).expanduser()


def _get_home_dir() -> Path:
    """현재 사용자 홈 디렉터리를 반환한다."""
    return Path.home()


def _iter_runtime_candidates(
    app_root: Path,
    configured_skill_dir: str | None,
    codex_home: Path | None,
    home_dir: Path,
) -> list[Path]:
    """설정 우선순위에 맞는 HWPX 런타임 후보 경로를 만든다."""
    candidates: list[Path] = []
    if configured_skill_dir:
        candidates.append(Path(configured_skill_dir).expanduser())

    candidates.append(app_root / "vendor" / RUNTIME_SKILL_NAME)
    if codex_home is not None:
        candidates.append(codex_home / "skills" / RUNTIME_SKILL_NAME)
    candidates.append(home_dir / ".codex" / "skills" / RUNTIME_SKILL_NAME)

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def _collect_missing_runtime_files(skill_dir: Path) -> list[str]:
    """필수 runtime 파일 중 누락된 상대 경로 목록을 반환한다."""
    missing_files: list[str] = []
    for relative_path in REQUIRED_RUNTIME_FILES:
        if not (skill_dir / relative_path).exists():
            missing_files.append(relative_path.as_posix())
    return missing_files


def _resolve_hwpx_runtime(
    app_root: Path = ROOT,
    configured_skill_dir: str | None = None,
    codex_home: Path | None = None,
    home_dir: Path | None = None,
) -> HwpxRuntimePaths:
    """사용 가능한 HWPX export 런타임 경로를 찾고 상세 실패 정보를 만든다."""
    resolved_codex_home = codex_home if codex_home is not None else _get_codex_home()
    resolved_home_dir = home_dir if home_dir is not None else _get_home_dir()
    candidates = _iter_runtime_candidates(
        app_root=app_root,
        configured_skill_dir=configured_skill_dir,
        codex_home=resolved_codex_home,
        home_dir=resolved_home_dir,
    )

    checked_paths: list[str] = []
    missing_details: list[str] = []
    for candidate in candidates:
        checked_paths.append(str(candidate))
        missing_files = _collect_missing_runtime_files(candidate)
        if not missing_files:
            return HwpxRuntimePaths(
                skill_dir=candidate,
                scripts_dir=candidate / "scripts",
                template_dir=candidate / "templates" / "base",
            )
        missing_details.append(f"{candidate} -> {', '.join(missing_files)}")

    checked_text = "; ".join(checked_paths) if checked_paths else "<none>"
    missing_text = "; ".join(missing_details) if missing_details else "<none>"
    raise FileNotFoundError(
        f"HWPX export runtime not found. checked: {checked_text} missing: {missing_text}"
    )


def _load_hwpx_runtime_modules(scripts_dir: Path) -> HwpxRuntimeModules:
    """scripts 디렉터리에서 필요한 helper 모듈을 임시로 불러온다."""
    previous_modules = {name: sys.modules.get(name) for name in RUNTIME_MODULE_NAMES}
    scripts_dir_str = str(scripts_dir)
    sys.path.insert(0, scripts_dir_str)

    try:
        for module_name in RUNTIME_MODULE_NAMES:
            sys.modules.pop(module_name, None)

        xml_primitives = importlib.import_module("xml_primitives")
        exam_helpers = importlib.import_module("exam_helpers")
        hwpx_utils = importlib.import_module("hwpx_utils")
    except Exception as error:
        raise RuntimeError(
            f"Failed to load HWPX export runtime from {scripts_dir}: {error}"
        ) from error
    finally:
        try:
            sys.path.remove(scripts_dir_str)
        except ValueError:
            pass

        for module_name in RUNTIME_MODULE_NAMES:
            sys.modules.pop(module_name, None)
        for module_name, module in previous_modules.items():
            if module is not None:
                sys.modules[module_name] = module

    return HwpxRuntimeModules(
        IDGen=xml_primitives.IDGen,
        STYLE=xml_primitives.STYLE,
        SEC_NAMESPACES=xml_primitives.SEC_NAMESPACES,
        make_empty_para=xml_primitives.make_empty_para,
        make_text_para=xml_primitives.make_text_para,
        make_picture_para=exam_helpers.make_picture_para,
        make_secpr_para=exam_helpers.make_secpr_para,
        make_multi_run_para=xml_primitives._make_multi_run_para,
        make_equation_run=xml_primitives._make_equation_run,
        update_metadata=hwpx_utils.update_metadata,
        pack_hwpx=hwpx_utils.pack_hwpx,
        validate_hwpx=hwpx_utils.validate_hwpx,
    )


def export_hwpx(root_path: Path, job: JobPipelineContext, export_dir: Path) -> Path:
    """OCR 결과를 HWPX 파일로 조립하고 구조 검증까지 수행한다."""
    runtime_paths = _resolve_hwpx_runtime(
        app_root=ROOT,
        configured_skill_dir=get_settings(ROOT).hwpx_skill_dir,
    )
    runtime_modules = _load_hwpx_runtime_modules(runtime_paths.scripts_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    hwpx_path = export_dir / f"{job.job_id}.hwpx"

    with tempfile.TemporaryDirectory() as tmpdir_str:
        work_dir = Path(tmpdir_str) / "build"
        shutil.copytree(runtime_paths.template_dir, work_dir)

        section_path = work_dir / "Contents" / "section0.xml"
        bindata_dir = work_dir / "Contents" / "BinData"
        bindata_dir.mkdir(parents=True, exist_ok=True)

        images_info = _generate_section0_xml(
            root_path=root_path,
            job=job,
            output_path=section_path,
            bindata_tgt_dir=bindata_dir,
            runtime=runtime_modules,
        )

        content_hpf = work_dir / "Contents" / "content.hpf"
        runtime_modules.update_metadata(content_hpf, f"MathOCR_{job.job_id}", "MathOCR")
        _inject_images_to_manifest(content_hpf, images_info)

        header_xml_path = work_dir / "Contents" / "header.xml"
        _update_header_xml(header_xml_path, images_info)
        runtime_modules.pack_hwpx(work_dir, hwpx_path)

    errors = runtime_modules.validate_hwpx(hwpx_path)
    if errors:
        raise ValueError(f"HWPX Validation failed: {errors}")

    return hwpx_path


def _parse_math_text_to_runs(
    idgen: Any,
    text: str,
    default_char_pr: int,
    runtime: HwpxRuntimeModules,
    base_unit: int = 1000,
) -> list[str]:
    """텍스트를 <math> 태그 기준으로 분리해 HWPX run 목록으로 변환한다."""
    runs: list[str] = []
    if not text:
        return runs

    parts = re.split(r"(<math>.*?</math>)", text, flags=re.DOTALL)
    for part in parts:
        if not part:
            continue
        if part.startswith("<math>") and part.endswith("</math>"):
            math_script = part[6:-7].strip()
            runs.append(runtime.make_equation_run(idgen, math_script, default_char_pr, base_unit))
            continue

        safe_part = escape(part)
        runs.append(f'<hp:run charPrIDRef="{default_char_pr}"><hp:t>{safe_part}</hp:t></hp:run>')
    return runs


def _generate_section0_xml(
    root_path: Path,
    job: JobPipelineContext,
    output_path: Path,
    bindata_tgt_dir: Path,
    runtime: HwpxRuntimeModules,
) -> list[dict[str, str]]:
    """region 목록을 순회하며 section0.xml과 BinData 정보를 생성한다."""
    images_info: list[dict[str, str]] = []
    idgen = runtime.IDGen()
    paras: list[str] = []

    paras.append(runtime.make_secpr_para(idgen, col_count=2, same_gap=2268))

    title_runs = [
        (
            f'<hp:run charPrIDRef="{runtime.STYLE["CHAR_EXAM_TITLE"]}">'
            f"<hp:t>수학 분석 ({job.job_id})</hp:t></hp:run>"
        )
    ]
    paras.append(runtime.make_multi_run_para(idgen, title_runs, para_pr=runtime.STYLE["PARA_EXAM_TITLE"]))
    paras.append(runtime.make_empty_para(idgen, para_pr=runtime.STYLE["PARA_HR"], char_pr=0))
    paras.append(runtime.make_empty_para(idgen))

    for region in sorted(job.regions, key=lambda candidate: candidate.context.order):
        order = region.context.order
        region_id = region.context.id
        image_url = region.figure.png_rendered_url or region.figure.crop_url

        if image_url:
            source_image = root_path / image_url
            if source_image.exists():
                extension = source_image.suffix[1:].lower() or "png"
                unique_suffix = uuid.uuid4().hex
                bindata_filename = f"img_{region_id}_{unique_suffix}.{extension}"
                destination_image = bindata_tgt_dir / bindata_filename
                shutil.copy2(source_image, destination_image)

                bindata_id = f"BIN_{region_id}_{unique_suffix}"
                images_info.append(
                    {"id": bindata_id, "filename": bindata_filename, "ext": extension}
                )
                paras.append(
                    runtime.make_picture_para(
                        idgen,
                        bindata_id,
                        width_hu=25000,
                        height_hu=15000,
                        para_pr=runtime.STYLE["PARA_EQ"],
                        char_pr=0,
                    )
                )
                paras.append(runtime.make_empty_para(idgen))

        ocr_text = (region.extractor.ocr_text or "").strip()
        if ocr_text:
            lines = [line for line in ocr_text.split("\n") if line.strip()]
            for index, line in enumerate(lines):
                runs: list[str] = []
                if index == 0:
                    runs.append(
                        f'<hp:run charPrIDRef="{runtime.STYLE["CHAR_EXAM_NUM"]}"><hp:t>{order}. </hp:t></hp:run>'
                    )
                runs.extend(
                    _parse_math_text_to_runs(idgen, line, runtime.STYLE["CHAR_BODY"], runtime)
                )
                paras.append(
                    runtime.make_multi_run_para(idgen, runs, para_pr=runtime.STYLE["PARA_BODY"])
                )

        explanation = (region.extractor.explanation or "").strip()
        if explanation:
            paras.append(runtime.make_empty_para(idgen))
            paras.append(
                runtime.make_text_para(
                    idgen,
                    "[해설]",
                    para_pr=runtime.STYLE["PARA_CHOICE"],
                    char_pr=runtime.STYLE["CHAR_SUBTITLE"],
                )
            )

            lines = [line for line in explanation.split("\n") if line.strip()]
            for line in lines:
                runs = _parse_math_text_to_runs(
                    idgen,
                    line,
                    runtime.STYLE["CHAR_CHOICE"],
                    runtime,
                )
                paras.append(
                    runtime.make_multi_run_para(
                        idgen,
                        runs,
                        para_pr=runtime.STYLE["PARA_CHOICE"],
                    )
                )

        paras.append(runtime.make_empty_para(idgen))
        paras.append(runtime.make_empty_para(idgen, para_pr=runtime.STYLE["PARA_HR"], char_pr=0))
        paras.append(runtime.make_empty_para(idgen))

    body_xml = "\n".join(paras)
    xml_content = (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        f"<hs:sec {runtime.SEC_NAMESPACES}>\n  {body_xml}\n</hs:sec>"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_content, encoding="utf-8")
    return images_info


def _inject_images_to_manifest(content_hpf: Path, images_info: list) -> None:
    """content.hpf manifest에 BinData 이미지를 추가한다."""
    ET.register_namespace("opf", "http://www.idpf.org/2007/opf/")
    tree = ET.parse(str(content_hpf))
    root = tree.getroot()
    ns = {"opf": "http://www.idpf.org/2007/opf/"}

    manifest_el = root.find(".//opf:manifest", ns)
    if manifest_el is not None:
        for img in images_info:
            item = ET.SubElement(manifest_el, "{http://www.idpf.org/2007/opf/}item")
            item.set("id", img["id"])
            item.set("href", f"Contents/BinData/{img['filename']}")
            item.set("media-type", f"image/{img['ext']}")
            item.set("isEmbeded", "1")

    with open(str(content_hpf), "wb") as f:
        tree.write(f, encoding="UTF-8", xml_declaration=True)


def _update_header_xml(header_xml_path: Path, images_info: list) -> None:
    """header.xml의 binDataList를 실제 이미지 개수에 맞게 갱신한다."""
    ET.register_namespace("hh", "http://www.hancom.co.kr/hwpml/2011/head")
    tree = ET.parse(str(header_xml_path))
    root = tree.getroot()
    ns = {"hh": "http://www.hancom.co.kr/hwpml/2011/head"}
    
    bindata_list = root.find(".//hh:binDataList", ns)
    if bindata_list is None:
        reflist = root.find(".//hh:refList", ns)
        if reflist is not None:
            bindata_list = ET.SubElement(reflist, "{http://www.hancom.co.kr/hwpml/2011/head}binDataList")
            bindata_list.set("itemCnt", "0")
        else:
            return

    current_cnt = int(bindata_list.get("itemCnt", "0"))
    bindata_list.set("itemCnt", str(current_cnt + len(images_info)))

    for img in images_info:
        item = ET.SubElement(bindata_list, "{http://www.hancom.co.kr/hwpml/2011/head}binData")
        item.set("id", img["id"])
        item.set("extension", img["ext"])
        item.set("type", "BINA")
        item.set("format", img["ext"].upper())

    with open(str(header_xml_path), "wb") as f:
        tree.write(f, encoding="UTF-8", xml_declaration=True)
