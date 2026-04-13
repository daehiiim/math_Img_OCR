import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app.admin_mode import AdminModeService
from app.auth import AuthenticatedUser, require_authenticated_user
from app.config import AppSettings, AuthSettings, BillingSettings, get_settings
from app.main import app

KST = timezone(timedelta(hours=9))


class DashboardStubClient:
    """관리자 대시보드 select 응답을 테이블과 필터별로 돌려주는 테스트용 클라이언트다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def select(self, table: str, *, params: dict[str, str]) -> list[dict]:
        """호출을 기록하고 조건에 맞는 고정 응답을 반환한다."""
        self.calls.append((table, params))

        if table == "ocr_jobs" and params.get("status") == "eq.failed":
            return [{"id": "job-fail-1"}, {"id": "job-fail-2"}]

        if table == "ocr_job_regions" and params.get("status") == "eq.completed":
            return [
                {"id": "region-1", "ocr_text": "x=1", "mathml": "", "styled_image_path": "", "styled_image_model": ""},
                {"id": "region-2", "ocr_text": "", "mathml": "", "styled_image_path": "", "styled_image_model": ""},
                {
                    "id": "region-3",
                    "ocr_text": "",
                    "mathml": "",
                    "styled_image_path": "styled/job-3.png",
                    "styled_image_model": "nano-banana",
                },
            ]

        if table == "ocr_jobs" and params.get("order") == "updated_at.desc":
            return [
                {
                    "id": "job-latest-user-1",
                    "user_id": "user-aaaabbbbcccc1111",
                    "file_name": "latest.png",
                    "status": "completed",
                    "created_at": "2026-04-13T00:10:00+00:00",
                    "updated_at": "2026-04-13T00:30:00+00:00",
                },
                {
                    "id": "job-older-user-1",
                    "user_id": "user-aaaabbbbcccc1111",
                    "file_name": "older.png",
                    "status": "failed",
                    "created_at": "2026-04-12T22:10:00+00:00",
                    "updated_at": "2026-04-12T22:20:00+00:00",
                },
                {
                    "id": "job-latest-user-2",
                    "user_id": "user-2222333344449999",
                    "file_name": "second.png",
                    "status": "failed",
                    "created_at": "2026-04-12T21:10:00+00:00",
                    "updated_at": "2026-04-12T22:00:00+00:00",
                },
            ]

        if table == "ocr_job_regions" and params.get("job_id") == "eq.job-latest-user-1":
            return [{"region_key": "r1"}, {"region_key": "r2"}]

        if table == "ocr_job_regions" and params.get("job_id") == "eq.job-latest-user-2":
            return [{"region_key": "r1"}]

        if table == "profiles" and params.get("id") == "eq.user-aaaabbbbcccc1111":
            return [{"id": "user-aaaabbbbcccc1111", "display_name": "aaaabbbb"}]

        if table == "profiles" and params.get("id") == "eq.user-2222333344449999":
            return [{"id": "user-2222333344449999", "display_name": "홍길동"}]

        return []


def _build_settings() -> AppSettings:
    """관리자 모드 테스트에 필요한 최소 설정 묶음을 만든다."""
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
        admin_mode_password="admin-secret",
        admin_mode_session_secret="admin-session-secret",
        admin_mode_session_ttl_minutes=30,
    )


def test_get_settings_reads_admin_mode_values(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "ADMIN_MODE_PASSWORD=file-admin-password",
                "ADMIN_MODE_SESSION_SECRET=file-admin-secret",
                "ADMIN_MODE_SESSION_TTL_MINUTES=45",
            ]
        ),
        encoding="utf-8",
    )

    settings = get_settings(tmp_path)

    assert settings.admin_mode_password == "file-admin-password"
    assert settings.admin_mode_session_secret == "file-admin-secret"
    assert settings.admin_mode_session_ttl_minutes == 45


def test_get_settings_uses_default_admin_session_ttl(tmp_path):
    settings = get_settings(tmp_path)

    assert settings.admin_mode_session_ttl_minutes == 30


def test_create_admin_session_returns_signed_token(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="access-token")
    app.dependency_overrides[require_authenticated_user] = lambda: user
    monkeypatch.setattr("app.admin_mode.get_settings", lambda root_path: _build_settings())
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/admin/session", json={"password": "admin-secret"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["session_token"], str) and payload["session_token"]
    assert payload["expires_at"].startswith("20")


def test_create_admin_session_rejects_wrong_password(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="access-token")
    app.dependency_overrides[require_authenticated_user] = lambda: user
    monkeypatch.setattr("app.admin_mode.get_settings", lambda root_path: _build_settings())
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/admin/session", json={"password": "wrong-password"})

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "관리자 비밀번호가 올바르지 않습니다."


def test_admin_dashboard_rejects_missing_session_header(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="access-token")
    service = AdminModeService(settings=_build_settings(), admin_client_factory=DashboardStubClient)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    monkeypatch.setattr(main_module, "_get_admin_mode_service", lambda: service)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/admin/dashboard")

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "관리자 인증이 필요합니다."


def test_admin_dashboard_rejects_expired_session(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="access-token")
    settings = _build_settings()
    expired_token = jwt.encode(
        {
            "sub": user.user_id,
            "type": "admin_mode",
            "exp": int(datetime.now(tz=timezone.utc).timestamp()) - 5,
        },
        settings.admin_mode_session_secret,
        algorithm="HS256",
    )
    service = AdminModeService(settings=settings, admin_client_factory=DashboardStubClient)
    app.dependency_overrides[require_authenticated_user] = lambda: user
    monkeypatch.setattr(main_module, "_get_admin_mode_service", lambda: service)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/admin/dashboard", headers={"X-Admin-Session": expired_token})

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "관리자 세션이 만료되었습니다. 다시 인증해 주세요."


def test_admin_mode_service_builds_dashboard_snapshot_with_kst_rules():
    fixed_now = datetime(2026, 4, 13, 9, 15, tzinfo=KST)
    client = DashboardStubClient()
    service = AdminModeService(
        settings=_build_settings(),
        admin_client_factory=lambda: client,
        now_provider=lambda: fixed_now,
    )

    snapshot = service.read_dashboard()

    assert snapshot["failed_jobs_today"] == 2
    assert snapshot["missing_openai_request_regions_today"] == 2
    assert len(snapshot["recent_user_runs"]) == 2
    assert snapshot["recent_user_runs"][0]["user_label"] == "1111"
    assert snapshot["recent_user_runs"][0]["user_id_suffix"] == "1111"
    assert snapshot["recent_user_runs"][0]["region_count"] == 2
    assert snapshot["recent_user_runs"][1]["user_label"] == "홍길동"
    assert snapshot["recent_user_runs"][1]["region_count"] == 1

    expected_boundary = "gte.2026-04-12T15:00:00+00:00"
    failed_call = next(params for table, params in client.calls if table == "ocr_jobs" and params.get("status") == "eq.failed")
    missing_call = next(
        params for table, params in client.calls if table == "ocr_job_regions" and params.get("status") == "eq.completed"
    )

    assert failed_call["created_at"] == expected_boundary
    assert missing_call["created_at"] == expected_boundary


def test_admin_dashboard_returns_snapshot_for_valid_session(monkeypatch):
    user = AuthenticatedUser(user_id="user-123", access_token="access-token")
    service = AdminModeService(
        settings=_build_settings(),
        admin_client_factory=DashboardStubClient,
    )
    session = service.create_session(user, "admin-secret")
    app.dependency_overrides[require_authenticated_user] = lambda: user
    monkeypatch.setattr(main_module, "_get_admin_mode_service", lambda: service)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/admin/dashboard", headers={"X-Admin-Session": session["session_token"]})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["failed_jobs_today"] == 2
    assert payload["missing_openai_request_regions_today"] == 2
    assert payload["recent_user_runs"][0]["job_id"] == "job-latest-user-1"
