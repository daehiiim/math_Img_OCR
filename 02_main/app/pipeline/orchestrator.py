from __future__ import annotations

import copy
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.pipeline.extractor import (
    analyze_region_with_gpt,
    generate_explanation_with_gpt,
    generate_styled_image_with_nano_banana,
)
from app.pipeline.figure import (
    crop_image_bytes,
    crop_region_image,
    normalize_svg_xml,
    read_image_size,
    render_svg_to_png,
    sanitize_svg,
)
from app.pipeline.markdown_contract import (
    MARKDOWN_VERSION,
    bridge_legacy_markup_to_markdown,
    has_markdown_output,
)
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
        return read_image_size(content)
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
            type=raw_region.get("type") or "mixed",
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


def _is_region_exportable(region: RegionPipelineContext) -> bool:
    """문제 또는 해설 텍스트가 있으면 문서 포함 가능 영역으로 본다."""
    return bool(
        has_markdown_output(region.extractor.problem_markdown, region.extractor.explanation_markdown)
        or (region.extractor.ocr_text or "").strip()
        or (region.extractor.explanation or "").strip()
    )


def _sync_region_markdown_version(region: RegionPipelineContext) -> None:
    """현재 region에 Markdown 출력이 남아 있으면 버전을 기록한다."""
    if has_markdown_output(region.extractor.problem_markdown, region.extractor.explanation_markdown):
        region.extractor.markdown_version = MARKDOWN_VERSION
        return
    region.extractor.markdown_version = None


def _should_skip_region(region: RegionPipelineContext) -> bool:
    """액션 재실행 정책상 모든 영역을 다시 처리 대상으로 유지한다."""
    return False


def _reset_region_outputs(
    region: RegionPipelineContext,
    *,
    do_ocr: bool,
    do_image_stylize: bool,
    do_explanation: bool,
) -> None:
    """선택한 액션에 해당하는 산출물만 초기화한다."""
    if do_ocr:
        region.extractor.ocr_text = None
        region.extractor.mathml = None
        region.extractor.problem_markdown = None
    if do_explanation:
        region.extractor.explanation = None
        region.extractor.explanation_markdown = None
    _sync_region_markdown_version(region)
    region.extractor.model_used = None
    region.extractor.openai_request_id = None
    region.figure.crop_url = None
    if do_image_stylize:
        region.figure.image_crop_url = None
        region.figure.styled_image_url = None
        region.figure.styled_image_model = None
    region.status = "running"
    region.success = None
    region.error_reason = None
    region.processing_ms = None


def _summarize_job_regions(job: JobPipelineContext) -> dict[str, int]:
    """현재 job의 영역 결과 개수를 집계한다."""
    completed_count = sum(1 for region in job.regions if region.status == "completed")
    failed_count = sum(1 for region in job.regions if region.status == "failed")
    exportable_count = sum(1 for region in job.regions if _is_region_exportable(region))
    return {
        "completed_count": completed_count,
        "failed_count": failed_count,
        "exportable_count": exportable_count,
    }


def _build_job_last_error(job: JobPipelineContext) -> str | None:
    """실패한 영역 중 마지막 오류 메시지를 job 에러로 반영한다."""
    failed_regions = [region for region in job.regions if region.status == "failed" and region.error_reason]
    return failed_regions[-1].error_reason if failed_regions else None


def _select_export_image_field(region: RegionPipelineContext) -> str | None:
    """문서 내보내기에 사용할 이미지 경로 필드를 우선순위대로 고른다."""
    for field_name in ("styled_image_url", "image_crop_url", "png_rendered_url", "crop_url"):
        if getattr(region.figure, field_name):
            return field_name
    return None


def _finalize_region_status(region: RegionPipelineContext) -> None:
    """최종 텍스트 보유 여부에 따라 영역 성공 여부를 결정한다."""
    if _is_region_exportable(region):
        region.status = "completed"
        region.success = True
        return
    region.status = "failed"
    region.success = False
    region.error_reason = region.error_reason or "텍스트 또는 해설을 생성하지 못했습니다."


