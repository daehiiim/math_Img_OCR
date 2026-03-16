from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests


class SupabaseApiError(RuntimeError):
    """Supabase REST 요청 실패를 감싸는 예외다."""


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    anon_key: str
    storage_bucket: str


class SupabaseClient:
    """사용자 JWT를 이용해 Supabase REST와 Storage를 호출한다."""

    def __init__(self, config: SupabaseConfig, access_token: str, api_key: str | None = None) -> None:
        self._config = config
        self._access_token = access_token
        self._api_key = api_key or config.anon_key
        self._session = requests.Session()

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Supabase 공통 인증 헤더를 조립한다."""
        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._access_token}",
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Supabase 엔드포인트에 HTTP 요청을 보내고 응답을 해석한다."""
        response = self._session.request(
            method=method,
            url=f"{self._config.url.rstrip('/')}{path}",
            params=params,
            json=json_body,
            data=data,
            headers=self._headers(headers),
            timeout=60,
        )
        if response.status_code >= 400:
            raise SupabaseApiError(response.text or f"Supabase request failed: {response.status_code}")

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.content

    def select(self, table: str, *, params: dict[str, Any]) -> list[dict[str, Any]]:
        """PostgREST select 결과를 반환한다."""
        payload = self._request("GET", f"/rest/v1/{table}", params=params)
        return payload if isinstance(payload, list) else []

    def insert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        """PostgREST insert를 수행하고 representation을 반환한다."""
        response = self._request(
            "POST",
            f"/rest/v1/{table}",
            json_body=payload,
            headers={"Prefer": "return=representation"},
        )
        return response if isinstance(response, list) else [response]

    def update(
        self,
        table: str,
        *,
        filters: dict[str, Any],
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """PostgREST update를 수행하고 representation을 반환한다."""
        response = self._request(
            "PATCH",
            f"/rest/v1/{table}",
            params=filters,
            json_body=payload,
            headers={"Prefer": "return=representation"},
        )
        return response if isinstance(response, list) else [response]

    def upsert(
        self,
        table: str,
        *,
        payload: list[dict[str, Any]],
        on_conflict: str,
    ) -> list[dict[str, Any]]:
        """PostgREST upsert를 수행한다."""
        response = self._request(
            "POST",
            f"/rest/v1/{table}",
            params={"on_conflict": on_conflict},
            json_body=payload,
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
        )
        return response if isinstance(response, list) else [response]

    def delete(self, table: str, *, filters: dict[str, Any]) -> None:
        """PostgREST delete를 수행한다."""
        self._request("DELETE", f"/rest/v1/{table}", params=filters)

    def upload_bytes(self, storage_path: str, content: bytes, content_type: str) -> None:
        """Storage object를 업로드하거나 덮어쓴다."""
        encoded_path = quote(storage_path, safe="/")
        self._request(
            "POST",
            f"/storage/v1/object/{self._config.storage_bucket}/{encoded_path}",
            data=content,
            headers={
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )

    def download_bytes(self, storage_path: str) -> bytes:
        """Storage object 바이트를 읽어온다."""
        encoded_path = quote(storage_path, safe="/")
        payload = self._request(
            "GET",
            f"/storage/v1/object/authenticated/{self._config.storage_bucket}/{encoded_path}",
        )
        return payload if isinstance(payload, bytes) else bytes(payload)

    def create_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Storage object에 대한 presigned URL을 생성한다."""
        encoded_path = quote(storage_path, safe="/")
        payload = self._request(
            "POST",
            f"/storage/v1/object/sign/{self._config.storage_bucket}/{encoded_path}",
            json_body={"expiresIn": expires_in},
        )
        signed_path = (
            payload.get("signedURL")
            or payload.get("signedUrl")
            or payload.get("signed_url")
        )
        if not signed_path:
            raise SupabaseApiError("signed URL is missing from response")
        return f"{self._config.url.rstrip('/')}/storage/v1{signed_path}"
