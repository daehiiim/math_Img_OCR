import importlib
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from PIL import Image
from lxml import etree

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.schema import (
    ExtractorContext,
    FigureContext,
    JobPipelineContext,
    RegionContext,
    RegionPipelineContext,
)

REQUIRED_RUNTIME_FILES = (
    Path("scripts/xml_primitives.py"),
    Path("scripts/exam_helpers.py"),
    Path("scripts/hwpx_utils.py"),
    Path("templates/base/BinData/image1.PNG"),
    Path("templates/base/mimetype"),
    Path("templates/base/Contents/header.xml"),
    Path("templates/base/Contents/content.hpf"),
    Path("templates/base/Contents/masterpage0.xml"),
    Path("templates/base/Contents/masterpage1.xml"),
    Path("templates/base/Contents/section0.xml"),
)

OPTIONAL_RUNTIME_FILES = (
    Path("templates/base/settings.xml"),
    Path("templates/base/version.xml"),
    Path("templates/base/META-INF/container.rdf"),
    Path("templates/base/META-INF/container.xml"),
    Path("templates/base/META-INF/manifest.xml"),
    Path("templates/base/Preview/PrvImage.png"),
    Path("templates/base/Preview/PrvText.txt"),
)

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "opf": "http://www.idpf.org/2007/opf/",
}


def make_png_bytes(width: int = 32, height: int = 24) -> bytes:
    """테스트용 PNG 바이트를 생성한다."""
    image = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def load_exporter_module():
    """exporter 모듈을 매 테스트마다 새로 import한다."""
    sys.modules.pop("app.pipeline.exporter", None)
    return importlib.import_module("app.pipeline.exporter")


def copy_runtime_bundle(target_dir: Path) -> Path:
    """저장소의 vendored runtime bundle을 임시 경로로 복사한다."""
    source_dir = Path(__file__).resolve().parents[1] / "vendor" / "hwpxskill-math"

    for relative_path in REQUIRED_RUNTIME_FILES + OPTIONAL_RUNTIME_FILES:
        source_path = source_dir / relative_path
        destination_path = target_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(source_path.read_bytes())

    return target_dir


def make_export_job(image_path: str) -> JobPipelineContext:
    """HWPX export 테스트에 필요한 최소 job fixture를 만든다."""
    return JobPipelineContext(
        job_id="job-export-1",
        file_name="uploaded_image.png",
        image_url="user-123/job-export-1/input/uploaded_image.png",
        image_width=32,
        image_height=24,
        status="completed",
        created_at="2026-03-18T00:00:00+00:00",
        updated_at="2026-03-18T00:00:00+00:00",
        regions=[
            RegionPipelineContext(
                context=RegionContext(
                    id="q1",
                    polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
                    type="diagram",
                    order=1,
                ),
                extractor=ExtractorContext(
                    ocr_text="문제 본문",
                    explanation="해설 본문",
                ),
                figure=FigureContext(image_crop_url=image_path),
                status="completed",
                success=True,
            )
        ],
    )


def test_exporter_module_import_is_lazy():
    """exporter 모듈 import 자체는 외부 runtime 없이 성공해야 한다."""
    module = load_exporter_module()

    assert callable(module.export_hwpx)


def test_resolve_hwpx_runtime_prefers_configured_skill_dir(tmp_path):
    """설정 경로가 유효하면 vendored 경로보다 먼저 선택해야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    configured_dir = copy_runtime_bundle(tmp_path / "configured-skill")
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")

    runtime = module._resolve_hwpx_runtime(
        app_root=app_root,
        configured_skill_dir=str(configured_dir),
        codex_home=tmp_path / "codex-home",
        home_dir=tmp_path / "home",
    )

    assert runtime.skill_dir == configured_dir


def test_resolve_hwpx_runtime_uses_vendored_fallback(tmp_path):
    """설정 경로가 없으면 02_main/vendor bundle을 기본으로 선택해야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    vendored_dir = copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")

    runtime = module._resolve_hwpx_runtime(
        app_root=app_root,
        configured_skill_dir=None,
        codex_home=tmp_path / "codex-home",
        home_dir=tmp_path / "home",
    )

    assert runtime.skill_dir == vendored_dir