def _save_region_progress(user: PipelineUserContext, job: JobPipelineContext) -> None:
    """단계별 진행 상황을 저장소에 즉시 반영한다."""
    save_job(user, job)


def _process_region(
    user: PipelineUserContext,
    job: JobPipelineContext,
    region: RegionPipelineContext,
    *,
    image_path: Path,
    outputs_dir: Path,
    repository: PipelineRepository,
    api_key: str | None,
    do_ocr: bool,
    do_image_stylize: bool,
    do_explanation: bool,
    nano_banana_model: str | None,
    nano_banana_prompt_version: str,
    executed_action_flags: dict[str, bool],
) -> None:
    """단일 영역의 OCR, 해설, 이미지 생성을 순차 처리한다."""
    started = time.perf_counter()
    region_id = region.context.id
    crop_path = outputs_dir / f"{region_id}_crop.png"
    image_crop_path = outputs_dir / f"{region_id}_image_crop.png"
    styled_image_path = outputs_dir / f"{region_id}_styled.png"

    try:
        crop_bytes = crop_region_image(image_path, region.context.polygon, crop_path)
        crop_storage_path = f"{user.user_id}/{job.job_id}/outputs/{region_id}_crop.png"
        repository.upload_bytes(user, crop_storage_path, crop_bytes, "image/png")
        region.figure.crop_url = crop_storage_path
        _save_region_progress(user, job)

        analyzed = analyze_region_with_gpt(
            ROOT,
            crop_bytes,
            region.context.type,
            api_key=api_key,
            include_ocr=do_ocr,
            include_image_detection=do_image_stylize,
        )
        if do_ocr:
            region.extractor.ocr_text = (analyzed.get("ocr_text") or "") or None
            region.extractor.mathml = (analyzed.get("mathml") or "") or None
            region.extractor.problem_markdown = bridge_legacy_markup_to_markdown(region.extractor.ocr_text)
            _sync_region_markdown_version(region)
            executed_action_flags["ocr"] = True
        region.extractor.model_used = analyzed.get("model_used")
        region.extractor.openai_request_id = analyzed.get("openai_request_id")
        _save_region_progress(user, job)

        if do_explanation:
            try:
                explanation = generate_explanation_with_gpt(
                    ROOT,
                    crop_bytes,
                    region.extractor.ocr_text or "",
                    region.extractor.mathml or "",
                    api_key=api_key,
                )
            except Exception:
                explanation = "연습장에 풀이를 기록하세요."
            region.extractor.explanation = explanation or None
            region.extractor.explanation_markdown = bridge_legacy_markup_to_markdown(region.extractor.explanation)
            _sync_region_markdown_version(region)
            executed_action_flags["explanation"] = True
            _save_region_progress(user, job)

        if do_image_stylize:
            _process_region_image(
                user=user,
                job=job,
                region=region,
                crop_bytes=crop_bytes,
                image_crop_path=image_crop_path,
                styled_image_path=styled_image_path,
                repository=repository,
                analyzed=analyzed,
                nano_banana_model=nano_banana_model,
                nano_banana_prompt_version=nano_banana_prompt_version,
                executed_action_flags=executed_action_flags,
            )
    except Exception as error:
        region.error_reason = str(error)
    finally:
        region.processing_ms = int((time.perf_counter() - started) * 1000)
        _finalize_region_status(region)
        _save_region_progress(user, job)


