from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from app import core

app = FastAPI(title="Math Region OCR MVP API", version="0.1.0")


class Region(BaseModel):
    id: str
    polygon: list[list[float]] = Field(min_length=4)
    type: Literal["text", "diagram", "mixed"]
    order: int = Field(default=1, ge=1)

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, value: list[list[float]]) -> list[list[float]]:
        core.validate_polygon(value)
        return value


class RegionSetRequest(BaseModel):
    regions: list[Region]


class RegionResult(BaseModel):
    id: str
    status: Literal["pending", "running", "completed", "failed"]
    ocr_text: str | None = None
    svg_url: str | None = None
    crop_url: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: Literal["created", "regions_pending", "queued", "running", "completed", "failed"]
    image_url: str | None = None
    regions: list[RegionResult] = Field(default_factory=list)


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(image: UploadFile = File(...)) -> JobResponse:
    content = await image.read()
    job = core.create_job_from_bytes(image.filename or "uploaded_image", content)
    return JobResponse(**job)


@app.put("/jobs/{job_id}/regions")
def save_regions(job_id: str, payload: RegionSetRequest) -> dict:
    try:
        return core.save_regions(job_id, [r.model_dump() for r in payload.regions])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")


@app.post("/jobs/{job_id}/run")
def run_pipeline(job_id: str) -> dict:
    try:
        return core.run_pipeline(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    try:
        job = core.read_job(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(**job)


@app.post("/jobs/{job_id}/export/hwpx")
def export_hwpx(job_id: str) -> dict:
    try:
        return core.export_hwpx(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
