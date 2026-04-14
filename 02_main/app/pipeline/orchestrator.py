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
    build_detection_image_source,
    crop_image_bytes,
    crop_region_image,
    normalize_svg_xml,
    preprocess_auto_full_ocr_image,
    read_image_size,
    render_svg_to_png,
    sanitize_svg,
)
from app.pipeline.hwpx_reference_renderer import normalize_choice_value, parse_problem_text
from app.pipeline.markdown_contract import (
    MARKDOWN_VERSION,
    bridge_legacy_markup_to_markdown,
    has_markdown_output,
    markdown_to_hwp_legacy_markup,
    ordered_segments_to_markdown,
)
from app.pipeline.region_detector import (
    AutoDetectRegionsResult,
    DetectedRegionCandidate,
    detect_problem_regions_with_gpt,
)
from app.pipeline.region_refiner import (
    RefinedAutoDetectResult,
    RefinedRegionCandidate,
    refine_detected_regions,
)
from app.pipeline.repository import PipelineRepository, PipelineUserContext, build_repository_from_settings
from app.pipeline.schema import JobPipelineContext, RegionContext, RegionPipelineContext

ROOT = Path(__file__).resolve().parents[2]
_repository_factory: Callable[[], PipelineRepository] | None = None
EXPLANATION_VERIFICATION_WARNING_TEXT = "해설 검증이 필요합니다. 정답과 풀이의 일치 여부를 자동 확인하지 못했습니다."
EXPORT_RUNTIME_MISSING_DETAIL = "문서 생성 엔진이 준비되지 않았습니다. 관리자에게 문의하세요."
EXPORT_APPLY_FAILED_DETAIL = "텍스트 추출은 완료됐지만 문서 양식 적용에 실패했습니다. Markdown 결과는 저장되어 있으니 다시 내보내기 하세요."
AUTO_DETECT_FAILURE_DETAIL = "AI가 문항 경계를 안정적으로 찾지 못했습니다. 박스를 확인하거나 직접 수정해 주세요."


def _coerce_ordered_segments(raw_segments: Any) -> list[dict[str, Any]]:
    """저장/응답에 안전한 ordered segment 사전 목록으로 정리한다."""
    if not isinstance(raw_segments, list):
        return []
    segments: list[dict[str, Any]] = []
    for fallback_order, raw_segment in enumerate(raw_segments):
        if not isinstance(raw_segment, dict):
            continue
        segment_type = raw_segment.get("type")
        if segment_type not in ("text", "math"):
            continue
        try:
            source_order = int(raw_segment.get("source_order"))
        except (TypeError, ValueError):
            source_order = fallback_order
        segments.append(
            {
                "type": segment_type,
                "content": str(raw_segment.get("content") or ""),
                "source_order": source_order,
            }
        )
    return sorted(segments, key=lambda segment: segment["source_order"])


def _clear_ocr_outputs(region: RegionPipelineContext) -> None:
    """OCR 재실행 전 원문/문항 메타데이터를 초기화한다."""
    region.extractor.ocr_text = None
    region.extractor.mathml = None
    region.extractor.problem_markdown = None
    region.extractor.raw_transcript = None
    region.extractor.ordered_segments = []
    region.extractor.question_type = None
    region.extractor.parsed_choices = []


def _clear_explanation_outputs(region: RegionPipelineContext) -> None:
    """해설 재실행 전 검증 메타데이터와 해설 산출물을 초기화한다."""
    region.extractor.explanation = None
    region.extractor.explanation_markdown = None
    region.extractor.resolved_answer_index = None
    region.extractor.resolved_answer_value = None
    region.extractor.answer_confidence = None
    region.extractor.verification_status = None
    region.extractor.verification_warnings = []
    region.extractor.reason_summary = None


def _coerce_answer_index(value: Any) -> int | None:
    """모델이 반환한 정답 번호를 1 이상 정수로 정규화한다."""
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return None
    return resolved if resolved > 0 else None


