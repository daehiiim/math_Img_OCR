from __future__ import annotations

import importlib
import logging
import os
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile
from zoneinfo import ZoneInfo

from lxml import etree

from app.config import get_settings
from app.pipeline.hwpforge_roundtrip import (
    HwpForgeRoundtripError,
    build_section_via_hwpforge,
    inspect_and_validate_hwpx_via_hwpforge,
    roundtrip_section_via_hwpforge,
)
from app.pipeline.hwpx_math_layout import repair_equation_widths
from app.pipeline.hwpx_reference_renderer import render_section_from_reference
from app.pipeline.schema import JobPipelineContext

ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)
TEMPLATE_ERROR_MESSAGE = "문서 템플릿을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
RUNTIME_SKILL_NAME = "hwpxskill-math"
CANONICAL_TEMPLATE_NAME = "style_guide.hwpx"
KOREA_TZ = ZoneInfo("Asia/Seoul")
RUNTIME_MODULE_NAMES = ("xml_primitives", "exam_helpers", "hwpx_utils")
TEMPLATE_RUNTIME_MISSING_CODE = "HWPX_TEMPLATE_RUNTIME_MISSING"
TEMPLATE_CANONICAL_MISSING_CODE = "HWPX_TEMPLATE_CANONICAL_MISSING"
TEMPLATE_MANIFEST_MISSING_CODE = "HWPX_TEMPLATE_MANIFEST_MISSING"
TEMPLATE_MASTERPAGE_MISSING_CODE = "HWPX_TEMPLATE_MASTERPAGE_MISSING"
TEMPLATE_STYLE_REF_MISMATCH_CODE = "HWPX_TEMPLATE_STYLE_REF_MISMATCH"
TEMPLATE_CANONICAL_CORRUPTED_CODE = "HWPX_TEMPLATE_CANONICAL_CORRUPTED"
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
REQUIRED_CANONICAL_ARCHIVE_FILES = (
    "mimetype",
    "settings.xml",
    "version.xml",
    "BinData/image1.bmp",
    "Contents/header.xml",
    "Contents/content.hpf",
    "Contents/masterpage0.xml",
    "Contents/masterpage1.xml",
    "Contents/section0.xml",
    "META-INF/container.rdf",
    "META-INF/container.xml",
    "META-INF/manifest.xml",
    "Preview/PrvImage.png",
    "Preview/PrvText.txt",
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


class HwpxTemplateError(Exception):
    """예측 가능한 HWPX 템플릿 오류 코드를 함께 보관한다."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


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
    raise HwpxTemplateError(
        TEMPLATE_RUNTIME_MISSING_CODE,
        f"HWPX export runtime not found. checked: {checked_text} missing: {missing_text}",
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


def _resolve_canonical_template_path(app_root: Path = ROOT) -> Path:
    """로컬 저장소와 컨테이너 번들을 모두 고려해 canonical template를 찾는다."""
    candidates = [
        app_root.parent / "templates" / CANONICAL_TEMPLATE_NAME,
        app_root / "templates" / CANONICAL_TEMPLATE_NAME,
    ]
    for canonical_path in dict.fromkeys(candidates):
        if canonical_path.exists():
            return canonical_path
    raise HwpxTemplateError(
        TEMPLATE_CANONICAL_MISSING_CODE,
        "canonical template missing: " + "; ".join(str(path) for path in candidates),
    )


def _extract_canonical_template(canonical_path: Path, work_dir: Path) -> None:
    """style guide HWPX 전체를 작업 디렉터리로 그대로 풀어 쓴다."""
    try:
        with ZipFile(canonical_path, "r") as archive:
            names = set(archive.namelist())
            missing_files = sorted(set(REQUIRED_CANONICAL_ARCHIVE_FILES) - names)
            if missing_files:
                error_code = (
                    TEMPLATE_MASTERPAGE_MISSING_CODE
                    if any("masterpage" in path for path in missing_files)
                    else TEMPLATE_MANIFEST_MISSING_CODE
                )
                raise HwpxTemplateError(
                    error_code,
                    f"canonical bundle missing entries: {missing_files}",
                )
            for archive_info in archive.infolist():
                if archive_info.is_dir():
                    continue
                target_path = work_dir / archive_info.filename
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(archive.read(archive_info.filename))
    except HwpxTemplateError:
        raise
    except BadZipFile as error:
        raise HwpxTemplateError(
            TEMPLATE_CANONICAL_CORRUPTED_CODE,
            f"canonical bundle is corrupted: {canonical_path}",
        ) from error


def export_hwpx(root_path: Path, job: JobPipelineContext, export_dir: Path) -> Path:
    """OCR 결과를 기준 템플릿에 주입해 HWPX 파일을 생성한다."""
    context = _build_render_context()
    warnings = QualityWarningCollector()
    try:
        settings = get_settings(ROOT)
        runtime_paths = _resolve_hwpx_runtime(app_root=ROOT, configured_skill_dir=settings.hwpx_skill_dir)
        canonical_template_path = _resolve_canonical_template_path(ROOT)
        runtime_modules = _load_hwpx_runtime_modules(runtime_paths.scripts_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        hwpx_path = export_dir / f"{job.job_id}.hwpx"
        used_hwpforge = False
        export_engine = getattr(settings, "hwpx_export_engine", "auto")
        configured_runtime_path = getattr(settings, "hwpforge_mcp_path", None)
        with tempfile.TemporaryDirectory() as tmpdir_str:
            work_dir: Path | None = None
            if export_engine != "legacy":
                direct_work_dir = Path(tmpdir_str) / "build-direct"
                try:
                    _prepare_direct_hwpforge_bundle(
                        root_path=root_path,
                        job=job,
                        work_dir=direct_work_dir,
                        runtime_modules=runtime_modules,
                        context=context,
                        canonical_template_path=canonical_template_path,
                        configured_runtime_path=configured_runtime_path,
                        warnings=warnings,
                    )
                    work_dir = direct_work_dir
                    used_hwpforge = True
                except Exception as error:
                    if export_engine == "hwpforge":
                        raise
                    warnings.add(
                        getattr(error, "code", "HWPFORGE_SECTION_BUILD_FAILED"),
                        f"fallback=legacy detail={error}",
                    )
            if work_dir is None:
                work_dir = Path(tmpdir_str) / "build-legacy"
                _prepare_export_bundle(
                    root_path=root_path,
                    job=job,
                    work_dir=work_dir,
                    runtime_modules=runtime_modules,
                    context=context,
                    canonical_template_path=canonical_template_path,
                    warnings=warnings,
                )
            runtime_modules.pack_hwpx(work_dir, hwpx_path)
        errors = runtime_modules.validate_hwpx(hwpx_path)
        if errors:
            raise ValueError(f"hwpx validation failed: {errors}")
        if used_hwpforge:
            inspect_and_validate_hwpx_via_hwpforge(hwpx_path, configured_runtime_path)
    except Exception as error:
        warnings.emit()
        error_code = getattr(error, "code", "HWPX_EXPORT_FAILED")
        LOGGER.exception("hwpx export failed code=%s detail=%s", error_code, error)
        raise ValueError(TEMPLATE_ERROR_MESSAGE) from error
    warnings.emit()
    return hwpx_path


def _prepare_export_bundle(
    root_path: Path,
    job: JobPipelineContext,
    work_dir: Path,
    runtime_modules: HwpxRuntimeModules,
    context: TemplateRenderContext,
    canonical_template_path: Path,
    warnings: QualityWarningCollector,
) -> tuple[Path, Path, Path]:
    """canonical bundle을 풀고 현재 legacy renderer로 baseline section을 만든다."""
    _extract_canonical_template(canonical_template_path, work_dir)
    section_path, header_xml_path, content_hpf, bindata_dir = _resolve_bundle_paths(work_dir)
    images_info = render_section_from_reference(
        section_path=section_path,
        root_path=root_path,
        job=job,
        bindata_dir=bindata_dir,
        runtime=runtime_modules,
        context=context,
        warnings=warnings,
    )
    _repair_inline_equation_layout_metrics(section_path, canonical_template_path, warnings)
    _strip_section_linesegarray_cache(section_path)
    _apply_bundle_common_updates(work_dir, content_hpf, header_xml_path, images_info, runtime_modules)
    _validate_template_contract(work_dir, content_hpf, header_xml_path, section_path, canonical_template_path)
    return section_path, header_xml_path, content_hpf


def _prepare_direct_hwpforge_bundle(
    root_path: Path,
    job: JobPipelineContext,
    work_dir: Path,
    runtime_modules: HwpxRuntimeModules,
    context: TemplateRenderContext,
    canonical_template_path: Path,
    configured_runtime_path: str | None,
    warnings: QualityWarningCollector,
) -> tuple[Path, Path, Path]:
    """canonical bundle에 direct HwpForge writer가 만든 section을 주입한다."""
    _extract_canonical_template(canonical_template_path, work_dir)
    section_path, header_xml_path, content_hpf, bindata_dir = _resolve_bundle_paths(work_dir)
    direct_section_path, images_info = build_section_via_hwpforge(
        root_path=root_path,
        job=job,
        bindata_dir=bindata_dir,
        output_dir=work_dir,
        year=context.year,
        warnings=warnings,
        runtime_path=configured_runtime_path,
        app_root=ROOT,
    )
    section_path.write_bytes(direct_section_path.read_bytes())
    _repair_inline_equation_layout_metrics(section_path, canonical_template_path, warnings)
    _strip_section_linesegarray_cache(section_path)
    _apply_bundle_common_updates(work_dir, content_hpf, header_xml_path, images_info, runtime_modules)
    _validate_template_contract(work_dir, content_hpf, header_xml_path, section_path, canonical_template_path)
    return section_path, header_xml_path, content_hpf


def _resolve_bundle_paths(work_dir: Path) -> tuple[Path, Path, Path, Path]:
    """작업 디렉터리 안 canonical bundle 핵심 경로를 반환한다."""
    bindata_dir = work_dir / "BinData"
    bindata_dir.mkdir(parents=True, exist_ok=True)
    return (
        work_dir / "Contents" / "section0.xml",
        work_dir / "Contents" / "header.xml",
        work_dir / "Contents" / "content.hpf",
        bindata_dir,
    )


def _apply_bundle_common_updates(
    work_dir: Path,
    content_hpf: Path,
    header_xml_path: Path,
    images_info: list[dict[str, str]],
    runtime_modules: HwpxRuntimeModules,
) -> None:
    """legacy/direct 공통으로 필요한 manifest, header, footer 갱신을 적용한다."""
    runtime_modules.update_metadata(content_hpf, "생성결과", "MathOCR")
    _inject_images_to_manifest(content_hpf, images_info)
    _update_header_xml(header_xml_path, images_info)
    _normalize_masterpage_footer(work_dir / "Contents" / "masterpage0.xml")
    _normalize_masterpage_footer(work_dir / "Contents" / "masterpage1.xml")


def _repair_inline_equation_layout_metrics(
    section_path: Path,
    canonical_template_path: Path,
    warnings: QualityWarningCollector,
) -> None:
    """최종 section0.xml의 inline equation 박스 크기를 한글 정상 프로파일로 다시 맞춘다."""
    try:
        with ZipFile(canonical_template_path, "r") as archive:
            reference_section_xml = archive.read("Contents/section0.xml")
        repaired_section_xml = repair_equation_widths(section_path.read_bytes(), reference_section_xml)
        section_path.write_bytes(repaired_section_xml)
    except Exception as error:
        warnings.add("HWPX_EQUATION_LAYOUT_REPAIR_FAILED", f"detail={error}")


def _strip_section_linesegarray_cache(section_path: Path) -> None:
    """최종 section0.xml 전체에서 stale linesegarray cache를 제거한다."""
    tree = etree.parse(str(section_path))
    root = tree.getroot()
    removed = False
    for node in root.findall(".//hp:linesegarray", HWPX_NS):
        parent = node.getparent()
        if parent is None:
            continue
        parent.remove(node)
        removed = True
    if removed:
        tree.write(str(section_path), encoding="UTF-8", xml_declaration=True)


def _apply_hwpforge_section_roundtrip(
    work_dir: Path,
    section_path: Path,
    header_xml_path: Path,
    content_hpf: Path,
    canonical_template_path: Path,
    runtime_modules: HwpxRuntimeModules,
    export_engine: str,
    configured_runtime_path: str | None,
    warnings: QualityWarningCollector,
) -> bool:
    """legacy section 위에 HwpForge roundtrip fallback을 적용한다."""
    if export_engine == "legacy":
        return False
    original_section_bytes = section_path.read_bytes()
    baseline_hwpx_path = work_dir.parent / "baseline.hwpx"
    runtime_modules.pack_hwpx(work_dir, baseline_hwpx_path)
    try:
        helper_output_dir = work_dir.parent / "hwpforge-roundtrip"
        helper_section_path = roundtrip_section_via_hwpforge(
            baseline_hwpx_path,
            helper_output_dir,
            configured_runtime_path,
        )
        section_path.write_bytes(helper_section_path.read_bytes())
        _validate_template_contract(
            work_dir,
            content_hpf,
            header_xml_path,
            section_path,
            canonical_template_path,
        )
        return True
    except (HwpForgeRoundtripError, HwpxTemplateError) as error:
        section_path.write_bytes(original_section_bytes)
        if export_engine == "hwpforge":
            raise
        warnings.add(getattr(error, "code", "HWPFORGE_SECTION_BUILD_FAILED"), f"fallback=legacy detail={error}")
        return False


def _resolve_media_type(extension: str) -> str:
    """확장자에 맞는 media-type을 계산한다."""
    if extension in {"jpg", "jpeg"}:
        return "image/jpeg"
    return f"image/{extension}"


def _inject_images_to_manifest(content_hpf: Path, images_info: list[dict[str, str]]) -> None:
    """content.hpf manifest에 추가 BinData 이미지를 등록한다."""
    if not images_info:
        return
    tree = etree.parse(str(content_hpf))
    root = tree.getroot()
    manifest_el = root.find(".//opf:manifest", HWPX_NS)
    if manifest_el is None:
        raise HwpxTemplateError(TEMPLATE_MANIFEST_MISSING_CODE, "content manifest missing")
    for img in images_info:
        item = etree.SubElement(manifest_el, f"{{{HWPX_NS['opf']}}}item")
        item.set("id", img["id"])
        item.set("href", f"BinData/{img['filename']}")
        item.set("media-type", _resolve_media_type(img["ext"]))
        item.set("isEmbeded", "1")
    tree.write(str(content_hpf), encoding="UTF-8", xml_declaration=True)


def _update_header_xml(header_xml_path: Path, images_info: list[dict[str, str]]) -> None:
    """header.xml의 binDataList를 실제 이미지 개수에 맞게 갱신한다."""
    if not images_info:
        return
    tree = etree.parse(str(header_xml_path))
    root = tree.getroot()
    bindata_list = root.find(".//hh:binDataList", HWPX_NS)
    if bindata_list is None:
        ref_list = root.find(".//hh:refList", HWPX_NS)
        if ref_list is None:
            raise HwpxTemplateError(TEMPLATE_CANONICAL_CORRUPTED_CODE, "header refList missing")
        bindata_list = etree.SubElement(ref_list, f"{{{HWPX_NS['hh']}}}binDataList")
        bindata_list.set("itemCnt", "0")
    current_cnt = len(bindata_list.findall("hh:binData", HWPX_NS))
    bindata_list.set("itemCnt", str(current_cnt + len(images_info)))
    for img in images_info:
        item = etree.SubElement(bindata_list, f"{{{HWPX_NS['hh']}}}binData")
        item.set("id", img["id"])
        item.set("extension", img["ext"])
        item.set("type", "BINA")
        item.set("format", img["ext"].upper())
    tree.write(str(header_xml_path), encoding="UTF-8", xml_declaration=True)


def _normalize_masterpage_footer(masterpage_path: Path) -> None:
    """footer에 정적 총페이지 숫자가 남아 있을 때만 제거한다."""
    tree = etree.parse(str(masterpage_path))
    root = tree.getroot()
    changed = False
    for cell in root.findall(".//hp:tc", HWPX_NS):
        if cell.find(".//hp:autoNum[@numType='PAGE']", HWPX_NS) is None:
            continue
        for sub_list in cell.findall(".//hp:subList", HWPX_NS):
            for paragraph in list(sub_list.findall("hp:p", HWPX_NS)):
                texts = "".join(node.text or "" for node in paragraph.findall(".//hp:t", HWPX_NS)).strip()
                if texts.isdigit():
                    sub_list.remove(paragraph)
                    changed = True
    if changed:
        tree.write(str(masterpage_path), encoding="UTF-8", xml_declaration=True)


def _validate_template_contract(
    work_dir: Path,
    content_hpf: Path,
    header_xml_path: Path,
    section_path: Path,
    canonical_template_path: Path,
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
    _validate_header_id_sets_match_canonical(header_xml_path, canonical_template_path)
    _validate_section_scaffold_matches_canonical(section_path, canonical_template_path)
    _validate_masterpages_match_canonical(work_dir, canonical_template_path)
    _validate_content_manifest_matches_canonical(content_hpf, canonical_template_path)


def _validate_required_manifest_entries(work_dir: Path, content_hpf: Path) -> None:
    """manifest 필수 항목과 실제 파일 존재를 함께 검증한다."""
    required_hrefs = {
        "Contents/header.xml",
        "Contents/masterpage0.xml",
        "Contents/masterpage1.xml",
        "Contents/section0.xml",
        "settings.xml",
    }
    tree = etree.parse(str(content_hpf))
    hrefs = {item.get("href", "") for item in tree.findall(".//opf:item", HWPX_NS)}
    missing_hrefs = sorted(required_hrefs - hrefs)
    if missing_hrefs:
        error_code = (
            TEMPLATE_MASTERPAGE_MISSING_CODE
            if any("masterpage" in href for href in missing_hrefs)
            else TEMPLATE_MANIFEST_MISSING_CODE
        )
        raise HwpxTemplateError(error_code, f"manifest missing required entries: {missing_hrefs}")
    missing_files = sorted(href for href in hrefs if href and not (work_dir / href).exists())
    if missing_files:
        error_code = (
            TEMPLATE_MASTERPAGE_MISSING_CODE
            if any("masterpage" in href for href in missing_files)
            else TEMPLATE_MANIFEST_MISSING_CODE
        )
        raise HwpxTemplateError(error_code, f"manifest references missing files: {missing_files}")


def _validate_masterpage_contract(work_dir: Path, section_path: Path) -> None:
    """section0.xml의 masterpage 연결과 개수를 검증한다."""
    root = etree.parse(str(section_path)).getroot()
    sec_pr = root.find(".//hp:secPr", HWPX_NS)
    if sec_pr is None:
        raise HwpxTemplateError(TEMPLATE_CANONICAL_CORRUPTED_CODE, "section secPr missing")
    master_pages = [node.get("idRef", "") for node in sec_pr.findall("hp:masterPage", HWPX_NS)]
    if master_pages != ["masterpage0", "masterpage1"]:
        raise HwpxTemplateError(TEMPLATE_MASTERPAGE_MISSING_CODE, f"unexpected masterpage refs: {master_pages}")
    if sec_pr.get("masterPageCnt") != str(len(master_pages)):
        raise HwpxTemplateError(TEMPLATE_MASTERPAGE_MISSING_CODE, "masterpage count mismatch")
    for masterpage in master_pages:
        if not (work_dir / "Contents" / f"{masterpage}.xml").exists():
            raise HwpxTemplateError(TEMPLATE_MASTERPAGE_MISSING_CODE, f"missing masterpage file: {masterpage}")


def _collect_xml_style_refs(xml_path: Path) -> tuple[set[str], set[str], set[str]]:
    """XML 문서 하나에서 paraPr/charPr/style 참조 ID를 수집한다."""
    root = etree.parse(str(xml_path)).getroot()
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
    style_refs = {
        node.get("styleIDRef", "")
        for node in root.findall(".//hp:p", HWPX_NS)
        if node.get("styleIDRef")
    }
    return para_refs, char_refs, style_refs


def _validate_style_references(header_xml_path: Path, xml_paths: list[Path]) -> None:
    """section/masterpage가 header 정의 안의 style ref만 쓰는지 확인한다."""
    header_root = etree.parse(str(header_xml_path)).getroot()
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
    valid_style_ids = {
        node.get("id", "")
        for node in header_root.findall(".//hh:style", HWPX_NS)
        if node.get("id")
    }
    used_para_ids: set[str] = set()
    used_char_ids: set[str] = set()
    used_style_ids: set[str] = set()
    for xml_path in xml_paths:
        para_refs, char_refs, style_refs = _collect_xml_style_refs(xml_path)
        used_para_ids.update(para_refs)
        used_char_ids.update(char_refs)
        used_style_ids.update(style_refs)
    if not used_para_ids <= valid_para_ids:
        raise HwpxTemplateError(
            TEMPLATE_STYLE_REF_MISMATCH_CODE,
            f"style reference mismatch: para={sorted(used_para_ids - valid_para_ids)}",
        )
    if not used_char_ids <= valid_char_ids:
        raise HwpxTemplateError(
            TEMPLATE_STYLE_REF_MISMATCH_CODE,
            f"style reference mismatch: char={sorted(used_char_ids - valid_char_ids)}",
        )
    if not used_style_ids <= valid_style_ids:
        raise HwpxTemplateError(
            TEMPLATE_STYLE_REF_MISMATCH_CODE,
            f"style reference mismatch: style={sorted(used_style_ids - valid_style_ids)}",
        )


def _read_canonical_xml(canonical_template_path: Path, inner_path: str) -> Any:
    """canonical HWPX 안 XML 하나를 읽어 파싱한다."""
    try:
        with ZipFile(canonical_template_path, "r") as archive:
            return etree.fromstring(archive.read(inner_path))
    except KeyError as error:
        error_code = (
            TEMPLATE_MASTERPAGE_MISSING_CODE if "masterpage" in inner_path else TEMPLATE_MANIFEST_MISSING_CODE
        )
        raise HwpxTemplateError(
            error_code,
            f"canonical bundle missing xml: {inner_path}",
        ) from error
    except BadZipFile as error:
        raise HwpxTemplateError(
            TEMPLATE_CANONICAL_CORRUPTED_CODE,
            f"canonical bundle is corrupted: {canonical_template_path}",
        ) from error


def _serialize_xml_for_compare(element: Any) -> bytes:
    """공백과 prefix 차이를 제거한 canonical XML 바이트를 만든다."""
    return etree.tostring(element, method="c14n")


def _collect_header_id_sets(header_root: Any) -> tuple[set[str], set[str], set[str]]:
    """header의 charPr/paraPr/style ID 집합을 추출한다."""
    return (
        {node.get("id", "") for node in header_root.findall(".//hh:charPr", HWPX_NS) if node.get("id")},
        {node.get("id", "") for node in header_root.findall(".//hh:paraPr", HWPX_NS) if node.get("id")},
        {node.get("id", "") for node in header_root.findall(".//hh:style", HWPX_NS) if node.get("id")},
    )


def _collect_manifest_items(content_root: Any) -> list[tuple[str, str, str | None]]:
    """content.hpf manifest item의 핵심 속성을 정렬해 반환한다."""
    items: list[tuple[str, str, str | None]] = []
    for node in content_root.findall(".//opf:item", HWPX_NS):
        items.append((node.get("id", ""), node.get("href", ""), node.get("media-type")))
    return sorted(items)


def _validate_header_id_sets_match_canonical(header_xml_path: Path, canonical_template_path: Path) -> None:
    """generated header의 style ID 집합이 canonical과 완전히 같은지 확인한다."""
    generated_header = etree.parse(str(header_xml_path)).getroot()
    canonical_header = _read_canonical_xml(canonical_template_path, "Contents/header.xml")
    if _collect_header_id_sets(generated_header) != _collect_header_id_sets(canonical_header):
        raise HwpxTemplateError(
            TEMPLATE_STYLE_REF_MISMATCH_CODE,
            "header id sets differ from canonical style guide",
        )


def _validate_section_scaffold_matches_canonical(section_path: Path, canonical_template_path: Path) -> None:
    """generated section의 secPr/pagePr/masterPage scaffold가 canonical과 같은지 확인한다."""
    generated_section = etree.parse(str(section_path)).getroot()
    canonical_section = _read_canonical_xml(canonical_template_path, "Contents/section0.xml")
    generated_sec_pr = generated_section.find(".//hp:secPr", HWPX_NS)
    canonical_sec_pr = canonical_section.find(".//hp:secPr", HWPX_NS)
    if generated_sec_pr is None or canonical_sec_pr is None:
        raise HwpxTemplateError(TEMPLATE_CANONICAL_CORRUPTED_CODE, "section secPr missing")
    if _serialize_xml_for_compare(generated_sec_pr) != _serialize_xml_for_compare(canonical_sec_pr):
        raise HwpxTemplateError(
            TEMPLATE_CANONICAL_CORRUPTED_CODE,
            "section scaffold differs from canonical style guide",
        )


def _validate_masterpages_match_canonical(work_dir: Path, canonical_template_path: Path) -> None:
    """generated masterpage가 canonical과 같은지 확인한다."""
    for file_name in ("masterpage0.xml", "masterpage1.xml"):
        generated_root = etree.parse(str(work_dir / "Contents" / file_name)).getroot()
        canonical_root = _read_canonical_xml(canonical_template_path, f"Contents/{file_name}")
        if _serialize_xml_for_compare(generated_root) != _serialize_xml_for_compare(canonical_root):
            raise HwpxTemplateError(
                TEMPLATE_MASTERPAGE_MISSING_CODE,
                f"masterpage differs from canonical style guide: {file_name}",
            )


def _validate_content_manifest_matches_canonical(content_hpf: Path, canonical_template_path: Path) -> None:
    """generated content.hpf가 title과 동적 이미지 항목만 제외하고 canonical과 같은지 확인한다."""
    generated_content = etree.parse(str(content_hpf)).getroot()
    canonical_content = _read_canonical_xml(canonical_template_path, "Contents/content.hpf")
    generated_title = generated_content.find(".//opf:title", HWPX_NS)
    canonical_title = canonical_content.find(".//opf:title", HWPX_NS)
    if generated_title is None or canonical_title is None:
        raise HwpxTemplateError(TEMPLATE_CANONICAL_CORRUPTED_CODE, "content title missing")
    generated_title.text = canonical_title.text
    generated_items = _collect_manifest_items(generated_content)
    canonical_items = _collect_manifest_items(canonical_content)
    dynamic_items = [
        item
        for item in generated_items
        if item[1].startswith("BinData/image") and item[1] not in {"BinData/image1.bmp", "BinData/image1.BMP"}
    ]
    preserved_items = [item for item in generated_items if item not in dynamic_items]
    if preserved_items != canonical_items:
        raise HwpxTemplateError(
            TEMPLATE_MANIFEST_MISSING_CODE,
            "content manifest differs from canonical style guide",
        )
