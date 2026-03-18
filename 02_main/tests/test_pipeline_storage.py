import copy
import importlib
import sys
import uuid
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline import orchestrator
from app.pipeline.repository import PipelineRepository, PipelineUserContext
from app.pipeline.schema import (
    ExtractorContext,
    FigureContext,
    JobPipelineContext,
    RegionContext,
    RegionPipelineContext,
)


def make_png_bytes(width: int = 32, height: int = 24) -> bytes:
    image = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class MemoryPipelineRepository(PipelineRepository):
    def __init__(self) -> None:
        self.jobs: dict[str, JobPipelineContext] = {}
        self.assets: dict[str, bytes] = {}

    def create_job(
        self,
        user: PipelineUserContext,
        filename: str,
        content: bytes,
        image_width: int,
        image_height: int,
    ) -> JobPipelineContext:
        safe_name = Path(filename or "uploaded_image").name
        job_id = str(uuid.uuid4())
        image_path = f"{user.user_id}/{job_id}/input/{safe_name}"
        self.assets[image_path] = content
        job = JobPipelineContext(
            job_id=job_id,
            file_name=safe_name,
            image_url=image_path,
            image_width=image_width,
            image_height=image_height,
            status="regions_pending",
            created_at="2026-03-15T00:00:00+00:00",
            updated_at="2026-03-15T00:00:00+00:00",
        )
        self.jobs[job_id] = job.model_copy(deep=True)
        return job

    def read_job(self, user: PipelineUserContext, job_id: str) -> JobPipelineContext:
        job = self.jobs.get(job_id)
        if job is None:
            raise FileNotFoundError(f"job not found: {job_id}")
        return job.model_copy(deep=True)

    def save_job(self, user: PipelineUserContext, job: JobPipelineContext) -> None:
        self.jobs[job.job_id] = job.model_copy(deep=True)

    def upload_bytes(
        self,
        user: PipelineUserContext,
        storage_path: str,
        content: bytes,
        content_type: str,
    ) -> None:
        self.assets[storage_path] = content

    def download_bytes(self, user: PipelineUserContext, storage_path: str) -> bytes:
        return self.assets[storage_path]

    def download_text(self, user: PipelineUserContext, storage_path: str) -> str:
        return self.assets[storage_path].decode("utf-8")

    def create_signed_url(
        self,
        user: PipelineUserContext,
        storage_path: str,
        expires_in: int = 3600,
    ) -> str:
        return f"https://signed.example/{storage_path}?expires={expires_in}"


def install_memory_repository(monkeypatch) -> MemoryPipelineRepository:
    repository = MemoryPipelineRepository()
    monkeypatch.setattr(orchestrator, "_repository_factory", lambda: repository)
    return repository


def make_user() -> PipelineUserContext:
    return PipelineUserContext(user_id="user-123", access_token="token-123")


def test_create_job_persists_source_asset_via_repository(monkeypatch):
    repository = install_memory_repository(monkeypatch)

    job = orchestrator.create_job_from_bytes(make_user(), "sample.png", make_png_bytes())

    assert job.file_name == "sample.png"
    assert job.image_width == 32
    assert job.image_height == 24
    assert repository.assets[job.image_url] == make_png_bytes()
    assert repository.jobs[job.job_id].image_url == job.image_url


def test_save_regions_replaces_existing_regions(monkeypatch):
    install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes())

    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [8, 0], [8, 8], [0, 8]], "type": "text", "order": 1},
            {"id": "q2", "polygon": [[10, 0], [18, 0], [18, 8], [10, 8]], "type": "diagram", "order": 2},
        ],
    )
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q3", "polygon": [[0, 0], [6, 0], [6, 6], [0, 6]], "type": "mixed", "order": 1},
        ],
    )

    saved_job = orchestrator.read_job(user, job.job_id)

    assert saved_job.status == "queued"
    assert [region.context.id for region in saved_job.regions] == ["q3"]


