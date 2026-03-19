from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import Body, Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from app import pipeline
from app.auth import AuthenticatedUser, require_authenticated_user
from app.billing import BillingProfile, build_billing_service
from app.config import get_settings
from app.supabase import SupabaseApiError

app = FastAPI(title="Math Region OCR MVP API", version="0.1.0")
ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)
SCHEMA_MISMATCH_DETAIL = "배포 DB 스키마가 최신이 아닙니다."
STORAGE_FAILURE_DETAIL = "서버 저장소 연결에 실패했습니다. 잠시 후 다시 시도하세요."
USER_OPENAI_KEY_CONFIG_DETAIL = "사용자 OpenAI 키 설정이 완료되지 않았습니다."
IMAGE_PIPELINE_CONFIG_DETAIL = "이미지 생성 서버 설정이 완료되지 않았습니다."


def _get_allowed_origins() -> list[str]:
    """환경설정 기준으로 허용할 프런트 origin 목록을 계산한다."""
    settings = get_settings(ROOT)
    if settings.cors_allow_origins:
        return list(settings.cors_allow_origins)
    if settings.app_url:
        return [settings.app_url]
    return []

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Region(BaseModel):
    id: str
    polygon: list[list[float]] = Field(min_length=4)
    type: Literal["text", "diagram", "mixed"]
    order: int = Field(default=1, ge=1)

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[list[float]]) -> list[list[float]]:
        """영역 polygon 포맷을 검증한다."""
        if len(value) < 4:
            raise ValueError("polygon must contain at least 4 points")
        for point in value:
            if len(point) != 2:
                raise ValueError("each point must have exactly two coordinates")
        return value


class RegionSetRequest(BaseModel):
    regions: list[Region]


class RegionResult(BaseModel):
    id: str
    status: Literal["pending", "running", "completed", "failed"]
    polygon: list[list[float]] = Field(default_factory=list)
    type: Literal["text", "diagram", "mixed"] | None = None
    order: int = 1
    ocr_text: str | None = None
    explanation: str | None = None
    mathml: str | None = None
    svg_url: str | None = None
    crop_url: str | None = None
    image_crop_url: str | None = None
    styled_image_url: str | None = None
    styled_image_model: str | None = None
    processing_ms: int | None = None
    success: bool | None = None
    error_reason: str | None = None
    model_used: str | None = None
    openai_request_id: str | None = None
    edited_svg_url: str | None = None
    edited_svg_version: int | None = None
    was_charged: bool = False
    ocr_charged: bool = False
    image_charged: bool = False
    explanation_charged: bool = False
    charged_at: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: Literal["created", "regions_pending", "queued", "running", "completed", "failed", "exported"]
    file_name: str | None = None
    image_url: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    regions: list[RegionResult] = Field(default_factory=list)
    last_error: str | None = None
    hwpx_export_path: str | None = None


class RunJobResponse(BaseModel):
    job_id: str
    status: Literal["completed", "failed"]
    executed_actions: list[Literal["ocr", "image_stylize", "explanation"]] = Field(default_factory=list)
    charged_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    exportable_count: int = 0


class EditedSvgRequest(BaseModel):
    svg: str


class RunJobRequest(BaseModel):
    do_ocr: bool = True
    do_image_stylize: bool = True
    do_explanation: bool = True


def _collect_selected_actions(run_request: RunJobRequest) -> list[Literal["ocr", "image_stylize", "explanation"]]:
    """실행 요청에서 사용자가 선택한 액션 목록을 순서대로 추린다."""
    selected_actions: list[Literal["ocr", "image_stylize", "explanation"]] = []
    if run_request.do_ocr:
        selected_actions.append("ocr")
    if run_request.do_image_stylize:
        selected_actions.append("image_stylize")
    if run_request.do_explanation:
        selected_actions.append("explanation")
    return selected_actions


class CheckoutSessionRequest(BaseModel):
    plan_id: Literal["single", "starter", "pro"]
    success_url: str
    cancel_url: str


