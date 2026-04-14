from __future__ import annotations

from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.auth import AuthenticatedUser
from app.config import AppSettings, get_settings
from app.supabase import SupabaseClient, SupabaseConfig

ROOT = Path(__file__).resolve().parents[1]
PURGE_BATCH_SIZE = 100
PURGE_RETENTION_DAYS = 14
PURGE_TARGET_STATUSES = ("completed", "failed", "exported")
DELETE_RUNNING_JOB_DETAIL = "처리 중인 작업은 삭제할 수 없습니다."
JOB_HISTORY_CONFIG_DETAIL = "작업 history 유지 서버 설정이 완료되지 않았습니다."


class JobDeleteConflictError(ValueError):
    """처리 중 작업 삭제 요청을 구분하기 위한 예외다."""


def _build_service_role_client(settings: AppSettings) -> SupabaseClient:
    """Storage purge 전용 service-role Supabase 클라이언트를 만든다."""
    supabase_url = settings.auth.supabase_url
    service_role_key = settings.auth.supabase_service_role_key
    if not supabase_url or not service_role_key:
        raise ValueError(JOB_HISTORY_CONFIG_DETAIL)
    return SupabaseClient(
        SupabaseConfig(
            url=supabase_url,
            anon_key=settings.auth.supabase_anon_key or service_role_key,
            storage_bucket=settings.auth.supabase_storage_bucket or "ocr-assets",
        ),
        access_token=service_role_key,
        api_key=service_role_key,
    )