def test_save_edited_svg_increments_version_and_updates_asset_paths(monkeypatch, tmp_path):
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes())
    region = RegionPipelineContext(
        context=RegionContext(
            id="q1",
            polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
            type="diagram",
            order=1,
        ),
        extractor=ExtractorContext(ocr_text="도형", explanation="설명"),
        figure=FigureContext(
            svg_url=f"{user.user_id}/{job.job_id}/outputs/q1.svg",
            crop_url=f"{user.user_id}/{job.job_id}/outputs/q1_crop.png",
            png_rendered_url=f"{user.user_id}/{job.job_id}/outputs/q1.png",
        ),
        status="completed",
        success=True,
    )
    prepared_job = copy.deepcopy(job)
    prepared_job.status = "completed"
    prepared_job.regions = [region]
    repository.save_job(user, prepared_job)
    repository.upload_bytes(user, region.figure.svg_url or "", b"<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'/>", "image/svg+xml")

    result = orchestrator.save_edited_svg(
        user,
        job.job_id,
        "q1",
        "<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><circle cx='10' cy='10' r='5' /></svg>",
    )

    saved_job = orchestrator.read_job(user, job.job_id)
    saved_region = saved_job.regions[0]

    assert result["edited_svg_version"] == 1
    assert saved_region.figure.edited_svg_version == 1
    assert saved_region.figure.edited_svg_url in repository.assets
    assert saved_region.figure.png_rendered_url in repository.assets


def test_execute_hwpx_export_uploads_exported_file(monkeypatch, tmp_path):
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes())
    region = RegionPipelineContext(
        context=RegionContext(
            id="q1",
            polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
            type="diagram",
            order=1,
        ),
        extractor=ExtractorContext(ocr_text="문제", explanation="해설"),
        figure=FigureContext(
            crop_url=f"{user.user_id}/{job.job_id}/outputs/q1_crop.png",
            png_rendered_url=f"{user.user_id}/{job.job_id}/outputs/q1.png",
        ),
        status="completed",
        success=True,
    )
    prepared_job = copy.deepcopy(job)
    prepared_job.status = "completed"
    prepared_job.regions = [region]
    repository.save_job(user, prepared_job)
    repository.upload_bytes(user, region.figure.png_rendered_url or "", make_png_bytes(10, 10), "image/png")

    def fake_export_hwpx(root_path: Path, export_job: JobPipelineContext, export_dir: Path) -> Path:
        assert (root_path / export_job.regions[0].figure.png_rendered_url).exists()
        export_dir.mkdir(parents=True, exist_ok=True)
        output_path = export_dir / f"{export_job.job_id}.hwpx"
        output_path.write_bytes(b"hwpx-content")
        return output_path

    exporter_module = importlib.import_module("app.pipeline.exporter")
    monkeypatch.setattr(exporter_module, "export_hwpx", fake_export_hwpx)

    result = orchestrator.execute_hwpx_export(user, job.job_id)
    saved_job = orchestrator.read_job(user, job.job_id)

    assert result["download_url"].endswith(".hwpx")
    assert saved_job.status == "exported"
    assert result["download_url"] in repository.assets


def test_execute_hwpx_export_wraps_exporter_error(monkeypatch):
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes())
    prepared_job = copy.deepcopy(job)
    prepared_job.status = "completed"
    repository.save_job(user, prepared_job)

    exporter_module = importlib.import_module("app.pipeline.exporter")

    def fake_export_hwpx(root_path: Path, export_job: JobPipelineContext, export_dir: Path) -> Path:
        raise RuntimeError(
            "HWPX export runtime not found. checked: C:/runtime missing: scripts/xml_primitives.py"
        )

    monkeypatch.setattr(exporter_module, "export_hwpx", fake_export_hwpx)

    with pytest.raises(ValueError) as exc_info:
        orchestrator.execute_hwpx_export(user, job.job_id)

    assert (
        str(exc_info.value)
        == "HWPX export failed: HWPX export runtime not found. checked: C:/runtime missing: scripts/xml_primitives.py"
    )


def test_run_pipeline_uses_user_api_key_and_persists_processing_type(monkeypatch):
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes())
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [8, 0], [8, 8], [0, 8]], "type": "mixed", "order": 1},
        ],
    )

    analyze_calls: list[str] = []

    def fake_analyze_region_with_gpt(root_path: Path, crop_image_bytes: bytes, region_type: str, api_key: str | None = None):
        analyze_calls.append(api_key or "")
        return {
            "ocr_text": "문제",
            "mathml": "<math>x</math>",
            "diagram_svg": "<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'/>",
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_explanation_with_gpt", lambda *args, **kwargs: "설명")
    monkeypatch.setattr(orchestrator, "render_svg_to_png", lambda svg_text, png_path: png_path.write_bytes(make_png_bytes(10, 10)))

    result = orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-user-1234567890",
        processing_type="user_api_key",
    )
    saved_job = orchestrator.read_job(user, job.job_id)

    assert result["status"] == "completed"
    assert analyze_calls == ["sk-user-1234567890"]
    assert saved_job.processing_type == "user_api_key"