class BillingProfileResponse(BaseModel):
    credits_balance: int
    used_credits: int
    openai_connected: bool
    openai_key_masked: str | None = None


class OpenAiKeyRequest(BaseModel):
    api_key: str


def _signed_asset_url(current_user: AuthenticatedUser, storage_path: str | None) -> str | None:
    """Storage 내부 경로를 짧은 signed URL로 바꾼다."""
    return pipeline.create_asset_url(current_user, storage_path)


def _get_billing_service(require_polar: bool = False):
    """현재 환경설정으로 BillingService를 생성한다."""
    try:
        return build_billing_service(require_polar=require_polar)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _is_schema_mismatch_message(message: str) -> bool:
    """Supabase 에러 문자열이 스키마 드리프트인지 판별한다."""
    normalized = message.lower()
    schema_tokens = (
        "schema cache",
        "does not exist",
        "violates check constraint",
        "check constraint",
        "credit_ledger_reason_check",
        "ocr_charged",
        "image_charged",
        "explanation_charged",
        "image_crop_path",
        "styled_image_path",
        "styled_image_model",
    )
    return any(token in normalized for token in schema_tokens)


def _map_runtime_value_error(error: ValueError) -> HTTPException | None:
    """설정 누락 성격의 ValueError를 안정적인 HTTP 에러로 변환한다."""
    normalized = str(error).lower()
    if "openai_key_encryption_secret" in normalized:
        return HTTPException(status_code=500, detail=USER_OPENAI_KEY_CONFIG_DETAIL)
    if "nano_banana_" in normalized or "google-genai package is required" in normalized:
        return HTTPException(status_code=500, detail=IMAGE_PIPELINE_CONFIG_DETAIL)
    if "supabase" in normalized and "not configured" in normalized:
        return HTTPException(status_code=503, detail=STORAGE_FAILURE_DETAIL)
    return None


def _raise_runtime_http_error(error: Exception) -> None:
    """런타임 인프라 예외를 사용자용 HTTP 오류로 정규화한다."""
    if isinstance(error, SupabaseApiError):
        logger.exception("Supabase runtime error: %s", error)
        if _is_schema_mismatch_message(str(error)):
            raise HTTPException(status_code=500, detail=SCHEMA_MISMATCH_DETAIL) from error
        raise HTTPException(status_code=503, detail=STORAGE_FAILURE_DETAIL) from error

    if isinstance(error, ValueError):
        mapped_error = _map_runtime_value_error(error)
        if mapped_error is not None:
            raise mapped_error from error


def _map_job_response(current_user: AuthenticatedUser, job) -> JobResponse:
    """파이프라인 컨텍스트를 프런트 응답 모델로 바꾼다."""
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        file_name=job.file_name,
        image_url=_signed_asset_url(current_user, job.image_url),
        image_width=job.image_width,
        image_height=job.image_height,
        last_error=job.last_error,
        hwpx_export_path=job.hwpx_export_path,
        regions=[
            RegionResult(
                id=region.context.id,
                status=region.status,
                polygon=region.context.polygon,
                type=region.context.type,
                order=region.context.order,
                ocr_text=region.extractor.ocr_text,
                explanation=region.extractor.explanation,
                mathml=region.extractor.mathml,
                svg_url=_signed_asset_url(current_user, region.figure.svg_url),
                crop_url=_signed_asset_url(current_user, region.figure.crop_url),
                image_crop_url=_signed_asset_url(current_user, region.figure.image_crop_url),
                styled_image_url=_signed_asset_url(current_user, region.figure.styled_image_url),
                styled_image_model=region.figure.styled_image_model,
                processing_ms=region.processing_ms,
                success=region.success,
                error_reason=region.error_reason,
                model_used=region.extractor.model_used,
                openai_request_id=region.extractor.openai_request_id,
                edited_svg_url=_signed_asset_url(current_user, region.figure.edited_svg_url),
                edited_svg_version=region.figure.edited_svg_version,
                was_charged=region.was_charged,
                ocr_charged=region.ocr_charged,
                image_charged=region.image_charged,
                explanation_charged=region.explanation_charged,
                charged_at=region.charged_at,
            )
            for region in job.regions
        ],
    )


