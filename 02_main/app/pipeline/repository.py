from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Protocol

from app.auth import AuthenticatedUser
from app.config import get_settings
from app.schema_compat import (
    is_markdown_output_schema_error,
    is_region_metadata_schema_error,
    remember_markdown_output_columns_available,
    remember_region_metadata_columns_available,
    should_use_region_metadata_columns,
    should_use_markdown_output_columns,
    strip_markdown_output_fields,
    strip_region_metadata_fields,
)
from app.pipeline.schema import (
    ExtractorContext,
    FigureContext,
    JobPipelineContext,
    RegionContext,
    RegionPipelineContext,
)
from app.supabase import SupabaseClient, SupabaseConfig

PipelineUserContext = AuthenticatedUser
_REGION_BASE_SELECT_COLUMNS = (
    "region_key",
    "polygon",
    "region_type",
    "region_order",
    "status",
    "ocr_text",
    "explanation",
    "mathml",
    "model_used",
    "openai_request_id",
    "svg_path",
    "edited_svg_path",
    "edited_svg_version",
    "crop_path",
    "image_crop_path",
    "styled_image_path",
    "styled_image_model",
    "png_rendered_path",
    "processing_ms",
    "error_reason",
    "was_charged",
    "ocr_charged",
    "image_charged",
    "explanation_charged",
    "charged_at",
)
_REGION_MARKDOWN_COLUMNS = (
    "problem_markdown",
    "explanation_markdown",
    "markdown_version",
    "raw_transcript",
    "ordered_segments",
    "question_type",
    "parsed_choices",
    "resolved_answer_index",
    "resolved_answer_value",
    "answer_confidence",
    "verification_status",
    "verification_warnings",
    "reason_summary",
)
_REGION_METADATA_COLUMNS = (
    "selection_mode",
    "input_device",
    "warning_level",
    "auto_detect_confidence",
)


class PipelineRepository(Protocol):
    """파이프라인이 기대하는 영구 저장 계약이다."""

    def create_job(
        self,
        user: PipelineUserContext,
        filename: str,
        content: bytes,
        image_width: int,
        image_height: int,
    ) -> JobPipelineContext: ...

    def read_job(self, user: PipelineUserContext, job_id: str) -> JobPipelineContext: ...

    def save_job(self, user: PipelineUserContext, job: JobPipelineContext) -> None: ...

    def upload_bytes(
        self,
        user: PipelineUserContext,
        storage_path: str,
        content: bytes,
        content_type: str,
    ) -> None: ...

    def download_bytes(self, user: PipelineUserContext, storage_path: str) -> bytes: ...

    def download_text(self, user: PipelineUserContext, storage_path: str) -> str: ...

    def create_signed_url(
        self,
        user: PipelineUserContext,
        storage_path: str,
        expires_in: int = 3600,
    ) -> str: ...


def _sanitize_filename(filename: str) -> str:
    """업로드 파일명을 안전한 basename으로 정리한다."""
    candidate = Path(filename or "uploaded_image").name.strip()
    return candidate or "uploaded_image"


def _guess_content_type(path_value: str, fallback: str) -> str:
    """파일명 확장자로 MIME 타입을 추정한다."""
    guessed, _ = mimetypes.guess_type(path_value)
    return guessed or fallback


def _build_region_select(include_markdown_output: bool, include_region_metadata: bool) -> str:
    """region 조회 컬럼 목록을 현재 스키마 호환 수준에 맞게 만든다."""
    columns = list(_REGION_BASE_SELECT_COLUMNS)
    if include_region_metadata:
        columns.extend(_REGION_METADATA_COLUMNS)
    if include_markdown_output:
        columns[8:8] = list(_REGION_MARKDOWN_COLUMNS)
    return ",".join(columns)


