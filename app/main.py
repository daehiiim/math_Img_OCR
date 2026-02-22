from __future__ import annotations

from typing import Literal
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

from app import core
ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "runtime" / "jobs"
TEMPLATE_PATH = ROOT / "templates" / "hwpx" / "problem_block_template.xml"

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
def _job_dir(job_id: str) -> Path:
    return RUNTIME_DIR / job_id


def _job_json(job_id: str) -> Path:
    return _job_dir(job_id) / "job.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_job(job_id: str) -> dict:
    path = _job_json(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="job not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_job(job_id: str, data: dict) -> None:
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(_job_json(job_id), data)


def _build_mock_svg(region: Region) -> str:
    points = " ".join([f"{x},{y}" for x, y in region.polygon])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200">\n'
        f'  <polygon points="{points}" fill="none" stroke="#222" stroke-width="3"/>\n'
        f'  <text x="20" y="40" font-size="28">Region: {region.id} ({region.type})</text>\n'
        "</svg>\n"
    )


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(image: UploadFile = File(...)) -> JobResponse:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job_dir = _job_dir(job_id)
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    filename = image.filename or "uploaded_image"
    image_path = input_dir / filename
    content = await image.read()
    image_path.write_bytes(content)

    job = {
        "job_id": job_id,
        "status": "regions_pending",
        "image_url": str(image_path.relative_to(ROOT)),
        "regions": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_job(job_id, job)
    return JobResponse(**job)


@app.put("/jobs/{job_id}/regions")
def save_regions(job_id: str, payload: RegionSetRequest) -> dict:
    try:
        return core.save_regions(job_id, [r.model_dump() for r in payload.regions])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    job = _read_job(job_id)
    regions = [
        {
            "id": r.id,
            "status": "pending",
            "type": r.type,
            "order": r.order,
            "polygon": r.polygon,
        }
        for r in payload.regions
    ]
    job["regions"] = regions
    job["status"] = "queued"
    _save_job(job_id, job)
    return {"message": "regions saved", "count": len(regions)}


@app.post("/jobs/{job_id}/run")
def run_pipeline(job_id: str) -> dict:
    try:
        return core.run_pipeline(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    job = _read_job(job_id)
    if not job.get("regions"):
        raise HTTPException(status_code=400, detail="regions not set")

    outputs_dir = _job_dir(job_id) / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    job["status"] = "running"
    for region in job["regions"]:
        region["status"] = "running"

    _save_job(job_id, job)

    for region in job["regions"]:
        region_model = Region(
            id=region["id"],
            polygon=region["polygon"],
            type=region["type"],
            order=region.get("order", 1),
        )
        txt_path = outputs_dir / f"{region_model.id}.txt"
        svg_path = outputs_dir / f"{region_model.id}.svg"
        crop_path = outputs_dir / f"{region_model.id}_crop.txt"

        ocr_text = f"[MOCK OCR] {region_model.id} 영역 텍스트"
        txt_path.write_text(ocr_text, encoding="utf-8")
        svg_path.write_text(_build_mock_svg(region_model), encoding="utf-8")
        crop_path.write_text("mock crop placeholder", encoding="utf-8")

        region["status"] = "completed"
        region["ocr_text"] = ocr_text
        region["svg_url"] = str(svg_path.relative_to(ROOT))
        region["crop_url"] = str(crop_path.relative_to(ROOT))

    job["status"] = "completed"
    _save_job(job_id, job)
    return {"job_id": job_id, "status": "completed"}


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    try:
        job = core.read_job(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    job = _read_job(job_id)
    return JobResponse(**job)


@app.post("/jobs/{job_id}/export/hwpx")
def export_hwpx(job_id: str) -> dict:
    try:
        return core.export_hwpx(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    job = _read_job(job_id)
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="job is not completed")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    export_dir = _job_dir(job_id) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    hwpx_path = export_dir / f"{job_id}.hwpx"

    with ZipFile(hwpx_path, "w") as zf:
        zf.writestr("mimetype", "application/haansoft-hwpx")
        for region in sorted(job["regions"], key=lambda x: x.get("order", 1)):
            block = (
                template.replace("{{problem_id}}", region["id"])
                .replace("{{problem_title}}", f"문제 {region.get('order', 1)}")
                .replace("{{ocr_text}}", region.get("ocr_text", ""))
                .replace("{{svg_path}}", region.get("svg_url", ""))
                .replace("{{crop_image_path}}", region.get("crop_url", ""))
                .replace("{{job_id}}", job_id)
                .replace("{{region_type}}", region.get("type", "mixed"))
            )
            zf.writestr(f"Contents/{region['id']}.xml", block)

    return {"download_url": str(hwpx_path.relative_to(ROOT))}
