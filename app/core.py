from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "runtime" / "jobs"
TEMPLATE_PATH = ROOT / "templates" / "hwpx" / "problem_block_template.xml"

JobStatus = Literal["created", "regions_pending", "queued", "running", "completed", "failed"]
RegionStatus = Literal["pending", "running", "completed", "failed"]
RegionType = Literal["text", "diagram", "mixed"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_dir(job_id: str) -> Path:
    return RUNTIME_DIR / job_id


def _job_json(job_id: str) -> Path:
    return _job_dir(job_id) / "job.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_job(job_id: str) -> dict:
    path = _job_json(job_id)
    if not path.exists():
        raise FileNotFoundError(f"job not found: {job_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_job(job_id: str, data: dict) -> None:
    data["updated_at"] = _utc_now()
    _write_json(_job_json(job_id), data)


def validate_polygon(polygon: list[list[float]]) -> None:
    if len(polygon) < 4:
        raise ValueError("polygon must contain at least 4 points")
    for pt in polygon:
        if len(pt) != 2:
            raise ValueError("each point must have exactly two coordinates")


def _build_mock_svg(region_id: str, region_type: RegionType, polygon: list[list[float]]) -> str:
    points = " ".join([f"{x},{y}" for x, y in polygon])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200">\n'
        f'  <polygon points="{points}" fill="none" stroke="#222" stroke-width="3"/>\n'
        f'  <text x="20" y="40" font-size="28">Region: {region_id} ({region_type})</text>\n'
        "</svg>\n"
    )


def create_job_from_bytes(filename: str, content: bytes) -> dict:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    input_dir = _job_dir(job_id) / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    safe_name = filename or "uploaded_image"
    image_path = input_dir / safe_name
    image_path.write_bytes(content)

    job = {
        "job_id": job_id,
        "status": "regions_pending",
        "image_url": str(image_path.relative_to(ROOT)),
        "regions": [],
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    save_job(job_id, job)
    return job


def save_regions(job_id: str, regions: list[dict]) -> dict:
    job = read_job(job_id)
    normalized = []
    for region in regions:
        polygon = region["polygon"]
        validate_polygon(polygon)
        normalized.append(
            {
                "id": region["id"],
                "status": "pending",
                "type": region["type"],
                "order": int(region.get("order", 1)),
                "polygon": polygon,
            }
        )

    job["regions"] = normalized
    job["status"] = "queued"
    save_job(job_id, job)
    return {"message": "regions saved", "count": len(normalized)}


def run_pipeline(job_id: str) -> dict:
    job = read_job(job_id)
    if not job.get("regions"):
        raise ValueError("regions not set")

    outputs_dir = _job_dir(job_id) / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    job["status"] = "running"
    for region in job["regions"]:
        region["status"] = "running"
    save_job(job_id, job)

    for region in job["regions"]:
        txt_path = outputs_dir / f"{region['id']}.txt"
        svg_path = outputs_dir / f"{region['id']}.svg"
        crop_path = outputs_dir / f"{region['id']}_crop.txt"

        ocr_text = f"[MOCK OCR] {region['id']} 영역 텍스트"
        txt_path.write_text(ocr_text, encoding="utf-8")
        svg_path.write_text(
            _build_mock_svg(region["id"], region["type"], region["polygon"]),
            encoding="utf-8",
        )
        crop_path.write_text("mock crop placeholder", encoding="utf-8")

        region["status"] = "completed"
        region["ocr_text"] = ocr_text
        region["svg_url"] = str(svg_path.relative_to(ROOT))
        region["crop_url"] = str(crop_path.relative_to(ROOT))

    job["status"] = "completed"
    save_job(job_id, job)
    return {"job_id": job_id, "status": "completed"}


def export_hwpx(job_id: str) -> dict:
    job = read_job(job_id)
    if job.get("status") != "completed":
        raise ValueError("job is not completed")

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