class SupabasePipelineRepository:
    """OCR 파이프라인 데이터를 Supabase DB와 Storage에 저장한다."""

    def __init__(self, root_path: Path) -> None:
        settings = get_settings(root_path)
        if not settings.auth.supabase_url or not settings.auth.supabase_anon_key:
            raise ValueError("Supabase REST settings are not configured")

        self._config = SupabaseConfig(
            url=settings.auth.supabase_url,
            anon_key=settings.auth.supabase_anon_key,
            storage_bucket=settings.auth.supabase_storage_bucket or "ocr-assets",
        )

    def _client(self, user: PipelineUserContext) -> SupabaseClient:
        """사용자 JWT가 포함된 Supabase 클라이언트를 만든다."""
        return SupabaseClient(self._config, user.access_token)

    def _map_region_row(self, row: dict) -> RegionPipelineContext:
        """영역 row를 파이프라인 컨텍스트로 변환한다."""
        status = row.get("status") or "pending"
        return RegionPipelineContext(
            context=RegionContext(
                id=str(row["region_key"]),
                polygon=row.get("polygon") or [],
                type=row.get("region_type") or "mixed",
                order=int(row.get("region_order") or 1),
                selection_mode=row.get("selection_mode") or "manual",
                input_device=row.get("input_device"),
                warning_level=row.get("warning_level") or "normal",
                auto_detect_confidence=row.get("auto_detect_confidence"),
            ),
            extractor=ExtractorContext(
                ocr_text=row.get("ocr_text"),
                explanation=row.get("explanation"),
                mathml=row.get("mathml"),
                problem_markdown=row.get("problem_markdown"),
                explanation_markdown=row.get("explanation_markdown"),
                markdown_version=row.get("markdown_version"),
                raw_transcript=row.get("raw_transcript"),
                ordered_segments=row.get("ordered_segments") or [],
                question_type=row.get("question_type"),
                parsed_choices=row.get("parsed_choices") or [],
                resolved_answer_index=row.get("resolved_answer_index"),
                resolved_answer_value=row.get("resolved_answer_value"),
                answer_confidence=row.get("answer_confidence"),
                verification_status=row.get("verification_status"),
                verification_warnings=row.get("verification_warnings") or [],
                reason_summary=row.get("reason_summary"),
                model_used=row.get("model_used"),
                openai_request_id=row.get("openai_request_id"),
            ),
            figure=FigureContext(
                svg_url=row.get("svg_path"),
                crop_url=row.get("crop_path"),
                image_crop_url=row.get("image_crop_path"),
                styled_image_url=row.get("styled_image_path"),
                styled_image_model=row.get("styled_image_model"),
                edited_svg_url=row.get("edited_svg_path"),
                edited_svg_version=int(row.get("edited_svg_version") or 0),
                png_rendered_url=row.get("png_rendered_path"),
            ),
            status=status,
            success=(status == "completed") if row.get("status") is not None else None,
            error_reason=row.get("error_reason"),
            processing_ms=row.get("processing_ms"),
            was_charged=bool(row.get("was_charged") or False),
            ocr_charged=bool(row.get("ocr_charged") or False),
            image_charged=bool(row.get("image_charged") or False),
            explanation_charged=bool(row.get("explanation_charged") or False),
            charged_at=row.get("charged_at"),
        )

    def _build_region_payload(self, job: JobPipelineContext) -> list[dict[str, object]]:
        """영역 목록을 upsert payload로 변환한다."""
        payloads = [
            {
                "job_id": job.job_id,
                "region_key": region.context.id,
                "polygon": region.context.polygon,
                "region_type": region.context.type,
                "region_order": region.context.order,
                "selection_mode": region.context.selection_mode,
                "input_device": region.context.input_device,
                "warning_level": region.context.warning_level,
                "auto_detect_confidence": region.context.auto_detect_confidence,
                "status": region.status,
                "ocr_text": region.extractor.ocr_text,
                "explanation": region.extractor.explanation,
                "mathml": region.extractor.mathml,
                "problem_markdown": region.extractor.problem_markdown,
                "explanation_markdown": region.extractor.explanation_markdown,
                "markdown_version": region.extractor.markdown_version,
                "raw_transcript": region.extractor.raw_transcript,
                "ordered_segments": list(region.extractor.ordered_segments or []),
                "question_type": region.extractor.question_type,
                "parsed_choices": list(region.extractor.parsed_choices or []),
                "resolved_answer_index": region.extractor.resolved_answer_index,
                "resolved_answer_value": region.extractor.resolved_answer_value,
                "answer_confidence": region.extractor.answer_confidence,
                "verification_status": region.extractor.verification_status,
                "verification_warnings": list(region.extractor.verification_warnings or []),
                "reason_summary": region.extractor.reason_summary,
                "model_used": region.extractor.model_used,
                "openai_request_id": region.extractor.openai_request_id,
                "svg_path": region.figure.svg_url,
                "edited_svg_path": region.figure.edited_svg_url,
                "edited_svg_version": region.figure.edited_svg_version,
                "crop_path": region.figure.crop_url,
                "image_crop_path": region.figure.image_crop_url,
                "styled_image_path": region.figure.styled_image_url,
                "styled_image_model": region.figure.styled_image_model,
                "png_rendered_path": region.figure.png_rendered_url,
                "processing_ms": region.processing_ms,
                "error_reason": region.error_reason,
                "was_charged": region.was_charged,
                "ocr_charged": region.ocr_charged,
                "image_charged": region.image_charged,
                "explanation_charged": region.explanation_charged,
                "charged_at": region.charged_at,
            }
            for region in job.regions
        ]
        return payloads

    def _read_region_rows(self, client: SupabaseClient, job_id: str) -> list[dict]:
        """job region row를 현재 배포 스키마에 맞는 컬럼 집합으로 읽는다."""
        params = {
            "job_id": f"eq.{job_id}",
            "order": "region_order.asc",
        }
        include_markdown_output = should_use_markdown_output_columns()
        include_region_metadata = should_use_region_metadata_columns()

        while True:
            try:
                rows = client.select(
                    "ocr_job_regions",
                    params={
                        **params,
                        "select": _build_region_select(include_markdown_output, include_region_metadata),
                    },
                )
                if include_markdown_output:
                    remember_markdown_output_columns_available(True)
                if include_region_metadata:
                    remember_region_metadata_columns_available(True)
                return rows
            except Exception as error:
                if include_region_metadata and is_region_metadata_schema_error(error):
                    remember_region_metadata_columns_available(False)
                    include_region_metadata = False
                    continue
                if include_markdown_output and is_markdown_output_schema_error(error):
                    remember_markdown_output_columns_available(False)
                    include_markdown_output = False
                    continue
                raise

    def _upsert_region_rows(self, client: SupabaseClient, job: JobPipelineContext) -> None:
        """job region upsert를 현재 배포 스키마에 맞는 payload로 수행한다."""
        payload = self._build_region_payload(job)
        include_markdown_output = should_use_markdown_output_columns()
        include_region_metadata = should_use_region_metadata_columns()

        while True:
            current_payload = payload
            if not include_markdown_output:
                current_payload = [strip_markdown_output_fields(row) for row in current_payload]
            if not include_region_metadata:
                current_payload = [strip_region_metadata_fields(row) for row in current_payload]
            try:
                client.upsert("ocr_job_regions", payload=current_payload, on_conflict="job_id,region_key")
                if include_markdown_output:
                    remember_markdown_output_columns_available(True)
                if include_region_metadata:
                    remember_region_metadata_columns_available(True)
                return
            except Exception as error:
                if include_region_metadata and is_region_metadata_schema_error(error):
                    remember_region_metadata_columns_available(False)
                    include_region_metadata = False
                    continue
                if include_markdown_output and is_markdown_output_schema_error(error):
                    remember_markdown_output_columns_available(False)
                    include_markdown_output = False
                    continue
                raise

    def create_job(
        self,
        user: PipelineUserContext,
        filename: str,
        content: bytes,
        image_width: int,
        image_height: int,
    ) -> JobPipelineContext:
        """원본 이미지를 업로드하고 ocr_jobs row를 만든다."""
        from app.pipeline.orchestrator import _utc_now
        import uuid

        safe_name = _sanitize_filename(filename)
        job_id = str(uuid.uuid4())
        image_path = f"{user.user_id}/{job_id}/input/{safe_name}"
        now = _utc_now()

        self.upload_bytes(user, image_path, content, _guess_content_type(safe_name, "application/octet-stream"))
        self._client(user).insert(
            "ocr_jobs",
            {
                "id": job_id,
                "user_id": user.user_id,
                "file_name": safe_name,
                "source_image_path": image_path,
                "image_width": image_width,
                "image_height": image_height,
                "processing_type": "service_api",
                "status": "regions_pending",
                "was_charged": False,
                "last_error": None,
                "hwpx_export_path": None,
            },
        )

        return JobPipelineContext(
            job_id=job_id,
            file_name=safe_name,
            image_url=image_path,
            image_width=image_width,
            image_height=image_height,
            processing_type="service_api",
            status="regions_pending",
            created_at=now,
            updated_at=now,
        )

    def read_job(self, user: PipelineUserContext, job_id: str) -> JobPipelineContext:
        """DB row와 region row를 읽어 파이프라인 컨텍스트로 조립한다."""
        client = self._client(user)
        job_rows = client.select(
            "ocr_jobs",
            params={
                "select": "id,file_name,source_image_path,image_width,image_height,processing_type,status,last_error,hwpx_export_path,created_at,updated_at",
                "id": f"eq.{job_id}",
            },
        )
        if not job_rows:
            raise FileNotFoundError(f"job not found: {job_id}")

        region_rows = self._read_region_rows(client, job_id)

        job_row = job_rows[0]
        regions = [self._map_region_row(row) for row in region_rows]

        return JobPipelineContext(
            job_id=str(job_row["id"]),
            file_name=str(job_row.get("file_name") or "uploaded_image"),
            image_url=str(job_row.get("source_image_path") or ""),
            image_width=int(job_row.get("image_width") or 0),
            image_height=int(job_row.get("image_height") or 0),
            processing_type=job_row.get("processing_type") or "service_api",
            status=job_row.get("status") or "created",
            regions=regions,
            created_at=str(job_row.get("created_at")),
            updated_at=str(job_row.get("updated_at")),
            last_error=job_row.get("last_error"),
            hwpx_export_path=job_row.get("hwpx_export_path"),
        )

    def save_job(self, user: PipelineUserContext, job: JobPipelineContext) -> None:
        """Job 전체 상태와 region 목록을 DB에 동기화한다."""
        client = self._client(user)
        client.update(
            "ocr_jobs",
            filters={"id": f"eq.{job.job_id}"},
            payload={
                "file_name": job.file_name,
                "source_image_path": job.image_url,
                "image_width": job.image_width,
                "image_height": job.image_height,
                "processing_type": job.processing_type,
                "status": job.status,
                "last_error": job.last_error,
                "hwpx_export_path": job.hwpx_export_path,
            },
        )

        existing_rows = client.select(
            "ocr_job_regions",
            params={"select": "region_key", "job_id": f"eq.{job.job_id}"},
        )
        existing_keys = {str(row["region_key"]) for row in existing_rows}
        current_keys = {region.context.id for region in job.regions}
        for stale_key in sorted(existing_keys - current_keys):
            client.delete(
                "ocr_job_regions",
                filters={
                    "job_id": f"eq.{job.job_id}",
                    "region_key": f"eq.{stale_key}",
                },
            )

        if not job.regions:
            return

        self._upsert_region_rows(client, job)

    def upload_bytes(
        self,
        user: PipelineUserContext,
        storage_path: str,
        content: bytes,
        content_type: str,
    ) -> None:
        """Storage에 바이트를 저장한다."""
        self._client(user).upload_bytes(storage_path, content, content_type)

    def download_bytes(self, user: PipelineUserContext, storage_path: str) -> bytes:
        """Storage에서 바이트를 읽는다."""
        return self._client(user).download_bytes(storage_path)

    def download_text(self, user: PipelineUserContext, storage_path: str) -> str:
        """Storage에서 UTF-8 텍스트를 읽는다."""
        return self.download_bytes(user, storage_path).decode("utf-8")

    def create_signed_url(
        self,
        user: PipelineUserContext,
        storage_path: str,
        expires_in: int = 3600,
    ) -> str:
        """Storage object의 presigned URL을 생성한다."""
        return self._client(user).create_signed_url(storage_path, expires_in=expires_in)


def build_repository_from_settings(root_path: Path) -> PipelineRepository:
    """환경설정에 맞는 기본 저장소 구현체를 반환한다."""
    return SupabasePipelineRepository(root_path)