def test_resolve_hwpx_runtime_reports_checked_paths_and_missing_files(tmp_path):
    """모든 후보가 실패하면 확인한 경로와 누락 파일을 함께 보여줘야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    configured_dir = tmp_path / "missing-configured"
    codex_home = tmp_path / "missing-codex-home"
    home_dir = tmp_path / "missing-home"

    with pytest.raises(FileNotFoundError) as exc_info:
        module._resolve_hwpx_runtime(
            app_root=app_root,
            configured_skill_dir=str(configured_dir),
            codex_home=codex_home,
            home_dir=home_dir,
        )

    message = str(exc_info.value)

    assert "HWPX export runtime not found." in message
    assert str(configured_dir) in message
    assert str(app_root / "vendor" / "hwpxskill-math") in message
    assert str(codex_home / "skills" / "hwpxskill-math") in message
    assert str(home_dir / ".codex" / "skills" / "hwpxskill-math") in message
    assert "scripts/xml_primitives.py" in message
    assert "templates/base/Contents/header.xml" in message


def test_export_hwpx_creates_valid_file_using_vendored_runtime(tmp_path, monkeypatch):
    """vendored runtime bundle만으로 실제 HWPX 파일을 생성해야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    monkeypatch.setattr(module, "ROOT", app_root)
    monkeypatch.setattr(module, "_get_codex_home", lambda: tmp_path / "missing-codex-home")
    monkeypatch.setattr(module, "_get_home_dir", lambda: tmp_path / "missing-home")

    root_path = tmp_path / "runtime"
    image_relative_path = Path("assets/q1.png")
    image_path = root_path / image_relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes())

    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)

    assert hwpx_path.exists()
    assert hwpx_path.suffix == ".hwpx"

    with ZipFile(hwpx_path, "r") as archive:
        names = archive.namelist()
        assert names[0] == "mimetype"
        assert "Contents/content.hpf" in names
        assert "Contents/header.xml" in names
        assert "Contents/section0.xml" in names
        assert any(name.startswith("BinData/img_q1_") for name in names)


def test_export_hwpx_uses_reference_masterpages_and_page_layout(tmp_path, monkeypatch):
    """레퍼런스 템플릿의 masterpage와 조판 규칙을 유지해야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    monkeypatch.setattr(module, "ROOT", app_root)
    monkeypatch.setattr(module, "_get_codex_home", lambda: tmp_path / "missing-codex-home")
    monkeypatch.setattr(module, "_get_home_dir", lambda: tmp_path / "missing-home")

    root_path = tmp_path / "runtime"
    image_relative_path = Path("assets/q1.png")
    image_path = root_path / image_relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes())

    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)

    with ZipFile(hwpx_path, "r") as archive:
        names = archive.namelist()
        assert "Contents/masterpage0.xml" in names
        assert "Contents/masterpage1.xml" in names

        section_root = etree.fromstring(archive.read("Contents/section0.xml"))
        sec_pr = section_root.find(".//hp:secPr", NS)
        assert sec_pr is not None
        assert sec_pr.get("masterPageCnt") == "2"

        page_pr = sec_pr.find("hp:pagePr", NS)
        assert page_pr is not None
        assert page_pr.get("width") == "77102"
        assert page_pr.get("height") == "111685"

        margin = page_pr.find("hp:margin", NS)
        assert margin is not None
        assert margin.get("header") == "6803"
        assert margin.get("footer") == "2551"

        master_pages = sec_pr.findall("hp:masterPage", NS)
        assert [node.get("idRef") for node in master_pages] == ["masterpage0", "masterpage1"]

        col_pr = section_root.find(".//hp:colPr", NS)
        assert col_pr is not None
        assert col_pr.get("colCount") == "2"
        assert col_pr.get("sameGap") == "3316"


def test_export_hwpx_renders_current_year_and_current_page_only_footer(tmp_path, monkeypatch):
    """상단 연도는 런타임 값으로 바꾸고 footer는 현재 페이지 자동필드만 남겨야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    monkeypatch.setattr(module, "ROOT", app_root)
    monkeypatch.setattr(module, "_get_codex_home", lambda: tmp_path / "missing-codex-home")
    monkeypatch.setattr(module, "_get_home_dir", lambda: tmp_path / "missing-home")
    monkeypatch.setattr(
        module,
        "_build_render_context",
        lambda: module.TemplateRenderContext(year="2031"),
    )

    root_path = tmp_path / "runtime"
    image_relative_path = Path("assets/q1.png")
    image_path = root_path / image_relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes())

    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)

    with ZipFile(hwpx_path, "r") as archive:
        section_xml = archive.read("Contents/section0.xml").decode("utf-8")
        masterpage0_xml = archive.read("Contents/masterpage0.xml").decode("utf-8")
        masterpage1_xml = archive.read("Contents/masterpage1.xml").decode("utf-8")

    assert "2031학년도 수학시험 문제지" in section_xml
    assert 'numType="PAGE"' in masterpage0_xml
    assert 'numType="PAGE"' in masterpage1_xml
    assert ">20<" not in masterpage0_xml
    assert ">20<" not in masterpage1_xml


