from __future__ import annotations

import importlib
import logging
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.pipeline.hwpx_reference_renderer import render_section_from_reference
from app.pipeline.schema import JobPipelineContext

ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)
TEMPLATE_ERROR_MESSAGE = "문서 템플릿을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
RUNTIME_SKILL_NAME = "hwpxskill-math"
KOREA_TZ = ZoneInfo("Asia/Seoul")
RUNTIME_MODULE_NAMES = ("xml_primitives", "exam_helpers", "hwpx_utils")
HWPX_NS = {
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "opf": "http://www.idpf.org/2007/opf/",
}
REQUIRED_RUNTIME_FILES = (
    Path("scripts/xml_primitives.py"),
    Path("scripts/exam_helpers.py"),
    Path("scripts/hwpx_utils.py"),
    Path("templates/base/mimetype"),
    Path("templates/base/BinData/image1.bmp"),
    Path("templates/base/Contents/header.xml"),
    Path("templates/base/Contents/content.hpf"),
    Path("templates/base/Contents/masterpage0.xml"),
    Path("templates/base/Contents/masterpage1.xml"),
    Path("templates/base/Contents/section0.xml"),
)


@dataclass(frozen=True)
class HwpxRuntimePaths:
    """HWPX runtime 경로 묶음을 보관한다."""

    skill_dir: Path
    scripts_dir: Path
    template_dir: Path


@dataclass(frozen=True)
class HwpxRuntimeModules:
    """runtime helper 모듈의 필요한 심볼만 묶는다."""

    IDGen: Any
    update_metadata: Any
    pack_hwpx: Any
    validate_hwpx: Any


@dataclass(frozen=True)
class TemplateRenderContext:
    """템플릿 렌더링에 필요한 고정 값을 보관한다."""

    year: str


@dataclass
class QualityWarningCollector:
    """비치명 템플릿 경고를 수집해 구조화 로그로 남긴다."""

    warnings: list[tuple[str, str]] = field(default_factory=list)

    def add(self, code: str, detail: str) -> None:
        """경고 코드를 세부 정보와 함께 누적한다."""
        self.warnings.append((code, detail))

    def emit(self) -> None:
        """누적 경고를 logger로 출력한다."""
        for code, detail in self.warnings:
            LOGGER.warning("hwpx_template_warning code=%s detail=%s", code, detail)


def _get_codex_home() -> Path | None:
    """CODEX_HOME을 Path로 정규화한다."""
    raw_value = os.getenv("CODEX_HOME")
    if raw_value is None or not raw_value.strip():
        return None
    return Path(raw_value).expanduser()


def _get_home_dir() -> Path:
    """현재 사용자 홈 디렉터리를 반환한다."""
    return Path.home()


def _build_render_context() -> TemplateRenderContext:
    """문서 생성 시점의 연도를 렌더 컨텍스트로 만든다."""
    return TemplateRenderContext(year=str(datetime.now(KOREA_TZ).year))


def _iter_runtime_candidates(
    app_root: Path,
    configured_skill_dir: str | None,
    codex_home: Path | None,
    home_dir: Path,
) -> list[Path]:
    """설정 우선순위대로 runtime 후보 경로를 만든다."""
    candidates: list[Path] = []
    if configured_skill_dir:
        candidates.append(Path(configured_skill_dir).expanduser())
    candidates.append(app_root / "vendor" / RUNTIME_SKILL_NAME)
    if codex_home is not None:
        candidates.append(codex_home / "skills" / RUNTIME_SKILL_NAME)
    candidates.append(home_dir / ".codex" / "skills" / RUNTIME_SKILL_NAME)
    return list(dict.fromkeys(candidates))


def _collect_missing_runtime_files(skill_dir: Path) -> list[str]:
    """필수 runtime 파일 중 누락된 상대 경로를 반환한다."""
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
    """사용 가능한 HWPX runtime 경로를 찾는다."""
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
    """runtime scripts 디렉터리에서 필요한 helper만 로드한다."""
    previous_modules = {name: sys.modules.get(name) for name in RUNTIME_MODULE_NAMES}
    scripts_dir_str = str(scripts_dir)
    sys.path.insert(0, scripts_dir_str)
    try:
        for module_name in RUNTIME_MODULE_NAMES:
            sys.modules.pop(module_name, None)
        xml_primitives = importlib.import_module("xml_primitives")
        hwpx_utils = importlib.import_module("hwpx_utils")
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
        update_metadata=hwpx_utils.update_metadata,
        pack_hwpx=hwpx_utils.pack_hwpx,
        validate_hwpx=hwpx_utils.validate_hwpx,
    )


