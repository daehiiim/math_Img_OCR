import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw

# Add main project directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.orchestrator import (
    create_job_from_bytes,
    save_regions,
    run_pipeline,
    execute_hwpx_export,
    read_job
)

def create_dummy_image() -> bytes:
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50, 50), "Test Image for Smoke Test", fill=(0, 0, 0))
    
    # Save to memory
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def run_smoke_test():
    print("starting smoke test...")
    
    # 1. Create Job
    image_bytes = create_dummy_image()
    job = create_job_from_bytes("test_smoke.png", image_bytes)
    job_id = job.job_id
    print(f"job created: {job_id}")
    
    # 2. Add Regions
    regions = [
        {
            "id": "R1",
            "polygon": [[10, 10], [100, 10], [100, 100], [10, 100]],
            "type": "text",
            "order": 1
        },
        {
            "id": "R2",
            "polygon": [[120, 10], [300, 10], [300, 100], [120, 100]],
            "type": "diagram",
            "order": 2
        }
    ]
    save_regions(job_id, regions)
    print("regions saved")
    
    # 3. Run Pipeline
    print("running pipeline...")
    run_pipeline(job_id)
    
    # Check results
    updated_job = read_job(job_id)
    print(f"pipeline finished with status: {updated_job.status}")
    
    for r in updated_job.regions:
        print(f"  Region {r.context.id} status: {r.status}")
        
    if updated_job.status != 'completed':
        print("Pipeline did not complete fully. Warning!")
        
    # 4. Export HWPX
    print("exporting hwpx...")
    export_res = execute_hwpx_export(job_id)
    hwpx_rel_url = export_res["download_url"]
    print(f"HWPX created at relative url: {hwpx_rel_url}")
    
    # Validate HWPX size
    root = Path(__file__).resolve().parents[1]
    hwpx_path = root / hwpx_rel_url
    
    if not hwpx_path.exists():
        raise FileNotFoundError(f"exported file not found at {hwpx_path}")
        
    size = hwpx_path.stat().st_size
    print(f"HWPX file size: {size} bytes")
    if size < 100:
        raise ValueError("HWPX file is suspiciously small, might be empty!")
        
    print("Smoke test completed successfully!")

if __name__ == "__main__":
    run_smoke_test()