def test_export_hwpx_section_uses_only_header_defined_style_refs(tmp_path, monkeypatch):
    """생성된 본문은 레퍼런스 header.xml에 정의된 style ref만 사용해야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    monkeypatch.setattr(module, "ROOT", app_root)
    monkeypatch.setattr(module, "_get_codex_home", lambda: tmp_path / "missing-codex-home")
    monkeypatch.setattr(module, "_get_home_dir", lambda: tmp_path / "missing-home")

    root_path = tmp_path / "runtime"
    image_relative_path = Path("assets/q1.png")
    image_path = root_path / image_relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes())

    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)

    with ZipFile(hwpx_path, "r") as archive:
        header_root = etree.fromstring(archive.read("Contents/header.xml"))
        section_root = etree.fromstring(archive.read("Contents/section0.xml"))

    valid_para_ids = {
        node.get("id")
        for node in header_root.findall(".//hh:paraPr", {"hh": "http://www.hancom.co.kr/hwpml/2011/head"})
    }
    valid_char_ids = {
        node.get("id")
        for node in header_root.findall(".//hh:charPr", {"hh": "http://www.hancom.co.kr/hwpml/2011/head"})
    }
    used_para_ids = {
        node.get("paraPrIDRef")
        for node in section_root.findall(".//hp:p", NS)
        if node.get("paraPrIDRef")
    }
    used_char_ids = {
        node.get("charPrIDRef")
        for node in section_root.findall(".//hp:run", NS)
        if node.get("charPrIDRef")
    }

    assert used_para_ids <= valid_para_ids
    assert used_char_ids <= valid_char_ids


def test_export_hwpx_skips_empty_failed_regions_and_renumbers_items(tmp_path, monkeypatch):
    """내보낼 텍스트가 없는 실패 영역은 건너뛰고 문제 번호를 다시 매겨야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    monkeypatch.setattr(module, "ROOT", app_root)
    monkeypatch.setattr(module, "_get_codex_home", lambda: tmp_path / "missing-codex-home")
    monkeypatch.setattr(module, "_get_home_dir", lambda: tmp_path / "missing-home")

    root_path = tmp_path / "runtime"
    image_relative_path = Path("assets/q1.png")
    image_path = root_path / image_relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes())

    export_job = JobPipelineContext(
        job_id="job-export-2",
        file_name="uploaded_image.png",
        image_url="user-123/job-export-2/input/uploaded_image.png",
        image_width=32,
        image_height=24,
        status="failed",
        created_at="2026-03-18T00:00:00+00:00",
        updated_at="2026-03-18T00:00:00+00:00",
        regions=[
            RegionPipelineContext(
                context=RegionContext(
                    id="q1",
                    polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
                    type="mixed",
                    order=1,
                ),
                extractor=ExtractorContext(ocr_text="첫 번째 문제", explanation="첫 번째 해설"),
                figure=FigureContext(image_crop_url=image_relative_path.as_posix()),
                status="completed",
                success=True,
            ),
            RegionPipelineContext(
                context=RegionContext(
                    id="q2",
                    polygon=[[9, 0], [16, 0], [16, 8], [9, 8]],
                    type="mixed",
                    order=2,
                ),
                extractor=ExtractorContext(),
                figure=FigureContext(),
                status="failed",
                success=False,
                error_reason="ocr failed",
            ),
            RegionPipelineContext(
                context=RegionContext(
                    id="q3",
                    polygon=[[17, 0], [24, 0], [24, 8], [17, 8]],
                    type="mixed",
                    order=3,
                ),
                extractor=ExtractorContext(ocr_text="세 번째 문제"),
                figure=FigureContext(),
                status="failed",
                success=False,
                error_reason="image failed",
            ),
        ],
    )

    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, export_job, export_dir)

    with ZipFile(hwpx_path, "r") as archive:
        section_xml = archive.read("Contents/section0.xml").decode("utf-8")

    assert "첫 번째 문제" in section_xml
    assert "세 번째 문제" in section_xml
    assert "2. " in section_xml
    assert "3. " not in section_xml
