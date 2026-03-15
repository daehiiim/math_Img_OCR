import shutil
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import pipeline
from app.main import get_job


def make_png_bytes(width: int = 32, height: int = 24) -> bytes:
    image = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def cleanup_job(job_id: str) -> None:
    runtime_job_dir = Path(__file__).resolve().parents[1] / "runtime" / "jobs" / job_id
    if runtime_job_dir.exists():
        shutil.rmtree(runtime_job_dir)


def test_create_job_persists_image_metadata():
    job = pipeline.create_job_from_bytes("sample.png", make_png_bytes())

    try:
        assert job.file_name == "sample.png"
        assert job.image_width == 32
        assert job.image_height == 24
    finally:
        cleanup_job(job.job_id)


def test_get_job_returns_region_context_fields():
    job = pipeline.create_job_from_bytes("region-sample.png", make_png_bytes())

    try:
        polygon = [[1, 2], [21, 2], [21, 12], [1, 12]]
        pipeline.save_regions(
            job.job_id,
            [
                {
                    "id": "q1",
                    "polygon": polygon,
                    "type": "diagram",
                    "order": 2,
                }
            ],
        )

        response = get_job(job.job_id)

        assert response.file_name == "region-sample.png"
        assert response.image_width == 32
        assert response.image_height == 24
        assert response.regions[0].type == "diagram"
        assert response.regions[0].order == 2
        assert response.regions[0].polygon == polygon
    finally:
        cleanup_job(job.job_id)