def _normalize_explanation_payload(result: Any) -> dict[str, Any]:
    """구형 문자열 해설과 신형 구조화 해설을 공통 payload로 맞춘다."""
    if not isinstance(result, dict):
        text = str(result or "").strip()
        lines = [
            bridge_legacy_markup_to_markdown(line.strip()) or line.strip()
            for line in text.splitlines()
            if line.strip()
        ]
        return {
            "explanation_lines": lines,
            "final_answer_index": None,
            "final_answer_value": None,
            "confidence": None,
            "reason_summary": None,
        }
    lines = result.get("explanation_lines")
    normalized_lines = [
        bridge_legacy_markup_to_markdown(str(line).strip()) or str(line).strip()
        for line in lines or []
        if str(line).strip()
    ]
    confidence = result.get("confidence")
    return {
        "explanation_lines": normalized_lines,
        "final_answer_index": _coerce_answer_index(result.get("final_answer_index")),
        "final_answer_value": (
            bridge_legacy_markup_to_markdown(str(result.get("final_answer_value") or "").strip())
            or str(result.get("final_answer_value") or "").strip()
            or None
        ),
        "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
        "reason_summary": str(result.get("reason_summary") or "").strip() or None,
    }


def _store_problem_metadata(region: RegionPipelineContext, analyzed: dict[str, Any]) -> None:
    """OCR 결과를 region extractor 필드와 객관식 메타데이터에 반영한다."""
    ordered_segments = _coerce_ordered_segments(analyzed.get("ordered_segments"))
    region.extractor.ocr_text = (analyzed.get("ocr_text") or "") or None
    region.extractor.mathml = (analyzed.get("mathml") or "") or None
    region.extractor.raw_transcript = (analyzed.get("raw_transcript") or "") or None
    region.extractor.ordered_segments = ordered_segments
    problem_markdown = ordered_segments_to_markdown(ordered_segments)
    if not problem_markdown:
        problem_markdown = bridge_legacy_markup_to_markdown(region.extractor.raw_transcript or region.extractor.ocr_text)
    region.extractor.problem_markdown = problem_markdown
    problem_parse_source = markdown_to_hwp_legacy_markup(problem_markdown) if problem_markdown else (region.extractor.ocr_text or "")
    parsed_problem = parse_problem_text(problem_parse_source or "")
    region.extractor.question_type = "multiple_choice" if parsed_problem.choices is not None else "free_response"
    region.extractor.parsed_choices = list(parsed_problem.choices or ())


def _resolve_multiple_choice_warnings(
    choices: list[str],
    answer_index: int | None,
    answer_value: str | None,
) -> list[str]:
    """객관식 정답 번호/값 충돌 여부를 경고 목록으로 계산한다."""
    warnings: list[str] = []
    normalized_answer_value = normalize_choice_value(answer_value) if answer_value else None
    matched_indexes = [index + 1 for index, choice in enumerate(choices) if choice == normalized_answer_value]
    if not choices:
        warnings.append("객관식 보기를 복원하지 못했습니다.")
    if answer_index is not None and not 1 <= answer_index <= len(choices):
        warnings.append("해설 최종 답 번호가 보기 범위를 벗어났습니다.")
    if normalized_answer_value and not matched_indexes:
        warnings.append("해설 최종 답 값이 선택지와 일치하지 않습니다.")
    if answer_index is not None and matched_indexes and answer_index not in matched_indexes:
        warnings.append("해설 최종 답 번호와 선택지 값이 서로 일치하지 않습니다.")
    if answer_index is None and normalized_answer_value is None:
        warnings.append("해설에서 객관식 정답을 확정하지 못했습니다.")
    if answer_index is None and len(matched_indexes) > 1:
        warnings.append("동일한 보기 값이 여러 개라 자동 검증을 확정하지 못했습니다.")
    return warnings


