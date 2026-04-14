import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app.auth import AuthenticatedUser, require_authenticated_user
from app.config import AppSettings, AuthSettings, BillingSettings
from app.main import app


def _build_settings() -> AppSettings:
    """작업 history/maintenance 테스트용 최소 설정을 만든다."""
    return AppSettings(
        openai_api_key=None,
        openai_key_encryption_secret=None,
        database_url=None,
        auth=AuthSettings(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
            supabase_jwt_secret="jwt-secret",
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
        maintenance_job_token="maintenance-token",
    )


def test_get_jobs_returns_history_summaries(monkeypatch):
    """작업 목록 API는 워크스페이스 history 요약만 반환해야 한다."""
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user
    monkeypatch.setattr(
        main_module,
        "_get_job_history_service",
        lambda: SimpleNamespace(
            list_job_summaries=lambda current_user: [
                {
                    "job_id": "job-1",
                    "file_name": "sample.png",
                    "status": "completed",
                    "created_at": "2026-04-01T00:00:00+00:00",
                    "updated_at": "2026-04-01T00:12:00+00:00",
                    "region_count": 2,
                    "hwpx_ready": True,
                    "last_error": None,
                }
            ]
        ),
        raising=False,
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/jobs")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "job_id": "job-1",
            "file_name": "sample.png",
            "status": "completed",
            "created_at": "2026-04-01T00:00:00+00:00",
            "updated_at": "2026-04-01T00:12:00+00:00",
            "region_count": 2,
            "hwpx_ready": True,
            "last_error": None,
        }
    ]


def test_delete_job_returns_deleted_result(monkeypatch):
    """작업 삭제 API는 삭제된 파일 수를 포함해 hard delete 결과를 반환해야 한다."""
    user = AuthenticatedUser(user_id="user-123", access_token="token-123")
    app.dependency_overrides[require_authenticated_user] = lambda: user
    monkeypatch.setattr(
        main_module,
        "_get_job_history_service",
        lambda: SimpleNamespace(
            delete_job=lambda current_user, job_id: {
                "job_id": job_id,
                "deleted_objects": 4,
            }
        ),
        raising=False,
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.delete("/jobs/job-1")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-1", "deleted_objects": 4}


def test_purge_stale_jobs_requires_valid_token(monkeypatch):
    """maintenance purge 엔드포인트는 잘못된 토큰을 거부해야 한다."""
    monkeypatch.setattr(main_module, "get_settings", lambda root_path: _build_settings())

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/internal/maintenance/purge-stale-jobs",
        headers={"X-Maintenance-Token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "유효하지 않은 maintenance 토큰입니다."


def test_purge_stale_jobs_returns_purge_summary(monkeypatch):
    """maintenance purge 엔드포인트는 삭제 통계를 응답해야 한다."""
    monkeypatch.setattr(main_module, "get_settings", lambda root_path: _build_settings())
    monkeypatch.setattr(
        main_module,
        "_get_job_history_service",
        lambda: SimpleNamespace(
            purge_stale_jobs=lambda: {
                "deleted_jobs": 3,
                "deleted_objects": 11,
                "scanned_jobs": 5,
                "cutoff_at": "2026-03-31T19:10:00+00:00",
            }
        ),
        raising=False,
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/internal/maintenance/purge-stale-jobs",
        headers={"X-Maintenance-Token": "maintenance-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "deleted_jobs": 3,
        "deleted_objects": 11,
        "scanned_jobs": 5,
        "cutoff_at": "2026-03-31T19:10:00+00:00",
    }
