from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.auth import AuthenticatedUser
from app.config import AppSettings, get_settings
from app.supabase import SupabaseClient, SupabaseConfig

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))
MAX_RECENT_USERS = 10
RECENT_JOBS_SCAN_LIMIT = 200
ADMIN_MODE_CONFIG_DETAIL = "관리자 모드 서버 설정이 완료되지 않았습니다."
ADMIN_MODE_INVALID_PASSWORD_DETAIL = "관리자 비밀번호가 올바르지 않습니다."
ADMIN_MODE_INVALID_SESSION_DETAIL = "관리자 인증이 필요합니다."
ADMIN_MODE_EXPIRED_SESSION_DETAIL = "관리자 세션이 만료되었습니다. 다시 인증해 주세요."


class AdminModeConfigError(ValueError):
    """관리자 모드 필수 설정이 빠졌을 때 사용한다."""


class AdminModeAccessError(PermissionError):
    """관리자 인증 정보가 잘못됐을 때 사용한다."""


class AdminModeSessionExpiredError(ValueError):
    """관리자 세션 만료를 구분하기 위한 예외다."""


def _build_admin_supabase_client(settings: AppSettings) -> SupabaseClient:
    """서비스 롤 기반 관리자 전용 Supabase 클라이언트를 만든다."""
    supabase_url = settings.auth.supabase_url
    service_role_key = settings.auth.supabase_service_role_key
    if not supabase_url or not service_role_key:
        raise AdminModeConfigError(ADMIN_MODE_CONFIG_DETAIL)
    config = SupabaseConfig(
        url=supabase_url,
        anon_key=settings.auth.supabase_anon_key or service_role_key,
        storage_bucket=settings.auth.supabase_storage_bucket or "admin-mode",
    )
    return SupabaseClient(config, access_token=service_role_key, api_key=service_role_key)


