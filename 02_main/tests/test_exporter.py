import copy
import importlib
import shutil
import sys
import zipfile
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.schema import (
    ExtractorContext,
    FigureContext,
    JobPipelineContext,
    RegionContext,
    RegionPipelineContext,
)

RUNTIME_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "vendor" / "hwpxskill-math"


def make_png_bytes(width: int = 32, height: int = 24) -> bytes:
    image = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_job(image_path: str) -> JobPipelineContext:
    region = RegionPipelineContext(
        context=RegionContext(
            id="q1",
            polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
            type="diagram",
            order=1,
        ),
        extractor=ExtractorContext(ocr_text="문제", explanation="해설"),
        figure=FigureContext(png_rendered_url=image_path),
        status="completed",
        success=True,
    )
    return JobPipelineContext(
        job_id=str(uuid.uuid4()),
        file_name="sample.png",
        image_url="user/job/input/sample.png",
        image_width=32,
        image_height=24,
        status="completed",
        created_at="2026-03-15T00:00:00+00:00",
        updated_at="2026-03-15T00:00:00+00:00",
        regions=[region],
    )


def copy_runtime_bundle(target_dir: Path) -> Path:
    shutil.copytree(RUNTIME_FIXTURE_DIR, target_dir)
    return target_dir


def import_exporter_module():
    sys.modules.pop("app.pipeline.exporter", None)
    return importlib.import_module("app.pipeline.exporter")


def test_exporter_module_imports_without_runtime_side_effects():
    exporter = import_exporter_module()

    assert hasattr(exporter, "export_hwpx")


def test_resolve_hwpx_runtime_prefers_env_override(tmp_path, monkeypatch):
    exporter = import_exporter_module()
    backend_root = tmp_path / "backend"
    override_dir = copy_runtime_bundle(tmp_path / "override" / "hwpxskill-math")
    copy_runtime_bundle(backend_root / "vendor" / "hwpxskill-math")

    monkeypatch.setattr(exporter, "BACKEND_ROOT", backend_root)
    monkeypatch.setattr(exporter, "_get_configured_hwpx_skill_dir", lambda: str(override_dir))
    monkeypatch.setattr(exporter, "_get_codex_home", lambda: None)
    monkeypatch.setattr(exporter, "_get_user_home", lambda: tmp_path / "home")

    runtime = exporter._resolve_hwpx_runtime()

    assert runtime.skill_dir == override_dir


def test_resolve_hwpx_runtime_uses_vendored_fallback(tmp_path, monkeypatch):
    exporter = import_exporter_module()
    backend_root = tmp_path / "backend"
    vendor_dir = copy_runtime_bundle(backend_root / "vendor" / "hwpxskill-math")

    monkeypatch.setattr(exporter, "BACKEND_ROOT", backend_root)
    monkeypatch.setattr(exporter, "_get_configured_hwpx_skill_dir", lambda: None)
    monkeypatch.setattr(exporter, "_get_codex_home", lambda: None)
    monkeypatch.setattr(exporter, "_get_user_home", lambda: tmp_path / "home")

    runtime = exporter._resolve_hwpx_runtime()

    assert runtime.skill_dir == vendor_dir


def test_resolve_hwpx_runtime_reports_checked_paths_and_missing_items(tmp_path, monkeypatch):
    exporter = import_exporter_module()
    backend_root = tmp_path / "backend"
    override_dir = tmp_path / "missing-override"
    codex_home = tmp_path / "codex-home"
    home_dir = tmp_path / "home"

    monkeypatch.setattr(exporter, "BACKEND_ROOT", backend_root)
    monkeypatch.setattr(exporter, "_get_configured_hwpx_skill_dir", lambda: str(override_dir))
    monkeypatch.setattr(exporter, "_get_codex_home", lambda: codex_home)
    monkeypatch.setattr(exporter, "_get_user_home", lambda: home_dir)

    with pytest.raises(FileNotFoundError) as exc_info:
        exporter._resolve_hwpx_runtime()

    message = str(exc_info.value)

    assert str(override_dir) in message
    assert str(backend_root / "vendor" / "hwpxskill-math") in message
    assert str(codex_home / "skills" / "hwpxskill-math") in message
    assert str(home_dir / ".codex" / "skills" / "hwpxskill-math") in message
    assert "scripts/xml_primitives.py" in message
    assert "templates/base/Contents/header.xml" in message


def test_export_hwpx_creates_valid_hwpx_file(tmp_path, monkeypatch):
    exporter = import_exporter_module()
    skill_dir = copy_runtime_bundle(tmp_path / "runtime" / "hwpxskill-math")
    root_path = tmp_path / "workspace"
    image_path = root_path / "assets" / "q1" / "q1.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes(48, 36))
    job = build_job("assets/q1/q1.png")

    monkeypatch.setattr(exporter, "_get_configured_hwpx_skill_dir", lambda: str(skill_dir))
    monkeypatch.setattr(exporter, "_get_codex_home", lambda: None)
    monkeypatch.setattr(exporter, "_get_user_home", lambda: tmp_path / "home")

    hwpx_path = exporter.export_hwpx(root_path, copy.deepcopy(job), root_path / "exports")

    assert hwpx_path.exists()

    with zipfile.ZipFile(hwpx_path, "r") as archive:
        assert "mimetype" in archive.namelist()
        assert "Contents/content.hpf" in archive.namelist()
        assert "Contents/header.xml" in archive.namelist()
        assert "Contents/section0.xml" in archive.namelist()
        assert archive.read("mimetype").decode("utf-8").strip() == "application/hwp+zip"


def test_export_hwpx_converts_math_markup_to_equation_controls(tmp_path, monkeypatch):
    exporter = import_exporter_module()
    skill_dir = copy_runtime_bundle(tmp_path / "runtime" / "hwpxskill-math")
    root_path = tmp_path / "workspace"
    image_path = root_path / "assets" / "q1" / "q1.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes(48, 36))
    job = build_job("assets/q1/q1.png")
    job.regions[0].extractor.ocr_text = "문제 <math>AB</math> 입니다"
    job.regions[0].extractor.explanation = "해설 <math>x+1</math> 입니다"

    monkeypatch.setattr(exporter, "_get_configured_hwpx_skill_dir", lambda: str(skill_dir))
    monkeypatch.setattr(exporter, "_get_codex_home", lambda: None)
    monkeypatch.setattr(exporter, "_get_user_home", lambda: tmp_path / "home")

    hwpx_path = exporter.export_hwpx(root_path, copy.deepcopy(job), root_path / "exports")

    with zipfile.ZipFile(hwpx_path, "r") as archive:
        section_xml = archive.read("Contents/section0.xml").decode("utf-8")

    assert "<math>" not in section_xml
    assert "<hp:equation" in section_xml
    assert "<hp:script>AB</hp:script>" in section_xml
    assert "<hp:script>x+1</hp:script>" in section_xml
