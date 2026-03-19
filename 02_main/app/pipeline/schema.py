from typing import List, Literal, Optional

from pydantic import BaseModel, Field

RegionType = Literal["text", "diagram", "mixed"]


class RegionContext(BaseModel):
    """사용자가 지정한 영역 메타데이터를 보관한다."""

    id: str
    polygon: List[List[float]]
    type: RegionType
    order: int


class ExtractorContext(BaseModel):
    """OCR과 해설 생성 결과를 보관한다."""

    ocr_text: Optional[str] = None
    explanation: Optional[str] = None
    mathml: Optional[str] = None
    model_used: Optional[str] = None
    openai_request_id: Optional[str] = None


class FigureContext(BaseModel):
    """도형 및 이미지 산출물 경로를 보관한다."""

    svg_url: Optional[str] = None
    crop_url: Optional[str] = None
    image_crop_url: Optional[str] = None
    styled_image_url: Optional[str] = None
    styled_image_model: Optional[str] = None
    edited_svg_url: Optional[str] = None
    edited_svg_version: int = 0
    png_rendered_url: Optional[str] = None


class RegionPipelineContext(BaseModel):
    """영역별 처리 상태와 과금 상태를 함께 저장한다."""

    context: RegionContext
    extractor: ExtractorContext = Field(default_factory=ExtractorContext)
    figure: FigureContext = Field(default_factory=FigureContext)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    success: Optional[bool] = None
    error_reason: Optional[str] = None
    processing_ms: Optional[int] = None
    was_charged: bool = False
    ocr_charged: bool = False
    image_charged: bool = False
    explanation_charged: bool = False
    charged_at: Optional[str] = None


class JobPipelineContext(BaseModel):
    """작업 전체 상태와 영역 목록을 저장한다."""

    job_id: str
    file_name: str = "uploaded_image"
    image_url: str
    image_width: int = 0
    image_height: int = 0
    processing_type: Literal["user_api_key", "service_api"] = "service_api"
    status: Literal["created", "regions_pending", "queued", "running", "completed", "failed", "exported"]
    regions: List[RegionPipelineContext] = Field(default_factory=list)
    created_at: str
    updated_at: str
    last_error: Optional[str] = None
    hwpx_export_path: Optional[str] = None
