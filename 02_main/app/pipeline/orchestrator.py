from __future__ import annotations

import copy
import tempfile
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from app.pipeline.extractor import analyze_region_with_gpt, generate_explanation_with_gpt
from app.pipeline.figure import build_mock_svg, crop_region_image, normalize_svg_xml, render_svg_to_png, sanitize_svg
from app.pipeline.repository import PipelineRepository, PipelineUserContext, build_repository_from_settings
from app.pipeline.schema import JobPipelineContext, RegionContext, RegionPipelineContext

ROOT = Path(__file__).resolve().parents[2]
_repository_factory: Callable[[], PipelineRepository] | None = None


def _utc_now() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""
    return datetime.now(timezone.utc).isoformat()


def _get_repository() -> PipelineRepository:
    """현재 세션에서 사용할 저장소 구현체를 반환한다."""
    if _repository_factory is not None:
        return _repository_factory()
    return build_repository_from_settings(ROOT)


def _read_image_size(content: bytes) -> tuple[int, int]:
    """업로드 이미지 바이트에서 가로세로 크기를 읽는다."""
    try:
        with Image.open(BytesIO(content)) as image:
            return image.width, image.height
    except Exception:
        return 0, 0


def read_job(user: PipelineUserContext, job_id: str) -> JobPipelineContext:
    """영구 저장소에서 job과 region 상태를 읽는다."""
    return _get_repository().read_job(user, job_id)


def save_job(user: PipelineUserContext, job: JobPipelineContext) -> None:
    """변경된 job 전체 상태를 영구 저장소에 반영한다."""
    job.updated_at = _utc_now()
    _get_repository().save_job(user, job)


def create_asset_url(user: PipelineUserContext, storage_path: str | None, expires_in: int = 3600) -> str | None:
    """Storage 내부 경로를 프런트가 바로 쓸 수 있는 signed URL로 바꾼다."""
    if not storage_path:
        return None
    return _get_repository().create_signed_url(user, storage_path, expires_in=expires_in)


def download_asset_bytes(user: PipelineUserContext, storage_path: str) -> bytes:
    """Storage 내부 경로의 원본 바이트를 읽어온다."""
    return _get_repository().download_bytes(user, storage_path)


def create_job_from_bytes(user: PipelineUserContext, filename: str, content: bytes) -> JobPipelineContext:
    """업로드 이미지를 저장하고 초기 job row를 생성한다."""
    image_width, image_height = _read_image_size(content)
    return _get_repository().create_job(user, filename, content, image_width, image_height)


def save_regions(user: PipelineUserContext, job_id: str, regions_dict: list[dict[str, Any]]) -> dict:
    """사용자가 지정한 영역 목록으로 job region 상태를 교체한다."""
    job = read_job(user, job_id)
    regions: list[RegionPipelineContext] = []

    for raw_region in regions_dict:
        polygon = raw_region["polygon"]
        if len(polygon) < 4:
            raise ValueError("polygon must contain at least 4 points")

        region_context = RegionContext(
            id=raw_region["id"],
            polygon=polygon,
            type=raw_region["type"],
            order=int(raw_region.get("order", 1)),
        )
        regions.append(RegionPipelineContext(context=region_context))

    job.regions = regions
    job.status = "queued"
    job.last_error = None
    save_job(user, job)
    return {"message": "regions saved", "count": len(regions)}


def _materialize_input_image(
    user: PipelineUserContext,
    repository: PipelineRepository,
    job: JobPipelineContext,
    temp_root: Path,
) -> Path:
    """Storage의 원본 이미지를 임시 작업 경로로 내려받는다."""
    input_path = temp_root / "input" / job.file_name
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(repository.download_bytes(user, job.image_url))
    return input_path


def run_pipeline(user: PipelineUserContext, job_id: str) -> dict:
    """OCR/도형 분석을 수행하고 결과를 Storage와 DB에 저장한다."""
    repository = _get_repository()
    job = read_job(user, job_id)
    if not job.regions:
        raise ValueError("regions not set")

    job.status = "running"
    job.last_error = None
    for region in job.regions:
        region.status = "running"
        region.success = None
        region.error_reason = None
    save_job(user, job)

    any_failed = False

    with tempfile.TemporaryDirectory() as tempdir_str:
        temp_root = Path(tempdir_str)
        image_path = _materialize_input_image(user, repository, job, temp_root)

        for region in job.regions:
            started = time.perf_counter()
            region_id = region.context.id
            outputs_dir = temp_root / "outputs"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            svg_path = outputs_dir / f"{region_id}.svg"
            crop_path = outputs_dir / f"{region_id}_crop.png"
            png_path = outputs_dir / f"{region_id}.png"

            try:
                crop_bytes = crop_region_image(image_path, region.context.polygon, crop_path)
                crop_storage_path = f"{user.user_id}/{job.job_id}/outputs/{region_id}_crop.png"
                repository.upload_bytes(user, crop_storage_path, crop_bytes, "image/png")
                region.figure.crop_url = crop_storage_path

                analyzed = analyze_region_with_gpt(ROOT, crop_bytes, region.context.type)
                ocr_text = analyzed.get("ocr_text") or ""
                mathml = analyzed.get("mathml") or ""

                try:
                    explanation = generate_explanation_with_gpt(ROOT, crop_bytes, ocr_text, mathml)
                except Exception:
                    explanation = "연습장에 풀이를 기록하세요."

                svg_text = analyzed.get("diagram_svg") or build_mock_svg(
                    region_id,
                    region.context.type,
                    region.context.polygon,
                )
                svg_path.write_text(svg_text, encoding="utf-8")
                svg_storage_path = f"{user.user_id}/{job.job_id}/outputs/{region_id}.svg"
                repository.upload_bytes(user, svg_storage_path, svg_text.encode("utf-8"), "image/svg+xml")

                region.extractor.ocr_text = ocr_text
                region.extractor.explanation = explanation
                region.extractor.mathml = mathml
                region.extractor.model_used = analyzed.get("model_used")
                region.extractor.openai_request_id = analyzed.get("openai_request_id")
                region.figure.svg_url = svg_storage_path

                try:
                    render_svg_to_png(svg_text, png_path)
                    png_storage_path = f"{user.user_id}/{job.job_id}/outputs/{region_id}.png"
                    repository.upload_bytes(user, png_storage_path, png_path.read_bytes(), "image/png")
                    region.figure.png_rendered_url = png_storage_path
                except Exception:
                    region.figure.png_rendered_url = None

                region.status = "completed"
                region.success = True
                region.error_reason = None
            except Exception as error:
                any_failed = True
                region.status = "failed"
                region.success = False
                region.error_reason = str(error)
                job.last_error = str(error)
            finally:
                region.processing_ms = int((time.perf_counter() - started) * 1000)
                save_job(user, job)

    job.status = "failed" if any_failed else "completed"
    if not any_failed:
        job.last_error = None
    save_job(user, job)
    return {"job_id": job_id, "status": job.status}


