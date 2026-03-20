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


def make_oriented_jpeg_bytes() -> bytes:
    """EXIF 회전이 포함된 테스트용 JPEG 바이트를 만든다."""
    image = Image.new("RGB", (3, 2))
    image.putdata(
        [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (0, 255, 255),
            (255, 0, 255),
        ]
    )
    exif = image.getexif()
    exif[274] = 6
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=100, subsampling=0, exif=exif.tobytes())
    return buffer.getvalue()


def is_green_pixel(pixel: tuple[int, int, int]) -> bool:
    """패딩으로 포함되어야 하는 초록색 보조 픽셀을 판별한다."""
    return pixel[1] > 200 and pixel[0] < 80 and pixel[2] < 80


def is_yellow_pixel(pixel: tuple[int, int, int]) -> bool:
    """회전 정규화 후 보이는 노란색 픽셀을 판별한다."""
    return pixel[0] > 200 and pixel[1] > 200 and pixel[2] < 120


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


def test_create_job_from_bytes_uses_exif_oriented_image_size(monkeypatch):
    """업로드 이미지 크기는 EXIF 회전을 반영해서 읽어야 한다."""
    install_memory_repository(monkeypatch)

    job = orchestrator.create_job_from_bytes(make_user(), "rotated.jpg", make_oriented_jpeg_bytes())

    assert job.image_width == 2
    assert job.image_height == 3


def test_run_pipeline_crops_exif_oriented_image_with_normalized_coordinates(monkeypatch):
    """문제 영역 crop은 EXIF 정규화된 좌표 기준으로 잘려야 한다."""
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "rotated.jpg", make_oriented_jpeg_bytes())
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]], "type": "mixed", "order": 1},
        ],
    )

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        return {
            "ocr_text": "",
            "mathml": "",
            "has_stylizable_image": False,
            "image_bbox": None,
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)

    result = orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-user-1234567890",
        processing_type="user_api_key",
        do_ocr=False,
        do_image_stylize=False,
        do_explanation=False,
    )

    saved_job = orchestrator.read_job(user, job.job_id)
    crop_path = saved_job.regions[0].figure.crop_url
    assert result["status"] == "failed"
    assert crop_path in repository.assets

    crop_image = Image.open(BytesIO(repository.assets[crop_path]))
    pixel = crop_image.getpixel((0, 0))
    assert is_yellow_pixel(pixel)