class JobHistoryService:
    """작업 history 조회, 삭제, 자동 정리 흐름을 담당한다."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        admin_client_factory: Callable[[], SupabaseClient] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings
        self._admin_client_factory = admin_client_factory or (lambda: _build_service_role_client(settings))
        self._now_provider = now_provider or (lambda: datetime.now(tz=timezone.utc))

    def list_job_summaries(self, user: AuthenticatedUser) -> list[dict[str, Any]]:
        """현재 사용자 작업 목록을 최신순 summary로 반환한다."""
        client = self._build_user_client(user)
        rows = client.select(
            "ocr_jobs",
            params={
                "select": "id,file_name,status,created_at,updated_at,hwpx_export_path,last_error",
                "order": "updated_at.desc",
            },
        )
        return [self._build_job_summary(client, row) for row in rows]

    def delete_job(self, user: AuthenticatedUser, job_id: str) -> dict[str, Any]:
        """사용자 own job과 관련 Storage 자산을 hard delete 한다."""
        client = self._build_user_client(user)
        row = self._read_owned_job_row(client, job_id)
        if row is None:
            raise FileNotFoundError(f"job not found: {job_id}")
        if str(row.get("status") or "") == "running":
            raise JobDeleteConflictError(DELETE_RUNNING_JOB_DETAIL)
        deleted_objects = self._purge_job_assets(self._admin_client_factory(), str(row["user_id"]), job_id)
        client.delete("ocr_jobs", filters={"id": f"eq.{job_id}"})
        return {"job_id": job_id, "deleted_objects": deleted_objects}

    def purge_stale_jobs(self) -> dict[str, Any]:
        """14일 지난 종료 작업을 batch 단위로 자동 정리한다."""
        client = self._admin_client_factory()
        cutoff_at = self._build_cutoff_at()
        deleted_jobs = 0
        deleted_objects = 0
        scanned_jobs = 0
        while True:
            batch = self._read_stale_jobs_batch(client, cutoff_at)
            if not batch:
                break
            scanned_jobs += len(batch)
            for row in batch:
                deleted_objects += self._purge_job_assets(client, str(row["user_id"]), str(row["id"]))
                client.delete("ocr_jobs", filters={"id": f"eq.{row['id']}"})
                deleted_jobs += 1
        return {
            "deleted_jobs": deleted_jobs,
            "deleted_objects": deleted_objects,
            "scanned_jobs": scanned_jobs,
            "cutoff_at": cutoff_at,
        }

    def _build_user_client(self, user: AuthenticatedUser) -> SupabaseClient:
        """사용자 JWT로 own data에 접근하는 Supabase 클라이언트를 만든다."""
        supabase_url = self._settings.auth.supabase_url
        supabase_anon_key = self._settings.auth.supabase_anon_key
        if not supabase_url or not supabase_anon_key:
            raise ValueError("Supabase REST settings are not configured")
        return SupabaseClient(
            SupabaseConfig(
                url=supabase_url,
                anon_key=supabase_anon_key,
                storage_bucket=self._settings.auth.supabase_storage_bucket or "ocr-assets",
            ),
            access_token=user.access_token,
        )

    def _build_job_summary(self, client: SupabaseClient, row: dict[str, Any]) -> dict[str, Any]:
        """단일 작업 row를 워크스페이스용 summary로 변환한다."""
        job_id = str(row["id"])
        return {
            "job_id": job_id,
            "file_name": str(row.get("file_name") or ""),
            "status": str(row.get("status") or "created"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "region_count": self._count_regions_for_job(client, job_id),
            "hwpx_ready": bool(str(row.get("hwpx_export_path") or "").strip()),
            "last_error": row.get("last_error"),
        }

    def _count_regions_for_job(self, client: SupabaseClient, job_id: str) -> int:
        """작업별 영역 개수를 단순 row 수로 계산한다."""
        rows = client.select("ocr_job_regions", params={"select": "region_key", "job_id": f"eq.{job_id}"})
        return len(rows)

    def _read_owned_job_row(self, client: SupabaseClient, job_id: str) -> dict[str, Any] | None:
        """현재 사용자 기준으로 삭제 가능한 작업 row 1건을 읽는다."""
        rows = client.select(
            "ocr_jobs",
            params={"select": "id,user_id,status", "id": f"eq.{job_id}", "limit": "1"},
        )
        return rows[0] if rows else None

    def _read_stale_jobs_batch(self, client: SupabaseClient, cutoff_at: str) -> list[dict[str, Any]]:
        """자동 삭제 대상 종료 작업 batch를 오래된 순서로 읽는다."""
        statuses = ",".join(PURGE_TARGET_STATUSES)
        return client.select(
            "ocr_jobs",
            params={
                "select": "id,user_id,updated_at,status",
                "status": f"in.({statuses})",
                "updated_at": f"lt.{cutoff_at}",
                "order": "updated_at.asc",
                "limit": str(PURGE_BATCH_SIZE),
            },
        )

    def _build_cutoff_at(self) -> str:
        """자동 정리 기준 시각을 UTC ISO 문자열로 계산한다."""
        cutoff = self._now_provider().astimezone(timezone.utc) - timedelta(days=PURGE_RETENTION_DAYS)
        return cutoff.isoformat()

    def _purge_job_assets(self, client: SupabaseClient, user_id: str, job_id: str) -> int:
        """job prefix 아래 Storage 파일을 전부 삭제하고 삭제 수를 반환한다."""
        job_prefix = f"{user_id}/{job_id}"
        storage_paths = self._walk_storage_paths(client, job_prefix)
        self._remove_storage_paths(client, storage_paths)
        return len(storage_paths)

    def _walk_storage_paths(self, client: SupabaseClient, job_prefix: str) -> list[str]:
        """job prefix 아래 실제 파일 경로만 재귀적으로 수집한다."""
        pending = deque([job_prefix.strip("/")])
        storage_paths: list[str] = []
        while pending:
            prefix = pending.popleft()
            for entry in self._read_storage_entries(client, prefix):
                full_path = f"{prefix}/{entry['name']}".strip("/")
                if self._is_storage_file(entry):
                    storage_paths.append(full_path)
                else:
                    pending.append(full_path)
        return storage_paths

    def _read_storage_entries(self, client: SupabaseClient, prefix: str) -> list[dict[str, Any]]:
        """단일 Storage prefix의 모든 페이지를 합쳐 반환한다."""
        entries: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = client.list_objects(prefix, limit=PURGE_BATCH_SIZE, offset=offset)
            if not page:
                break
            entries.extend(page)
            if len(page) < PURGE_BATCH_SIZE:
                break
            offset += len(page)
        return entries

    def _remove_storage_paths(self, client: SupabaseClient, storage_paths: list[str]) -> None:
        """Storage 파일 경로 목록을 chunk 단위로 삭제한다."""
        for index in range(0, len(storage_paths), PURGE_BATCH_SIZE):
            client.remove_objects(storage_paths[index : index + PURGE_BATCH_SIZE])

    def _is_storage_file(self, entry: dict[str, Any]) -> bool:
        """Storage list 항목이 실제 파일인지 폴더인지 판별한다."""
        return bool(entry.get("id") or entry.get("metadata"))


def build_job_history_service() -> JobHistoryService:
    """현재 환경설정으로 작업 history 서비스를 생성한다."""
    return JobHistoryService(settings=get_settings(ROOT))