def export_hwpx(root_path: Path, job: JobPipelineContext, export_dir: Path) -> Path:
    """OCR 결과를 기준 템플릿에 주입해 HWPX 파일을 생성한다."""
    context = _build_render_context()
    warnings = QualityWarningCollector()
    try:
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
            header_xml_path = work_dir / "Contents" / "header.xml"
            content_hpf = work_dir / "Contents" / "content.hpf"
            bindata_dir = work_dir / "BinData"
            bindata_dir.mkdir(parents=True, exist_ok=True)
            images_info = render_section_from_reference(
                section_path=section_path,
                root_path=root_path,
                job=job,
                bindata_dir=bindata_dir,
                runtime=runtime_modules,
                context=context,
                warnings=warnings,
            )
            runtime_modules.update_metadata(content_hpf, f"{context.year}학년도 수학시험 문제지", "MathOCR")
            _inject_images_to_manifest(content_hpf, images_info)
            _update_header_xml(header_xml_path, images_info, warnings)
            _normalize_masterpage_footer(work_dir / "Contents" / "masterpage0.xml")
            _normalize_masterpage_footer(work_dir / "Contents" / "masterpage1.xml")
            _validate_template_contract(work_dir, content_hpf, header_xml_path, section_path)
            runtime_modules.pack_hwpx(work_dir, hwpx_path)
        errors = runtime_modules.validate_hwpx(hwpx_path)
        if errors:
            raise ValueError(f"hwpx validation failed: {errors}")
    except Exception as error:
        warnings.emit()
        LOGGER.exception("hwpx export failed: %s", error)
        raise ValueError(TEMPLATE_ERROR_MESSAGE) from error
    warnings.emit()
    return hwpx_path


def _resolve_media_type(extension: str) -> str:
    """확장자에 맞는 media-type을 계산한다."""
    if extension in {"jpg", "jpeg"}:
        return "image/jpeg"
    return f"image/{extension}"


def _inject_images_to_manifest(content_hpf: Path, images_info: list[dict[str, str]]) -> None:
    """content.hpf manifest에 추가 BinData 이미지를 등록한다."""
    if not images_info:
        return
    ET.register_namespace("opf", HWPX_NS["opf"])
    tree = ET.parse(str(content_hpf))
    root = tree.getroot()
    manifest_el = root.find(".//opf:manifest", HWPX_NS)
    if manifest_el is None:
        raise ValueError("content manifest missing")
    for img in images_info:
        item = ET.SubElement(manifest_el, "{http://www.idpf.org/2007/opf/}item")
        item.set("id", img["id"])
        item.set("href", f"BinData/{img['filename']}")
        item.set("media-type", _resolve_media_type(img["ext"]))
        item.set("isEmbeded", "1")
    tree.write(str(content_hpf), encoding="UTF-8", xml_declaration=True)


def _update_header_xml(
    header_xml_path: Path,
    images_info: list[dict[str, str]],
    warnings: QualityWarningCollector,
) -> None:
    """header.xml의 binDataList를 실제 이미지 개수에 맞게 갱신한다."""
    if not images_info:
        return
    ET.register_namespace("hh", HWPX_NS["hh"])
    tree = ET.parse(str(header_xml_path))
    root = tree.getroot()
    bindata_list = root.find(".//hh:binDataList", HWPX_NS)
    if bindata_list is None:
        ref_list = root.find(".//hh:refList", HWPX_NS)
        if ref_list is None:
            raise ValueError("header refList missing")
        bindata_list = ET.SubElement(ref_list, "{http://www.hancom.co.kr/hwpml/2011/head}binDataList")
        bindata_list.set("itemCnt", "0")
        warnings.add("created_bindata_list", str(header_xml_path))
    current_cnt = len(bindata_list.findall("hh:binData", HWPX_NS))
    bindata_list.set("itemCnt", str(current_cnt + len(images_info)))
    for img in images_info:
        item = ET.SubElement(bindata_list, "{http://www.hancom.co.kr/hwpml/2011/head}binData")
        item.set("id", img["id"])
        item.set("extension", img["ext"])
        item.set("type", "BINA")
        item.set("format", img["ext"].upper())
    tree.write(str(header_xml_path), encoding="UTF-8", xml_declaration=True)


