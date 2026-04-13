import copy
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.auth as auth_module
from app.auth import AuthenticatedUser, require_authenticated_user
from app.config import AppSettings, AuthSettings, BillingSettings
from app.main import app
from app.pipeline import orchestrator
from app.pipeline.schema import ExtractorContext, FigureContext, RegionContext, RegionPipelineContext
from app.supabase import SupabaseApiError
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
        openai_key_encryption_secret=None,
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
            selection_mode="auto_detected",
            input_device="pen",
            warning_level="normal",
            auto_detect_confidence=0.87,
        ),
        extractor=ExtractorContext(
            ocr_text="문제",
            explanation="설명",
            mathml="<math>x</math>",
            problem_markdown="문제 $x$",
            explanation_markdown="설명 $x$",
            markdown_version="mathocr_markdown_latex_v2",
            raw_transcript="1. 문제 <math>x</math>",
            ordered_segments=[
                {"type": "text", "content": "문제 ", "source_order": 0},
                {"type": "math", "content": "x", "source_order": 1},
            ],
            question_type="multiple_choice",
            parsed_choices=["1", "2", "3", "4", "5"],
            resolved_answer_index=2,
            resolved_answer_value="2",
            answer_confidence=0.88,
            verification_status="warning",
            verification_warnings=["해설 최종 답과 선택지 값이 일치하지 않습니다."],
            reason_summary="선택지 대조가 필요합니다.",
            model_used="gpt-test",
            openai_request_id="req-123",
        ),
        figure=FigureContext(
            svg_url=f"{user.user_id}/{job.job_id}/outputs/q1.svg",
            crop_url=f"{user.user_id}/{job.job_id}/outputs/q1_crop.png",
            image_crop_url=f"{user.user_id}/{job.job_id}/outputs/q1.image_crop.png",
            styled_image_url=f"{user.user_id}/{job.job_id}/outputs/q1.styled.png",
            styled_image_model="gemini-3-pro-image-preview",
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
    assert payload["regions"][0]["selection_mode"] == "auto_detected"
    assert payload["regions"][0]["input_device"] == "pen"
    assert payload["regions"][0]["warning_level"] == "normal"
    assert payload["regions"][0]["auto_detect_confidence"] == 0.87
    assert payload["regions"][0]["problem_markdown"] == "문제 $x$"
    assert payload["regions"][0]["explanation_markdown"] == "설명 $x$"
    assert payload["regions"][0]["markdown_version"] == "mathocr_markdown_latex_v2"
    assert payload["regions"][0]["raw_transcript"] == "1. 문제 <math>x</math>"
    assert payload["regions"][0]["ordered_segments"] == [
        {"type": "text", "content": "문제 ", "source_order": 0},
        {"type": "math", "content": "x", "source_order": 1},
    ]
    assert payload["regions"][0]["question_type"] == "multiple_choice"
    assert payload["regions"][0]["parsed_choices"] == ["1", "2", "3", "4", "5"]
    assert payload["regions"][0]["resolved_answer_index"] == 2
    assert payload["regions"][0]["resolved_answer_value"] == "2"
    assert payload["regions"][0]["answer_confidence"] == 0.88
    assert payload["regions"][0]["verification_status"] == "warning"
    assert payload["regions"][0]["verification_warnings"] == ["해설 최종 답과 선택지 값이 일치하지 않습니다."]
    assert payload["regions"][0]["reason_summary"] == "선택지 대조가 필요합니다."
    assert payload["regions"][0]["svg_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["crop_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["image_crop_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["styled_image_url"].startswith("https://signed.example/")
    assert payload["regions"][0]["styled_image_model"] == "gemini-3-pro-image-preview"
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


def test_get_job_returns_schema_mismatch_detail_for_supabase_error(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    monkeypatch.setattr(
        "app.main.pipeline.read_job",
        lambda current_user, job_id: (_ for _ in ()).throw(
            SupabaseApiError('column image_charged does not exist in relation "ocr_job_regions"')
        ),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/jobs/job-123")

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "배포 DB 스키마가 최신이 아닙니다."


def test_get_job_returns_storage_failure_detail_for_supabase_error(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    monkeypatch.setattr(
        "app.main.pipeline.read_job",
        lambda current_user, job_id: (_ for _ in ()).throw(SupabaseApiError("storage request timeout")),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/jobs/job-123")

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "서버 저장소 연결에 실패했습니다. 잠시 후 다시 시도하세요."


def test_download_hwpx_uses_fixed_filename(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    job_id = "job-123"
    prepared_job = SimpleNamespace(
        job_id=job_id,
        hwpx_export_path=f"{user.user_id}/{job_id}/exports/{job_id}.hwpx",
    )

    monkeypatch.setattr("app.main.pipeline.read_job", lambda current_user, job_id: prepared_job)
    monkeypatch.setattr("app.main.pipeline.download_asset_bytes", lambda current_user, storage_path: b"hwpx-bytes")

    client = TestClient(app)
    response = client.get(f"/jobs/{job_id}/export/hwpx/download")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == "attachment; filename*=UTF-8''%EC%83%9D%EC%84%B1%EA%B2%B0%EA%B3%BC.hwpx"
    )
    assert response.content == b"hwpx-bytes"


def test_export_hwpx_returns_runtime_missing_detail(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    monkeypatch.setattr(
        "app.main.pipeline.execute_hwpx_export",
        lambda current_user, job_id: (_ for _ in ()).throw(
            ValueError("문서 생성 엔진이 준비되지 않았습니다. 관리자에게 문의하세요.")
        ),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/jobs/job-123/export/hwpx")

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "문서 생성 엔진이 준비되지 않았습니다. 관리자에게 문의하세요."


def test_export_hwpx_returns_template_apply_failure_detail(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    monkeypatch.setattr(
        "app.main.pipeline.execute_hwpx_export",
        lambda current_user, job_id: (_ for _ in ()).throw(
            ValueError("텍스트 추출은 완료됐지만 문서 양식 적용에 실패했습니다. Markdown 결과는 저장되어 있으니 다시 내보내기 하세요.")
        ),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/jobs/job-123/export/hwpx")

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "텍스트 추출은 완료됐지만 문서 양식 적용에 실패했습니다. Markdown 결과는 저장되어 있으니 다시 내보내기 하세요."
    )


def test_save_regions_returns_schema_mismatch_detail_for_supabase_error(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    monkeypatch.setattr(
        "app.main.pipeline.save_regions",
        lambda current_user, job_id, regions: (_ for _ in ()).throw(
            SupabaseApiError('column image_charged does not exist in relation "ocr_job_regions"')
        ),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.put(
        "/jobs/job-123/regions",
        json={
            "regions": [
                {
                    "id": "q1",
                    "polygon": [[1, 1], [11, 1], [11, 11], [1, 11]],
                    "type": "mixed",
                    "order": 1,
                }
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "배포 DB 스키마가 최신이 아닙니다."


def test_save_regions_returns_storage_failure_detail_for_supabase_error(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user

    monkeypatch.setattr(
        "app.main.pipeline.save_regions",
        lambda current_user, job_id, regions: (_ for _ in ()).throw(SupabaseApiError("storage request timeout")),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.put(
        "/jobs/job-123/regions",
        json={
            "regions": [
                {
                    "id": "q1",
                    "polygon": [[1, 1], [11, 1], [11, 11], [1, 11]],
                    "type": "mixed",
                    "order": 1,
                }
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "서버 저장소 연결에 실패했습니다. 잠시 후 다시 시도하세요."
