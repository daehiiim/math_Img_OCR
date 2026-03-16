import copy
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.auth as auth_module
from app.auth import AuthenticatedUser, require_authenticated_user
from app.config import AppSettings, AuthSettings, BillingSettings
from app.main import app
from app.pipeline import orchestrator
from app.pipeline.schema import ExtractorContext, FigureContext, RegionContext, RegionPipelineContext
from tests.auth_test_utils import StubJwksResponse, build_es256_key_pair, build_es256_token
from tests.test_pipeline_storage import MemoryPipelineRepository, make_png_bytes


def install_memory_repository(monkeypatch) -> MemoryPipelineRepository:
    repository = MemoryPipelineRepository()
    monkeypatch.setattr(orchestrator, "_repository_factory", lambda: repository)
    return repository


def _build_auth_settings() -> AppSettings:
    """Jobs 인증 회귀 테스트용 최소 설정을 만든다."""
    return AppSettings(
        openai_api_key=None,
        database_url=None,
        auth=AuthSettings(
            supabase_url="https://jobs-auth.supabase.co",
            supabase_anon_key="anon-key",
            supabase_jwt_secret=None,
            supabase_storage_bucket="ocr-assets",
            supabase_service_role_key="service-role-key",
        ),
        billing=BillingSettings(
            polar_access_token=None,
            polar_webhook_secret=None,
            polar_server=None,
            polar_product_single_id=None,
            polar_product_starter_id=None,
            polar_product_pro_id=None,
        ),
    )


def test_get_job_returns_signed_asset_urls_and_region_context(monkeypatch):
    repository = install_memory_repository(monkeypatch)
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    job = orchestrator.create_job_from_bytes(user, "region-sample.png", make_png_bytes())
    region = RegionPipelineContext(
        context=RegionContext(
            id="q1",
            polygon=[[1, 2], [21, 2], [21, 12], [1, 12]],
            type="diagram",
            order=2,
        ),
        extractor=ExtractorContext(
            ocr_text="문제",
            explanation="설명",
            mathml="<math>x</math>",
            model_used="gpt-test",
            openai_request_id="req-123",
        ),
        figure=FigureContext(
            svg_url=f"{user.user_id}/{job.job_id}/outputs/q1.svg",
            crop_url=f"{user.user_id}/{job.job_id}/outputs/q1_crop.png",
            edited_svg_url=f"{user.user_id}/{job.job_id}/outputs/q1.edited.latest.svg",
            edited_svg_version=3,
        ),
        status="completed",
        success=True,
    )
    prepared_job = copy.deepcopy(job)
    prepared_job.regions = [region]
    repository.save_job(user, prepared_job)

    client = TestClient(app)
    response = client.get(f"/jobs/{job.job_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "region-sample.png"
    assert payload["image_width"] == 32
    assert payload["image_height"] == 24
    assert payload["image_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["type"] == "diagram"
    assert payload["regions"][0]["order"] == 2
    assert payload["regions"][0]["polygon"] == [[1, 2], [21, 2], [21, 12], [1, 12]]
    assert payload["regions"][0]["svg_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["crop_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["edited_svg_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["edited_svg_version"] == 3


def test_get_job_accepts_es256_authenticated_user(monkeypatch):
    repository = install_memory_repository(monkeypatch)
    private_key, jwk = build_es256_key_pair("jobs-read-kid")
    token = build_es256_token(private_key, "jobs-read-kid", "user-123")
    user = AuthenticatedUser(user_id="user-123", access_token=token)

    monkeypatch.setattr(auth_module, "get_settings", lambda root_path: _build_auth_settings())
    monkeypatch.setattr(
        auth_module.requests,
        "get",
        lambda url, timeout=5: StubJwksResponse({"keys": [jwk]}),
    )

    job = orchestrator.create_job_from_bytes(user, "region-sample.png", make_png_bytes())
    repository.save_job(user, copy.deepcopy(job))

    client = TestClient(app)
    response = client.get(
        f"/jobs/{job.job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["job_id"] == job.job_id