def test_run_pipeline_pads_stylizable_image_crop(monkeypatch):
    """2차 crop은 bbox보다 넉넉하게 잘려야 한다."""
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    source_image = Image.new("RGB", (32, 24), color="white")
    source_image.putpixel((19, 14), (0, 255, 0))
    source_buffer = BytesIO()
    source_image.save(source_buffer, format="PNG")
    job = orchestrator.create_job_from_bytes(user, "sample.png", source_buffer.getvalue())
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]], "type": "mixed", "order": 1},
        ],
    )

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        return {
            "ocr_text": "",
            "mathml": "",
            "has_stylizable_image": True,
            "image_bbox": [10, 10, 18, 18],
            "image_kind": "geometry",
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_styled_image_with_nano_banana", lambda *args, **kwargs: make_png_bytes(4, 4))

    result = orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-user-1234567890",
        processing_type="user_api_key",
        do_ocr=False,
        do_image_stylize=True,
        do_explanation=False,
        nano_banana_model="gemini-3-pro-image-preview",
    )

    saved_job = orchestrator.read_job(user, job.job_id)
    image_crop_path = saved_job.regions[0].figure.image_crop_url
    assert result["status"] == "failed"
    assert image_crop_path in repository.assets

    image_crop = Image.open(BytesIO(repository.assets[image_crop_path]))
    assert image_crop.width > 8
    assert image_crop.height > 8
    assert any(
        is_green_pixel(image_crop.getpixel((x, y)))
        for y in range(image_crop.height)
        for x in range(image_crop.width)
    )


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
    prepared_job.regions = [
        RegionPipelineContext(
            context=RegionContext(
                id="q1",
                polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
                type="mixed",
                order=1,
            ),
            extractor=ExtractorContext(ocr_text="문제"),
            status="completed",
            success=True,
        )
    ]
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

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        analyze_calls.append(api_key or "")
        return {
            "ocr_text": "문제",
            "mathml": "<math>x</math>",
            "has_stylizable_image": False,
            "image_bbox": None,
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_explanation_with_gpt", lambda *args, **kwargs: "설명")

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


def test_run_pipeline_saves_styled_image_when_detector_finds_visual(monkeypatch):
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes(40, 30))
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]], "type": "mixed", "order": 1},
        ],
    )

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        return {
            "ocr_text": "문제",
            "mathml": "<math>x</math>",
            "has_stylizable_image": True,
            "image_bbox": [2, 2, 12, 12],
            "image_kind": "geometry",
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    styled_calls: list[tuple[str, str, str]] = []

    def fake_generate_styled_image(
        root_path: Path,
        image_bytes: bytes,
        *,
        model_name: str,
        prompt_kind: str | None,
        prompt_version: str | None,
    ) -> bytes:
        styled_calls.append((model_name, prompt_kind or "", prompt_version or ""))
        return make_png_bytes(12, 12)

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_explanation_with_gpt", lambda *args, **kwargs: "설명")
    monkeypatch.setattr(orchestrator, "generate_styled_image_with_nano_banana", fake_generate_styled_image)

    result = orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-user-1234567890",
        processing_type="user_api_key",
        do_ocr=True,
        do_image_stylize=True,
        do_explanation=True,
        nano_banana_model="gemini-3-pro-image-preview",
    )
    saved_job = orchestrator.read_job(user, job.job_id)
    saved_region = saved_job.regions[0]

    assert result["status"] == "completed"
    assert result["executed_actions"] == ["ocr", "image_stylize", "explanation"]
    assert saved_region.figure.crop_url in repository.assets
    assert saved_region.figure.image_crop_url in repository.assets
    assert saved_region.figure.styled_image_url in repository.assets
    assert saved_region.figure.styled_image_model == "gemini-3-pro-image-preview"
    assert saved_region.figure.svg_url is None
    assert saved_region.figure.png_rendered_url is None
    assert styled_calls == [("gemini-3-pro-image-preview", "geometry", "csat_v1")]


def test_run_pipeline_skips_image_generation_when_detector_finds_no_visual(monkeypatch):
    install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes(40, 30))
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]], "type": "mixed", "order": 1},
        ],
    )

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        return {
            "ocr_text": "",
            "mathml": "",
            "has_stylizable_image": False,
            "image_bbox": None,
            "image_kind": None,
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    styled_calls: list[str] = []

    def fake_generate_styled_image(
        root_path: Path,
        image_bytes: bytes,
        *,
        model_name: str,
        prompt_kind: str | None,
        prompt_version: str | None,
    ) -> bytes:
        styled_calls.append(model_name)
        return make_png_bytes(12, 12)

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_styled_image_with_nano_banana", fake_generate_styled_image)

    result = orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-service-123",
        processing_type="service_api",
        do_ocr=False,
        do_image_stylize=True,
        do_explanation=False,
        nano_banana_model="gemini-2.5-flash-image",
    )
    saved_job = orchestrator.read_job(user, job.job_id)

    assert result["status"] == "failed"
    assert result["completed_count"] == 0
    assert result["failed_count"] == 1
    assert result["exportable_count"] == 0
    assert result["executed_actions"] == []
    assert styled_calls == []
    assert saved_job.regions[0].status == "failed"
    assert saved_job.regions[0].figure.image_crop_url is None
    assert saved_job.regions[0].figure.styled_image_url is None


def test_run_pipeline_keeps_text_and_explanation_when_image_generation_fails(monkeypatch):
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes(40, 30))
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]], "type": "mixed", "order": 1},
        ],
    )

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        return {
            "ocr_text": "문제 본문",
            "mathml": "<math>x</math>",
            "has_stylizable_image": True,
            "image_bbox": [2, 2, 12, 12],
            "image_kind": None,
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_explanation_with_gpt", lambda *args, **kwargs: "해설 본문")
    monkeypatch.setattr(
        orchestrator,
        "generate_styled_image_with_nano_banana",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("style failed")),
    )

    result = orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-service-123",
        processing_type="service_api",
        do_ocr=True,
        do_image_stylize=True,
        do_explanation=True,
        nano_banana_model="gemini-2.5-flash-image",
    )
    saved_job = orchestrator.read_job(user, job.job_id)
    saved_region = saved_job.regions[0]

    assert result["status"] == "completed"
    assert result["completed_count"] == 1
    assert result["failed_count"] == 0
    assert result["exportable_count"] == 1
    assert saved_region.status == "completed"
    assert saved_region.extractor.ocr_text == "문제 본문"
    assert saved_region.extractor.explanation == "해설 본문"
    assert saved_region.figure.styled_image_url is None
    assert saved_region.error_reason == "style failed"