def _store_explanation_metadata(region: RegionPipelineContext, explanation_result: Any) -> None:
    """해설 구조화 응답을 저장하고 객관식이면 일치 여부를 검증한다."""
    payload = _normalize_explanation_payload(explanation_result)
    explanation_markdown = "\n".join(payload["explanation_lines"]).strip() or None
    explanation_text = markdown_to_hwp_legacy_markup(explanation_markdown) if explanation_markdown else None
    region.extractor.resolved_answer_index = payload["final_answer_index"]
    region.extractor.resolved_answer_value = payload["final_answer_value"]
    region.extractor.answer_confidence = payload["confidence"]
    region.extractor.reason_summary = payload["reason_summary"]
    region.extractor.verification_warnings = []
    if region.extractor.question_type == "multiple_choice":
        region.extractor.verification_warnings = _resolve_multiple_choice_warnings(
            region.extractor.parsed_choices,
            region.extractor.resolved_answer_index,
            region.extractor.resolved_answer_value,
        )
        region.extractor.verification_status = "warning" if region.extractor.verification_warnings else "verified"
        if region.extractor.verification_status == "warning":
            explanation_text = EXPLANATION_VERIFICATION_WARNING_TEXT
            explanation_markdown = EXPLANATION_VERIFICATION_WARNING_TEXT
    else:
        region.extractor.verification_status = "verified" if explanation_markdown else "unverified"
    region.extractor.explanation = explanation_text or None
    region.extractor.explanation_markdown = explanation_markdown


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


def _build_region_polygon(left: int, top: int, right: int, bottom: int) -> list[list[int]]:
    """좌상단/우하단 좌표를 사각형 polygon으로 변환한다."""
    return [[left, top], [right, top], [right, bottom], [left, bottom]]


def _build_region_context(raw_region: dict[str, Any]) -> RegionContext:
    """입력 payload를 저장 가능한 RegionContext로 정규화한다."""
    return RegionContext(
        id=raw_region["id"],
        polygon=raw_region["polygon"],
        type=raw_region.get("type") or "mixed",
        order=int(raw_region.get("order", 1)),
        selection_mode=raw_region.get("selection_mode") or "manual",
        input_device=raw_region.get("input_device"),
        warning_level=raw_region.get("warning_level") or "normal",
        auto_detect_confidence=raw_region.get("auto_detect_confidence"),
    )


def _uses_auto_full_selection(region: RegionPipelineContext) -> bool:
    """현재 영역이 시스템 자동 전체 인식 fallback 인지 판단한다."""
    return region.context.selection_mode == "auto_full"


def _build_auto_detect_region_id(candidate: RefinedRegionCandidate, fallback_order: int) -> str:
    """감지된 문항 번호가 있으면 우선 사용하고 없으면 순번 기반 ID를 만든다."""
    if candidate.detected_question_number:
        return f"q{candidate.detected_question_number}"
    return f"q{fallback_order}"


def _build_auto_detect_warning_level(
    candidate: RefinedRegionCandidate,
) -> str:
    """refiner가 계산한 최종 위험도를 저장용 warning level로 반환한다."""
    return candidate.warning_level


def _build_auto_detect_region(
    candidate: RefinedRegionCandidate,
    *,
    fallback_order: int,
) -> RegionPipelineContext:
    """자동 분할 후보를 저장 가능한 region 컨텍스트로 변환한다."""
    left, top, right, bottom = candidate.bbox
    return RegionPipelineContext(
        context=RegionContext(
            id=_build_auto_detect_region_id(candidate, fallback_order),
            polygon=_build_region_polygon(left, top, right, bottom),
            type="mixed",
            order=fallback_order,
            selection_mode="auto_detected",
            input_device="system",
            warning_level=_build_auto_detect_warning_level(candidate),
            auto_detect_confidence=candidate.confidence,
        )
    )


def _build_auto_detect_regions(result: RefinedAutoDetectResult) -> list[RegionPipelineContext]:
    """자동 분할 응답을 region 목록으로 정규화한다."""
    return [
        _build_auto_detect_region(candidate, fallback_order=index + 1)
        for index, candidate in enumerate(result.regions)
    ]


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

        region_context = _build_region_context(raw_region)
        regions.append(RegionPipelineContext(context=region_context))

    job.regions = regions
    job.status = "queued" if regions else "regions_pending"
    job.last_error = None
    save_job(user, job)
    return {"message": "regions saved", "count": len(regions)}