def _process_region_image(
    *,
    user: PipelineUserContext,
    job: JobPipelineContext,
    region: RegionPipelineContext,
    crop_bytes: bytes,
    image_crop_path: Path,
    styled_image_path: Path,
    repository: PipelineRepository,
    analyzed: dict[str, Any],
    nano_banana_model: str | None,
    nano_banana_prompt_version: str,
    executed_action_flags: dict[str, bool],
) -> None:
    """영역 안의 시각 요소를 크롭하고 스타일 이미지를 생성한다."""
    image_bbox = analyzed.get("image_bbox")
    if not analyzed.get("has_stylizable_image") or not image_bbox:
        return

    try:
        region_id = region.context.id
        image_crop_bytes = crop_image_bytes(crop_bytes, image_bbox, image_crop_path)
        image_crop_storage_path = f"{user.user_id}/{job.job_id}/outputs/{region_id}_image_crop.png"
        repository.upload_bytes(user, image_crop_storage_path, image_crop_bytes, "image/png")
        region.figure.image_crop_url = image_crop_storage_path
        _save_region_progress(user, job)

        styled_image_bytes = generate_styled_image_with_nano_banana(
            ROOT,
            image_crop_bytes,
            model_name=nano_banana_model,
            prompt_kind=analyzed.get("image_kind") or "generic",
            prompt_version=nano_banana_prompt_version,
        )
        styled_image_path.write_bytes(styled_image_bytes)
        styled_image_storage_path = f"{user.user_id}/{job.job_id}/outputs/{region_id}_styled.png"
        repository.upload_bytes(user, styled_image_storage_path, styled_image_bytes, "image/png")
        region.figure.styled_image_url = styled_image_storage_path
        region.figure.styled_image_model = nano_banana_model
        executed_action_flags["image_stylize"] = True
        _save_region_progress(user, job)
    except Exception as error:
        region.error_reason = str(error)


def run_pipeline(
    user: PipelineUserContext,
    job_id: str,
    *,
    api_key: str | None = None,
    processing_type: str = "service_api",
    do_ocr: bool = True,
    do_image_stylize: bool = True,
    do_explanation: bool = True,
    nano_banana_model: str | None = None,
    nano_banana_prompt_version: str = "csat_v1",
) -> dict:
    """선택된 OCR/이미지 생성/해설 작업을 수행하고 결과를 저장한다."""
    repository = _get_repository()
    job = read_job(user, job_id)
    if not job.regions:
        raise ValueError("regions not set")

    job.processing_type = processing_type
    job.status = "running"
    job.last_error = None
    for region in job.regions:
        if _should_skip_region(region):
            continue
        _reset_region_outputs(
            region,
            do_ocr=do_ocr,
            do_image_stylize=do_image_stylize,
            do_explanation=do_explanation,
        )
    save_job(user, job)

    executed_action_flags = {
        "ocr": False,
        "image_stylize": False,
        "explanation": False,
    }

    with tempfile.TemporaryDirectory() as tempdir_str:
        temp_root = Path(tempdir_str)
        image_path = _materialize_input_image(user, repository, job, temp_root)

        for region in job.regions:
            if _should_skip_region(region):
                continue
            outputs_dir = temp_root / "outputs"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            _process_region(
                user,
                job,
                region,
                image_path=image_path,
                outputs_dir=outputs_dir,
                repository=repository,
                api_key=api_key,
                do_ocr=do_ocr,
                do_image_stylize=do_image_stylize,
                do_explanation=do_explanation,
                nano_banana_model=nano_banana_model,
                nano_banana_prompt_version=nano_banana_prompt_version,
                executed_action_flags=executed_action_flags,
            )

    summary = _summarize_job_regions(job)
    job.status = "failed" if summary["failed_count"] else "completed"
    job.last_error = _build_job_last_error(job)
    save_job(user, job)
    executed_actions = [
        action
        for action in ("ocr", "image_stylize", "explanation")
        if executed_action_flags[action]
    ]
    return {
        "job_id": job_id,
        "status": job.status,
        "executed_actions": executed_actions,
        **summary,
    }


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
        selected_field = _select_export_image_field(region)
        if selected_field is None:
            continue
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
    if not any(_is_region_exportable(region) for region in job.regions):
        raise ValueError("no exportable regions available for export")

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