class AdminModeService:
    """관리자 세션 발급과 운영 대시보드 집계를 담당한다."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        admin_client_factory: Callable[[], SupabaseClient] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings
        self._admin_client_factory = admin_client_factory or (lambda: _build_admin_supabase_client(settings))
        self._now_provider = now_provider or (lambda: datetime.now(tz=timezone.utc))

    def create_session(self, user: AuthenticatedUser, password: str) -> dict[str, str]:
        """관리자 비밀번호를 검증하고 현재 사용자 전용 세션 토큰을 발급한다."""
        self._validate_password(password)
        expires_at = self._now_provider().astimezone(timezone.utc) + timedelta(
            minutes=self._settings.admin_mode_session_ttl_minutes
        )
        payload = {
            "sub": user.user_id,
            "type": "admin_mode",
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._get_session_secret(), algorithm="HS256")
        return {"session_token": token, "expires_at": expires_at.isoformat()}

    def require_session(self, current_user: AuthenticatedUser, session_token: str | None) -> None:
        """현재 로그인 사용자와 관리자 세션 토큰이 함께 유효한지 검증한다."""
        payload = self._decode_session_token(session_token)
        if str(payload.get("sub") or "") != current_user.user_id:
            raise AdminModeAccessError(ADMIN_MODE_INVALID_SESSION_DETAIL)

    def read_dashboard(self) -> dict[str, Any]:
        """운영자가 보는 관리자 대시보드 응답 형태를 집계해 반환한다."""
        client = self._admin_client_factory()
        day_start = self._build_kst_day_start_filter()
        return {
            "generated_at": self._now_provider().astimezone(timezone.utc).isoformat(),
            "failed_jobs_today": self._count_failed_jobs_today(client, day_start),
            "missing_openai_request_regions_today": self._count_missing_requests_today(client, day_start),
            "recent_user_runs": self._read_recent_user_runs(client),
        }

    def _validate_password(self, password: str) -> None:
        """관리자 비밀번호 설정 존재 여부와 입력값 일치를 확인한다."""
        expected_password = self._settings.admin_mode_password
        if not expected_password:
            raise AdminModeConfigError(ADMIN_MODE_CONFIG_DETAIL)
        if not hmac.compare_digest(str(password or ""), expected_password):
            raise AdminModeAccessError(ADMIN_MODE_INVALID_PASSWORD_DETAIL)

    def _get_session_secret(self) -> str:
        """관리자 세션 서명에 사용할 비밀키를 반환한다."""
        session_secret = self._settings.admin_mode_session_secret
        if not session_secret:
            raise AdminModeConfigError(ADMIN_MODE_CONFIG_DETAIL)
        return session_secret

    def _decode_session_token(self, session_token: str | None) -> dict[str, Any]:
        """관리자 세션 토큰의 서명, 만료, 타입을 검증한다."""
        if not str(session_token or "").strip():
            raise AdminModeAccessError(ADMIN_MODE_INVALID_SESSION_DETAIL)
        try:
            payload = jwt.decode(session_token, self._get_session_secret(), algorithms=["HS256"])
        except ExpiredSignatureError as error:
            raise AdminModeSessionExpiredError(ADMIN_MODE_EXPIRED_SESSION_DETAIL) from error
        except InvalidTokenError as error:
            raise AdminModeAccessError(ADMIN_MODE_INVALID_SESSION_DETAIL) from error
        if payload.get("type") != "admin_mode":
            raise AdminModeAccessError(ADMIN_MODE_INVALID_SESSION_DETAIL)
        return payload

    def _build_kst_day_start_filter(self) -> str:
        """한국 시간 자정 기준 UTC ISO 필터 문자열을 만든다."""
        now_in_kst = self._now_provider().astimezone(KST)
        day_start = datetime(now_in_kst.year, now_in_kst.month, now_in_kst.day, tzinfo=KST)
        return f"gte.{day_start.astimezone(timezone.utc).isoformat()}"

    def _count_failed_jobs_today(self, client: SupabaseClient, day_start: str) -> int:
        """오늘 생성된 실패 작업 수를 계산한다."""
        rows = client.select(
            "ocr_jobs",
            params={"select": "id", "status": "eq.failed", "created_at": day_start},
        )
        return len(rows)

    def _count_missing_requests_today(self, client: SupabaseClient, day_start: str) -> int:
        """OpenAI request id 없이 완료된 OCR/이미지 분석 결과 수를 계산한다."""
        rows = client.select(
            "ocr_job_regions",
            params={
                "select": "id,ocr_text,mathml,styled_image_path,styled_image_model",
                "status": "eq.completed",
                "openai_request_id": "is.null",
                "created_at": day_start,
            },
        )
        return sum(1 for row in rows if self._has_analysis_output(row))

    def _has_analysis_output(self, row: dict[str, Any]) -> bool:
        """해설 전용 산출물을 제외하고 OCR/이미지 분석 결과 존재 여부만 판별한다."""
        return bool(
            str(row.get("ocr_text") or "").strip()
            or str(row.get("mathml") or "").strip()
            or str(row.get("styled_image_path") or "").strip()
            or str(row.get("styled_image_model") or "").strip()
        )

    def _read_recent_user_runs(self, client: SupabaseClient) -> list[dict[str, Any]]:
        """사용자별 최신 작업 1건만 뽑아 최근 실행 목록으로 변환한다."""
        rows = client.select(
            "ocr_jobs",
            params={
                "select": "id,user_id,file_name,status,created_at,updated_at",
                "order": "updated_at.desc",
                "limit": str(RECENT_JOBS_SCAN_LIMIT),
            },
        )
        latest_rows = self._pick_latest_job_per_user(rows)
        return [self._build_recent_user_run(client, row) for row in latest_rows]

    def _pick_latest_job_per_user(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """최신 정렬된 작업 목록에서 사용자당 첫 작업만 최대 10건 남긴다."""
        latest_rows: list[dict[str, Any]] = []
        seen_user_ids: set[str] = set()
        for row in rows:
            user_id = str(row.get("user_id") or "").strip()
            if not user_id or user_id in seen_user_ids:
                continue
            seen_user_ids.add(user_id)
            latest_rows.append(row)
            if len(latest_rows) >= MAX_RECENT_USERS:
                break
        return latest_rows

    def _build_recent_user_run(self, client: SupabaseClient, row: dict[str, Any]) -> dict[str, Any]:
        """최근 실행 row 하나를 프런트 전용 응답 구조로 바꾼다."""
        user_id = str(row.get("user_id") or "").strip()
        suffix = self._build_user_id_suffix(user_id)
        display_name = self._read_display_name(client, user_id)
        return {
            "user_label": self._resolve_user_label(user_id, display_name),
            "user_id_suffix": suffix,
            "job_id": str(row.get("id") or ""),
            "file_name": str(row.get("file_name") or ""),
            "job_status": str(row.get("status") or ""),
            "region_count": self._count_regions_for_job(client, str(row.get("id") or "")),
            "ran_at": row.get("updated_at") or row.get("created_at"),
        }

    def _build_user_id_suffix(self, user_id: str) -> str:
        """운영 화면에 표시할 짧은 사용자 식별자를 만든다."""
        return user_id[-4:] if len(user_id) > 4 else user_id

    def _read_display_name(self, client: SupabaseClient, user_id: str) -> str | None:
        """profiles 에서 운영자가 볼 사용자 표시 이름을 읽는다."""
        rows = client.select("profiles", params={"select": "id,display_name", "id": f"eq.{user_id}", "limit": "1"})
        if not rows:
            return None
        display_name = str(rows[0].get("display_name") or "").strip()
        return display_name or None

    def _resolve_user_label(self, user_id: str, display_name: str | None) -> str:
        """부실한 display_name 은 버리고 축약 user id 를 표시 라벨로 사용한다."""
        normalized = str(display_name or "").strip()
        looks_like_generated_id = normalized and len(normalized) <= 8 and normalized in user_id
        if normalized and not looks_like_generated_id and normalized not in {user_id, self._build_user_id_suffix(user_id)}:
            return normalized
        return self._build_user_id_suffix(user_id)

    def _count_regions_for_job(self, client: SupabaseClient, job_id: str) -> int:
        """작업별 영역 개수를 단순 카운트로 계산한다."""
        rows = client.select("ocr_job_regions", params={"select": "region_key", "job_id": f"eq.{job_id}"})
        return len(rows)


def build_admin_mode_service() -> AdminModeService:
    """현재 환경설정을 읽어 관리자 모드 서비스를 생성한다."""
    return AdminModeService(settings=get_settings(ROOT))
