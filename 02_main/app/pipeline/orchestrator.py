import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from app.pipeline.schema import (
    JobPipelineContext,
    RegionPipelineContext,
    RegionContext,
    ExtractorContext,
    FigureContext
)
from app.pipeline.extractor import analyze_region_with_gpt, generate_explanation_with_gpt
from app.pipeline.figure import crop_region_image, render_svg_to_png, build_mock_svg, sanitize_svg, normalize_svg_xml
from app.pipeline.exporter import export_hwpx

# It expects ROOT to be 2 levels up from app
ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "runtime" / "jobs"

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _job_dir(job_id: str) -> Path:
    return RUNTIME_DIR / job_id

def _job_json(job_id: str) -> Path:
    return _job_dir(job_id) / "job.json"

def read_job(job_id: str) -> JobPipelineContext:
    path = _job_json(job_id)
    print(f"[DEBUG] Reading job from: {path}")
    if not path.exists():
        print(f"[DEBUG] Job file not found: {path}")
        raise FileNotFoundError(f"job not found: {job_id}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        print(f"[DEBUG] Job file read successful. Length: {len(data)}")
        return JobPipelineContext.model_validate_json(data)
    except Exception as e:
        print(f"[DEBUG] Error reading job JSON: {e}")
        raise

def save_job(job: JobPipelineContext) -> None:
    job.updated_at = _utc_now()
    path = _job_json(job.job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(job.model_dump_json(indent=2))

def create_job_from_bytes(filename: str, content: bytes) -> JobPipelineContext:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    input_dir = _job_dir(job_id) / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    safe_name = filename or "uploaded_image"
    image_path = input_dir / safe_name
    image_path.write_bytes(content)

    job = JobPipelineContext(
        job_id=job_id,
        image_url=str(image_path.relative_to(ROOT)).replace("\\", "/"),
        status="regions_pending",
        created_at=_utc_now(),
        updated_at=_utc_now()
    )
    save_job(job)
    return job

def save_regions(job_id: str, regions_dict: List[Dict[str, Any]]) -> dict:
    job = read_job(job_id)
    regions = []
    
    for r in regions_dict:
        polygon = r["polygon"]
        if len(polygon) < 4:
            raise ValueError("polygon must contain at least 4 points")
            
        context = RegionContext(
            id=r["id"],
            polygon=polygon,
            type=r["type"],
            order=int(r.get("order", 1))
        )
        pipeline_context = RegionPipelineContext(context=context)
        regions.append(pipeline_context)
        
    job.regions = regions
    job.status = "queued"
    save_job(job)
    return {"message": "regions saved", "count": len(regions)}


def run_pipeline(job_id: str) -> dict:
    job = read_job(job_id)
    if not job.regions:
        raise ValueError("regions not set")

    outputs_dir = _job_dir(job_id) / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    image_path = ROOT / job.image_url
    if not image_path.exists():
        raise ValueError("job image file not found")

    job.status = "running"
    for r in job.regions:
        r.status = "running"
        r.error_reason = None
    save_job(job)

    any_failed = False

    for region in job.regions:
        started = time.perf_counter()
        
        region_id = region.context.id
        txt_path = outputs_dir / f"{region_id}.txt"
        explain_path = outputs_dir / f"{region_id}_explanation.txt"
        svg_path = outputs_dir / f"{region_id}.svg"
        crop_path = outputs_dir / f"{region_id}_crop.png"
        png_path = outputs_dir / f"{region_id}.png"

        try:
            crop_bytes = crop_region_image(image_path, region.context.polygon, crop_path)
            region.figure.crop_url = str(crop_path.relative_to(ROOT)).replace("\\", "/")
            
            analyzed = analyze_region_with_gpt(ROOT, crop_bytes, region.context.type)
            
            ocr_text = analyzed.get("ocr_text") or ""
            mathml = analyzed.get("mathml") or ""
            
            try:
                explanation = generate_explanation_with_gpt(ROOT, crop_bytes, ocr_text, mathml)
            except Exception:
                explanation = "연습장에 풀이를 기록하세요."
                
            txt_path.write_text(ocr_text, encoding="utf-8")
            explain_path.write_text(explanation, encoding="utf-8")
            
            svg_text = analyzed.get("diagram_svg") or build_mock_svg(region_id, region.context.type, region.context.polygon)
            svg_path.write_text(svg_text, encoding="utf-8")
            
            try:
                render_svg_to_png(svg_text, png_path)
                region.figure.png_rendered_url = str(png_path.relative_to(ROOT)).replace("\\", "/")
            except Exception as e:
                # Rendering might fail for complex or invalid SVGs
                print(f"Failed to render SVG to PNG: {e}")
                
            region.extractor.ocr_text = ocr_text
            region.extractor.explanation = explanation
            region.extractor.mathml = mathml
            region.figure.svg_url = str(svg_path.relative_to(ROOT)).replace("\\", "/")
            
            region.status = "completed"
            region.success = True
            region.error_reason = None
        except Exception as error:
            any_failed = True
            region.status = "failed"
            region.success = False
            region.error_reason = str(error)
        finally:
            region.processing_ms = int((time.perf_counter() - started) * 1000)
            
    job.status = "failed" if any_failed else "completed"
    save_job(job)
    return {"job_id": job_id, "status": job.status}


def get_region_svg(job_id: str, region_id: str) -> dict:
    job = read_job(job_id)
    region = next((r for r in job.regions if r.context.id == region_id), None)
    if region is None:
        raise ValueError("region not found")

    svg_rel = region.figure.edited_svg_url or region.figure.svg_url
    if not svg_rel:
        raise ValueError("svg not found")

    svg_path = ROOT / svg_rel
    if not svg_path.exists():
        raise ValueError("svg file not found")

    raw_svg = svg_path.read_text(encoding="utf-8")
    try:
        normalized_svg = normalize_svg_xml(raw_svg)
    except ValueError:
        normalized_svg = raw_svg

    return {
        "region_id": region_id,
        "svg": normalized_svg,
        "source": "edited" if region.figure.edited_svg_url else "original",
    }

def save_edited_svg(job_id: str, region_id: str, svg_text: str) -> dict:
    job = read_job(job_id)
    region = next((r for r in job.regions if r.context.id == region_id), None)
    if region is None:
        raise ValueError("region not found")
    if region.status != "completed":
        raise ValueError("region is not completed")

    cleaned = sanitize_svg(svg_text)

    outputs_dir = _job_dir(job_id) / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    current_version = region.figure.edited_svg_version
    next_version = current_version + 1
    edited_path = outputs_dir / f"{region_id}.edited.v{next_version}.svg"
    latest_path = outputs_dir / f"{region_id}.edited.latest.svg"

    edited_path.write_text(cleaned, encoding="utf-8")
    latest_path.write_text(cleaned, encoding="utf-8")
    
    # Needs to render to png again
    png_path = outputs_dir / f"{region_id}.png"
    try:
        render_svg_to_png(cleaned, png_path)
        region.figure.png_rendered_url = str(png_path.relative_to(ROOT)).replace("\\", "/")
    except Exception as e:
        print(f"Failed to render edited SVG to PNG: {e}")

    region.figure.edited_svg_url = str(latest_path.relative_to(ROOT)).replace("\\", "/")
    region.figure.edited_svg_version = next_version
    save_job(job)

    return {
        "region_id": region_id,
        "edited_svg_url": region.figure.edited_svg_url,
        "edited_svg_version": next_version,
    }


def execute_hwpx_export(job_id: str) -> dict:
    job = read_job(job_id)
    if job.status not in ("completed", "failed"):
        raise ValueError("job is not finished")

    export_dir = _job_dir(job_id) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    try:
        hwpx_path = export_hwpx(ROOT, job, export_dir)
    except Exception as error:
        raise ValueError(f"HWPX export failed: {error}") from error

    return {"download_url": str(hwpx_path.relative_to(ROOT)).replace("\\", "/")}
