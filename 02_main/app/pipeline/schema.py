from typing import Literal, Optional, List
from pydantic import BaseModel, Field

RegionType = Literal["text", "diagram", "mixed"]

class RegionContext(BaseModel):
    id: str
    polygon: List[List[float]]
    type: RegionType
    order: int
    
class ExtractorContext(BaseModel):
    ocr_text: Optional[str] = None
    explanation: Optional[str] = None
    mathml: Optional[str] = None
    model_used: Optional[str] = None
    openai_request_id: Optional[str] = None

class FigureContext(BaseModel):
    svg_url: Optional[str] = None
    crop_url: Optional[str] = None
    edited_svg_url: Optional[str] = None
    edited_svg_version: int = 0
    png_rendered_url: Optional[str] = None # When SVG is rendered to PNG for doc export

class RegionPipelineContext(BaseModel):
    context: RegionContext
    extractor: ExtractorContext = Field(default_factory=ExtractorContext)
    figure: FigureContext = Field(default_factory=FigureContext)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    success: Optional[bool] = None
    error_reason: Optional[str] = None
    processing_ms: Optional[int] = None
    
class JobPipelineContext(BaseModel):
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