def get_region_svg(user: PipelineUserContext, job_id: str, region_id: str) -> dict:
    """저장된 SVG를 읽어 정규화된 XML 문자열로 반환한다."""
    repository = _get_repository()
    job = read_job(user, job_id)
    region = next((candidate for candidate in job.regions if candidate.context.id == region_id), None)
    if region is None:
        raise ValueError("region not found")

    svg_path = region.figure.edited_svg_url or region.figure.svg_url
    if not svg_path:
        raise ValueError("svg not found")

    raw_svg = repository.download_text(user, svg_path)
    try:
        normalized_svg = normalize_svg_xml(raw_svg)
    except ValueError:
        normalized_svg = raw_svg

    return {
        "region_id": region_id,
        "svg": normalized_svg,
        "source": "edited" if region.figure.edited_svg_url else "original",
    }


def save_edited_svg(user: PipelineUserContext, job_id: str, region_id: str, svg_text: str) -> dict:
    """편집된 SVG와 재렌더된 PNG를 Storage에 저장한다."""
    repository = _get_repository()
    job = read_job(user, job_id)
    region = next((candidate for candidate in job.regions if candidate.context.id == region_id), None)
    if region is None:
        raise ValueError("region not found")
    if region.status != "completed":
        raise ValueError("region is not completed")

    cleaned = sanitize_svg(svg_text)
    next_version = region.figure.edited_svg_version + 1
    edited_storage_path = f"{user.user_id}/{job_id}/outputs/{region_id}.edited.v{next_version}.svg"
    latest_storage_path = f"{user.user_id}/{job_id}/outputs/{region_id}.edited.latest.svg"
    repository.upload_bytes(user, edited_storage_path, cleaned.encode("utf-8"), "image/svg+xml")
    repository.upload_bytes(user, latest_storage_path, cleaned.encode("utf-8"), "image/svg+xml")

    with tempfile.TemporaryDirectory() as tempdir_str:
        png_path = Path(tempdir_str) / f"{region_id}.png"
        try:
            render_svg_to_png(cleaned, png_path)
            png_storage_path = f"{user.user_id}/{job_id}/outputs/{region_id}.png"
            repository.upload_bytes(user, png_storage_path, png_path.read_bytes(), "image/png")
            region.figure.png_rendered_url = png_storage_path
        except Exception:
            pass

    region.figure.edited_svg_url = latest_storage_path
    region.figure.edited_svg_version = next_version
    save_job(user, job)

    return {
        "region_id": region_id,
        "edited_svg_url": region.figure.edited_svg_url,
        "edited_svg_version": next_version,
    }


def _materialize_job_for_export(
    user: PipelineUserContext,
    repository: PipelineRepository,
    job: JobPipelineContext,
    temp_root: Path,
) -> JobPipelineContext:
    """HWPX exporter가 읽을 수 있도록 필요한 이미지를 임시 경로로 풀어놓는다."""
    materialized = copy.deepcopy(job)
    for region in materialized.regions:
        selected_field = "png_rendered_url" if region.figure.png_rendered_url else "crop_url"
        storage_path = getattr(region.figure, selected_field)
        if not storage_path:
            continue

        rel_path = Path("assets") / region.context.id / Path(storage_path).name
        local_path = temp_root / rel_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(repository.download_bytes(user, storage_path))
        setattr(region.figure, selected_field, rel_path.as_posix())
    return materialized


def execute_hwpx_export(user: PipelineUserContext, job_id: str) -> dict:
    """완료된 OCR 결과를 HWPX로 내보내고 Storage에 저장한다."""
    repository = _get_repository()
    job = read_job(user, job_id)
    if job.status not in ("completed", "failed", "exported"):
        raise ValueError("job is not finished")

    try:
        from app.pipeline.exporter import export_hwpx

        with tempfile.TemporaryDirectory() as tempdir_str:
            temp_root = Path(tempdir_str)
            materialized_job = _materialize_job_for_export(user, repository, job, temp_root)
            export_dir = temp_root / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            hwpx_path = export_hwpx(temp_root, materialized_job, export_dir)
            storage_path = f"{user.user_id}/{job_id}/exports/{job_id}.hwpx"
            repository.upload_bytes(user, storage_path, hwpx_path.read_bytes(), "application/hwp+zip")
    except Exception as error:
        raise ValueError(f"HWPX export failed: {error}") from error

    job.status = "exported"
    job.hwpx_export_path = storage_path
    save_job(user, job)
    return {"download_url": storage_path}
