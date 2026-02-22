import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from app.main import app, core
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, ROOT


client = TestClient(app)


def test_mvp1_flow():
def test_mvp1_flow(tmp_path):
    response = client.post(
        "/jobs",
        files={"image": ("sheet.png", b"fake-image-bytes", "image/png")},
    )
    assert response.status_code == 201
    job = response.json()
    job_id = job["job_id"]
    assert job["status"] == "regions_pending"

    payload = {
        "regions": [
            {
                "id": "q1",
                "polygon": [[10, 10], [100, 10], [100, 100], [10, 100]],
                "type": "mixed",
                "order": 1,
            }
        ]
    }
    response = client.put(f"/jobs/{job_id}/regions", json=payload)
    assert response.status_code == 200

    response = client.post(f"/jobs/{job_id}/run")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["regions"][0]["ocr_text"].startswith("[MOCK OCR]")

    response = client.post(f"/jobs/{job_id}/export/hwpx")
    assert response.status_code == 200
    rel_path = response.json()["download_url"]
    assert rel_path.endswith(".hwpx")
    assert (core.ROOT / rel_path).exists()
    assert (ROOT / rel_path).exists()


def test_run_without_regions_fails():
    response = client.post(
        "/jobs",
        files={"image": ("sheet.png", b"fake-image-bytes", "image/png")},
    )
    job_id = response.json()["job_id"]

    run_response = client.post(f"/jobs/{job_id}/run")
    assert run_response.status_code == 400