def auto_detect_regions(
    user: PipelineUserContext,
    job_id: str,
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """원본 페이지에서 문항 단위 영역을 자동 분할해 저장한다."""
    repository = _get_repository()
    job = read_job(user, job_id)
    image_bytes = repository.download_bytes(user, job.image_url)
    detection_source = build_detection_image_source(image_bytes)
    coarse_result = detect_problem_regions_with_gpt(
        ROOT,
        detection_source.image_bytes,
        image_width=max(1, int(detection_source.width or job.image_width or 0)),
        image_height=max(1, int(detection_source.height or job.image_height or 0)),
        api_key=api_key,
    )
    refined_result = refine_detected_regions(
        detection_source.image_bytes,
        image_width=max(1, int(detection_source.width or job.image_width or 0)),
        image_height=max(1, int(detection_source.height or job.image_height or 0)),
        candidates=coarse_result.regions,
        detector_review_required=coarse_result.review_required,
    )
    regions = _build_auto_detect_regions(refined_result)
    if not regions:
        raise ValueError(AUTO_DETECT_FAILURE_DETAIL)
    job.image_width = detection_source.width
    job.image_height = detection_source.height
    job.regions = regions
    job.status = "queued"
    job.last_error = None
    save_job(user, job)
    return {
        "regions": job.regions,
        "detected_count": len(job.regions),
        "review_required": refined_result.review_required,
        "detector_model": coarse_result.detector_model,
        "detection_version": coarse_result.detection_version,
        "openai_request_id": coarse_result.openai_request_id,
    }


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
        _clear_ocr_outputs(region)
        _clear_explanation_outputs(region)
    if do_explanation:
        _clear_explanation_outputs(region)
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
        analysis_input_bytes = crop_bytes
        if _uses_auto_full_selection(region):
            analysis_input_bytes = preprocess_auto_full_ocr_image(
                crop_bytes,
                preserve_geometry=do_image_stylize,
            )
        crop_storage_path = f"{user.user_id}/{job.job_id}/outputs/{region_id}_crop.png"
        repository.upload_bytes(user, crop_storage_path, crop_bytes, "image/png")
        region.figure.crop_url = crop_storage_path
        _save_region_progress(user, job)

        analyzed = analyze_region_with_gpt(
            ROOT,
            analysis_input_bytes,
            region.context.type,
            api_key=api_key,
            include_ocr=do_ocr,
            include_image_detection=do_image_stylize,
        )
        if do_ocr:
            _store_problem_metadata(region, analyzed)
            _sync_region_markdown_version(region)
            executed_action_flags["ocr"] = True
        region.extractor.model_used = analyzed.get("model_used")
        region.extractor.openai_request_id = analyzed.get("openai_request_id")
        _save_region_progress(user, job)

        if do_explanation:
            try:
                explanation = generate_explanation_with_gpt(
                    ROOT,
                    analysis_input_bytes,
                    region.extractor.ocr_text or "",
                    region.extractor.mathml or "",
                    api_key=api_key,
                )
            except Exception:
                explanation = "연습장에 풀이를 기록하세요."
            _store_explanation_metadata(region, explanation)
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
        raise ValueError("먼저 AI 자동 분할 또는 수동 영역 지정을 완료해 주세요.")

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


def _is_runtime_missing_export_error(message: str) -> bool:
    """export 실패 문자열이 runtime 누락 계열인지 판별한다."""
    normalized = message.lower()
    return "runtime not found" in normalized or "template runtime missing" in normalized or "hwpx export runtime" in normalized


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
    except ValueError as error:
        message = str(error)
        if _is_runtime_missing_export_error(message):
            raise ValueError(EXPORT_RUNTIME_MISSING_DETAIL) from error
        raise ValueError(message if message in (EXPORT_RUNTIME_MISSING_DETAIL, EXPORT_APPLY_FAILED_DETAIL) else EXPORT_APPLY_FAILED_DETAIL) from error
    except Exception as error:
        if _is_runtime_missing_export_error(str(error)):
            raise ValueError(EXPORT_RUNTIME_MISSING_DETAIL) from error
        raise ValueError(EXPORT_APPLY_FAILED_DETAIL) from error

    job.status = "exported"
    job.hwpx_export_path = storage_path
    save_job(user, job)
    return {"download_url": storage_path}