def _map_billing_profile(profile: BillingProfile) -> BillingProfileResponse:
    """Billing profile을 응답 모델로 변환한다."""
    return BillingProfileResponse(
        credits_balance=profile.credits_balance,
        used_credits=profile.used_credits,
        openai_connected=profile.openai_connected,
        openai_key_masked=profile.openai_key_masked,
    )


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    image: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> JobResponse:
    """원본 이미지를 업로드하고 초기 job을 생성한다."""
    content = await image.read()
    job = pipeline.create_job_from_bytes(current_user, image.filename or "uploaded_image", content)
    return _map_job_response(current_user, job)


@app.put("/jobs/{job_id}/regions")
def save_regions(
    job_id: str,
    payload: RegionSetRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """사용자 지정 영역 목록을 저장한다."""
    try:
        return pipeline.save_regions(current_user, job_id, [region.model_dump() for region in payload.regions])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except SupabaseApiError as error:
        _raise_runtime_http_error(error)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/jobs/{job_id}/run", response_model=RunJobResponse)
def run_pipeline(
    job_id: str,
    payload: RunJobRequest | None = Body(default=None),
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """OCR 파이프라인을 실행한다."""
    try:
        run_request = payload or RunJobRequest()
        selected_actions = _collect_selected_actions(run_request)
        if not selected_actions:
            raise ValueError("at least one action must be selected")

        billing_service = _get_billing_service()
        openai_key = billing_service.resolve_openai_api_key(current_user)
        billing_service.ensure_job_action_credits_available(
            current_user,
            job_id,
            selected_actions,
            processing_type=openai_key.processing_type,
        )
        result = pipeline.run_pipeline(
            current_user,
            job_id,
            api_key=openai_key.api_key,
            processing_type=openai_key.processing_type,
            do_ocr=run_request.do_ocr,
            do_image_stylize=run_request.do_image_stylize,
            do_explanation=run_request.do_explanation,
            nano_banana_model=get_settings(ROOT).nano_banana_model,
            nano_banana_prompt_version=get_settings(ROOT).nano_banana_prompt_version,
        )
        charge_result = {"charged_count": 0}
        if result.get("status") in ("completed", "failed", "exported"):
            charge_result = billing_service.consume_job_action_credits(
                current_user,
                job_id,
                list(result.get("executed_actions") or []),
                processing_type=openai_key.processing_type,
            )
        return {
            **result,
            "charged_count": int(charge_result.get("charged_count") or len(charge_result.get("charged_actions") or [])),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except SupabaseApiError as error:
        _raise_runtime_http_error(error)
    except ValueError as error:
        _raise_runtime_http_error(error)
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> JobResponse:
    """DB와 Storage 상태를 합쳐 job 상세 응답을 반환한다."""
    try:
        job = pipeline.read_job(current_user, job_id)
        return _map_job_response(current_user, job)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except SupabaseApiError as error:
        _raise_runtime_http_error(error)
    except ValueError as error:
        _raise_runtime_http_error(error)
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/jobs/{job_id}/regions/{region_id}/svg")
def get_region_svg(
    job_id: str,
    region_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """편집기용 SVG 원문을 반환한다."""
    try:
        return pipeline.get_region_svg(current_user, job_id, region_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.put("/jobs/{job_id}/regions/{region_id}/svg/edited")
def save_edited_svg(
    job_id: str,
    region_id: str,
    payload: EditedSvgRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """편집된 SVG를 저장하고 최신 signed URL을 반환한다."""
    try:
        result = pipeline.save_edited_svg(current_user, job_id, region_id, payload.svg)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {
        "region_id": result["region_id"],
        "edited_svg_url": _signed_asset_url(current_user, result["edited_svg_url"]),
        "edited_svg_version": result["edited_svg_version"],
    }


@app.post("/jobs/{job_id}/export/hwpx")
def export_hwpx(
    job_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """HWPX 내보내기를 실행하고 다운로드 엔드포인트를 반환한다."""
    try:
        pipeline.execute_hwpx_export(current_user, job_id)
        return {"download_url": f"/jobs/{job_id}/export/hwpx/download"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/billing/profile", response_model=BillingProfileResponse)
def get_billing_profile(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> BillingProfileResponse:
    """현재 로그인 사용자의 크레딧 상태를 반환한다."""
    profile = _get_billing_service().get_profile(current_user)
    return _map_billing_profile(profile)


@app.put("/billing/openai-key", response_model=BillingProfileResponse)
def save_openai_key(
    payload: OpenAiKeyRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> BillingProfileResponse:
    """사용자 OpenAI key를 암호화 저장하고 연결 상태를 갱신한다."""
    try:
        profile = _get_billing_service().save_openai_key(current_user, payload.api_key)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _map_billing_profile(profile)


@app.delete("/billing/openai-key", response_model=BillingProfileResponse)
def delete_openai_key(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> BillingProfileResponse:
    """사용자 OpenAI key 연결을 해제하고 profile 상태를 갱신한다."""
    try:
        profile = _get_billing_service().delete_openai_key(current_user)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _map_billing_profile(profile)


@app.get("/billing/catalog")
def get_billing_catalog() -> dict:
    """현재 결제 가능한 고정 플랜 목록을 반환한다."""
    try:
        return {"plans": _get_billing_service(require_polar=True).list_plans()}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/billing/checkout")
@app.post("/billing/checkout-session")
def create_checkout(
    payload: CheckoutSessionRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """Polar checkout 세션을 만들고 리다이렉트 URL을 반환한다."""
    try:
        return _get_billing_service(require_polar=True).create_checkout(
            current_user,
            plan_id=payload.plan_id,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/billing/checkout/{checkout_id}")
@app.get("/billing/checkout-session/{checkout_id}")
def get_checkout_status(
    checkout_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """Polar checkout 상태와 내부 적립 상태를 조회한다."""
    try:
        return _get_billing_service(require_polar=True).get_checkout(checkout_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/billing/portal")
def get_customer_portal(
    return_url: str | None = None,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> dict:
    """Polar customer portal URL을 생성한다."""
    try:
        return _get_billing_service(require_polar=True).create_customer_portal(
            current_user,
            return_url=return_url,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/billing/webhooks/polar")
@app.post("/billing/webhook")
async def polar_webhook(
    request: Request,
    webhook_id: str | None = Header(default=None, alias="webhook-id"),
    webhook_signature: str | None = Header(default=None, alias="webhook-signature"),
    webhook_timestamp: str | None = Header(default=None, alias="webhook-timestamp"),
) -> dict:
    """Polar webhook을 검증하고 크레딧 적립을 반영한다."""
    payload = await request.body()
    try:
        service = _get_billing_service(require_polar=True)
        event = service.verify_webhook(
            payload,
            {
                "webhook-id": webhook_id or "",
                "webhook-signature": webhook_signature or "",
                "webhook-timestamp": webhook_timestamp or "",
            },
        )
        return service.apply_webhook_event(event)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"unexpected webhook error: {error}")


@app.get("/jobs/{job_id}/export/hwpx/download")
def download_hwpx(
    job_id: str,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> Response:
    """저장된 HWPX를 내려준다."""
    try:
        job = pipeline.read_job(current_user, job_id)
        if not job.hwpx_export_path:
            pipeline.execute_hwpx_export(current_user, job_id)
            job = pipeline.read_job(current_user, job_id)
        if not job.hwpx_export_path:
            raise HTTPException(status_code=404, detail="exported hwpx not found")

        content = pipeline.download_asset_bytes(current_user, job.hwpx_export_path)
        return Response(
            content=content,
            media_type="application/hwp+zip",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.hwpx"'},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