def _normalize_masterpage_footer(masterpage_path: Path) -> None:
    """footer 가운데 셀의 총페이지 정적 문단을 제거한다."""
    tree = ET.parse(str(masterpage_path))
    root = tree.getroot()
    for cell in root.findall(".//hp:tc", HWPX_NS):
        if cell.find(".//hp:autoNum[@numType='PAGE']", HWPX_NS) is None:
            continue
        for sub_list in cell.findall(".//hp:subList", HWPX_NS):
            for paragraph in list(sub_list.findall("hp:p", HWPX_NS)):
                texts = "".join(node.text or "" for node in paragraph.findall(".//hp:t", HWPX_NS)).strip()
                if texts.isdigit():
                    sub_list.remove(paragraph)
    tree.write(str(masterpage_path), encoding="UTF-8", xml_declaration=True)


def _validate_template_contract(
    work_dir: Path,
    content_hpf: Path,
    header_xml_path: Path,
    section_path: Path,
) -> None:
    """manifest/masterpage/style 정합성을 한 번에 검증한다."""
    _validate_required_manifest_entries(work_dir, content_hpf)
    _validate_masterpage_contract(work_dir, section_path)
    _validate_style_references(
        header_xml_path,
        [
            section_path,
            work_dir / "Contents" / "masterpage0.xml",
            work_dir / "Contents" / "masterpage1.xml",
        ],
    )


def _validate_required_manifest_entries(work_dir: Path, content_hpf: Path) -> None:
    """manifest 필수 항목과 실제 파일 존재를 함께 검증한다."""
    required_hrefs = {
        "Contents/header.xml",
        "Contents/masterpage0.xml",
        "Contents/masterpage1.xml",
        "Contents/section0.xml",
        "settings.xml",
    }
    tree = ET.parse(str(content_hpf))
    hrefs = {item.get("href", "") for item in tree.findall(".//opf:item", HWPX_NS)}
    missing_hrefs = sorted(required_hrefs - hrefs)
    if missing_hrefs:
        raise ValueError(f"manifest missing required entries: {missing_hrefs}")
    missing_files = sorted(href for href in hrefs if href and not (work_dir / href).exists())
    if missing_files:
        raise ValueError(f"manifest references missing files: {missing_files}")


def _validate_masterpage_contract(work_dir: Path, section_path: Path) -> None:
    """section0.xml의 masterpage 연결과 개수를 검증한다."""
    root = ET.parse(str(section_path)).getroot()
    sec_pr = root.find(".//hp:secPr", HWPX_NS)
    if sec_pr is None:
        raise ValueError("section secPr missing")
    master_pages = [node.get("idRef", "") for node in sec_pr.findall("hp:masterPage", HWPX_NS)]
    if master_pages != ["masterpage0", "masterpage1"]:
        raise ValueError(f"unexpected masterpage refs: {master_pages}")
    if sec_pr.get("masterPageCnt") != str(len(master_pages)):
        raise ValueError("masterpage count mismatch")
    for masterpage in master_pages:
        if not (work_dir / "Contents" / f"{masterpage}.xml").exists():
            raise ValueError(f"missing masterpage file: {masterpage}")


def _collect_xml_style_refs(xml_path: Path) -> tuple[set[str], set[str]]:
    """XML 문서 하나에서 paraPr/charPr 참조 ID를 수집한다."""
    root = ET.parse(str(xml_path)).getroot()
    para_refs = {
        node.get("paraPrIDRef", "")
        for node in root.findall(".//hp:p", HWPX_NS)
        if node.get("paraPrIDRef")
    }
    char_refs = {
        node.get("charPrIDRef", "")
        for node in root.findall(".//hp:run", HWPX_NS)
        if node.get("charPrIDRef")
    }
    return para_refs, char_refs


def _validate_style_references(header_xml_path: Path, xml_paths: list[Path]) -> None:
    """section/masterpage가 header 정의 안의 style ref만 쓰는지 확인한다."""
    header_root = ET.parse(str(header_xml_path)).getroot()
    valid_para_ids = {
        node.get("id", "")
        for node in header_root.findall(".//hh:paraPr", HWPX_NS)
        if node.get("id")
    }
    valid_char_ids = {
        node.get("id", "")
        for node in header_root.findall(".//hh:charPr", HWPX_NS)
        if node.get("id")
    }
    used_para_ids: set[str] = set()
    used_char_ids: set[str] = set()
    for xml_path in xml_paths:
        para_refs, char_refs = _collect_xml_style_refs(xml_path)
        used_para_ids.update(para_refs)
        used_char_ids.update(char_refs)
    if not used_para_ids <= valid_para_ids:
        raise ValueError(f"style reference mismatch: para={sorted(used_para_ids - valid_para_ids)}")
    if not used_char_ids <= valid_char_ids:
        raise ValueError(f"style reference mismatch: char={sorted(used_char_ids - valid_char_ids)}")
