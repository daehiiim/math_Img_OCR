from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app import pipeline
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "runtime" / "jobs"

app = FastAPI(title="Math Region OCR MVP API", version="0.1.0")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://0.0.0.0:5173,http://localhost:4173,http://127.0.0.1:4173,http://0.0.0.0:4173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNTIME_DIR.parent.mkdir(parents=True, exist_ok=True)
app.mount("/runtime", StaticFiles(directory=ROOT / "runtime"), name="runtime")


class Region(BaseModel):
    id: str
    polygon: list[list[float]] = Field(min_length=4)
    type: Literal["text", "diagram", "mixed"]
    order: int = Field(default=1, ge=1)

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) < 4:
            raise ValueError("polygon must contain at least 4 points")
        for pt in value:
            if len(pt) != 2:
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
    processing_ms: int | None = None
    success: bool | None = None
    error_reason: str | None = None
    model_used: str | None = None
    openai_request_id: str | None = None
    edited_svg_url: str | None = None
    edited_svg_version: int | None = None


class JobResponse(BaseModel):
    job_id: str
    status: Literal["created", "regions_pending", "queued", "running", "completed", "failed"]
    file_name: str | None = None
    image_url: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    regions: list[RegionResult] = Field(default_factory=list)


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(image: UploadFile = File(...)) -> JobResponse:
    content = await image.read()
    job = pipeline.create_job_from_bytes(image.filename or "uploaded_image", content)
    
    # Map back to UI schema
    return JobResponse(
         job_id=job.job_id,
         status=job.status,
         file_name=job.file_name,
         image_url=job.image_url,
         image_width=job.image_width,
         image_height=job.image_height,
         regions=[]
    )


@app.put("/jobs/{job_id}/regions")
def save_regions(job_id: str, payload: RegionSetRequest) -> dict:
    try:
        return pipeline.save_regions(job_id, [r.model_dump() for r in payload.regions])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/jobs/{job_id}/run")
def run_pipeline(job_id: str) -> dict:
    try:
        return pipeline.run_pipeline(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    try:
        job = pipeline.read_job(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
        
    regions = []
    for r in job.regions:
         regions.append(RegionResult(
             id=r.context.id,
             status=r.status,
             polygon=r.context.polygon,
             type=r.context.type,
             order=r.context.order,
             ocr_text=r.extractor.ocr_text,
             explanation=r.extractor.explanation,
             mathml=r.extractor.mathml,
             svg_url=r.figure.svg_url,
             crop_url=r.figure.crop_url,
             processing_ms=r.processing_ms,
             success=r.success,
             error_reason=r.error_reason,
             edited_svg_url=r.figure.edited_svg_url,
             edited_svg_version=r.figure.edited_svg_version
         ))
         
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        file_name=job.file_name,
        image_url=job.image_url,
        image_width=job.image_width,
        image_height=job.image_height,
        regions=regions
    )



class EditedSvgRequest(BaseModel):
    svg: str


@app.get("/jobs/{job_id}/regions/{region_id}/svg")
def get_region_svg(job_id: str, region_id: str) -> dict:
    try:
        return pipeline.get_region_svg(job_id, region_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

@app.put("/jobs/{job_id}/regions/{region_id}/svg/edited")
def save_edited_svg(job_id: str, region_id: str, payload: EditedSvgRequest) -> dict:
    try:
        return pipeline.save_edited_svg(job_id, region_id, payload.svg)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/jobs/{job_id}/export/hwpx")
def export_hwpx(job_id: str) -> dict:
    try:
        return pipeline.execute_hwpx_export(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"unexpected export error: {error}")


@app.get("/jobs/{job_id}/export/hwpx/download")
def download_hwpx(job_id: str) -> FileResponse:
    print("HIT download_hwpx", job_id)
    try:
        result = pipeline.execute_hwpx_export(job_id)
        path = ROOT / result["download_url"]
        if not path.exists():
            raise HTTPException(status_code=404, detail="exported hwpx not found")
        return FileResponse(
            path=path,
            media_type="application/hwp+zip",
            filename=f"{job_id}.hwpx",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