def test_run_pipeline_uses_generic_prompt_when_detector_kind_is_missing(monkeypatch):
    install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes(40, 30))
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]], "type": "mixed", "order": 1},
        ],
    )

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        return {
            "ocr_text": "문제",
            "mathml": "<math>x</math>",
            "has_stylizable_image": True,
            "image_bbox": [2, 2, 12, 12],
            "image_kind": None,
            "model_used": "gpt-test",
            "openai_request_id": "req-test",
        }

    styled_calls: list[tuple[str, str, str]] = []

    def fake_generate_styled_image(
        root_path: Path,
        image_bytes: bytes,
        *,
        model_name: str,
        prompt_kind: str | None,
        prompt_version: str | None,
    ) -> bytes:
        styled_calls.append((model_name, prompt_kind or "", prompt_version or ""))
        return make_png_bytes(12, 12)

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_explanation_with_gpt", lambda *args, **kwargs: "설명")
    monkeypatch.setattr(orchestrator, "generate_styled_image_with_nano_banana", fake_generate_styled_image)

    orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-user-1234567890",
        processing_type="user_api_key",
        do_ocr=True,
        do_image_stylize=True,
        do_explanation=True,
        nano_banana_model="gemini-2.5-flash-image",
    )

    assert styled_calls == [("gemini-2.5-flash-image", "generic", "csat_v1")]


def test_run_pipeline_returns_partial_failure_counts(monkeypatch):
    repository = install_memory_repository(monkeypatch)
    user = make_user()
    job = orchestrator.create_job_from_bytes(user, "sample.png", make_png_bytes(40, 30))
    orchestrator.save_regions(
        user,
        job.job_id,
        [
            {"id": "q1", "polygon": [[0, 0], [20, 0], [20, 20], [0, 20]], "type": "mixed", "order": 1},
            {"id": "q2", "polygon": [[20, 0], [40, 0], [40, 20], [20, 20]], "type": "mixed", "order": 2},
        ],
    )

    def fake_analyze_region_with_gpt(
        root_path: Path,
        crop_image_bytes: bytes,
        region_type: str,
        api_key: str | None = None,
        *,
        include_ocr: bool = True,
        include_image_detection: bool = False,
    ):
        if fake_analyze_region_with_gpt.calls == 0:
            fake_analyze_region_with_gpt.calls += 1
            return {
                "ocr_text": "첫 번째 문제",
                "mathml": "<math>a</math>",
                "has_stylizable_image": False,
                "image_bbox": None,
                "model_used": "gpt-test",
                "openai_request_id": "req-test-1",
            }
        fake_analyze_region_with_gpt.calls += 1
        raise RuntimeError("ocr failed")

    fake_analyze_region_with_gpt.calls = 0

    monkeypatch.setattr(orchestrator, "analyze_region_with_gpt", fake_analyze_region_with_gpt)
    monkeypatch.setattr(orchestrator, "generate_explanation_with_gpt", lambda *args, **kwargs: "해설")

    result = orchestrator.run_pipeline(
        user,
        job.job_id,
        api_key="sk-service-123",
        processing_type="service_api",
        do_ocr=True,
        do_image_stylize=False,
        do_explanation=True,
    )
    saved_job = orchestrator.read_job(user, job.job_id)

    assert result["status"] == "failed"
    assert result["completed_count"] == 1
    assert result["failed_count"] == 1
    assert result["exportable_count"] == 1
    assert saved_job.regions[0].status == "completed"
    assert saved_job.regions[1].status == "failed"
    assert saved_job.regions[0].extractor.ocr_text == "첫 번째 문제"
    assert saved_job.regions[1].extractor.ocr_text is None
