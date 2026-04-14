from __future__ import annotations

import json

from app.supabase import SupabaseClient, SupabaseConfig


class StubResponse:
    """Supabase HTTP 응답 모형을 단순화한 테스트 더블이다."""

    def __init__(self, payload: object, *, status_code: int = 200, content_type: str = "application/json") -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = {"content-type": content_type}
        self.text = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        self.content = self.text.encode("utf-8")

    def json(self) -> object:
        """JSON payload를 그대로 반환한다."""
        return self._payload


def build_client() -> SupabaseClient:
    """Storage helper 테스트용 Supabase 클라이언트를 만든다."""
    return SupabaseClient(
        SupabaseConfig(
            url="https://example.supabase.co",
            anon_key="anon-key",
            storage_bucket="ocr-assets",
        ),
        access_token="token-123",
    )


def test_list_objects_posts_prefix_payload(monkeypatch):
    """Storage list helper는 prefix 기준 목록 요청을 보내야 한다."""
    client = build_client()
    calls: list[dict[str, object]] = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return StubResponse([{"name": "input/sample.png"}])

    monkeypatch.setattr(client._session, "request", fake_request)

    objects = client.list_objects("user-123/job-1", limit=50, offset=10)

    assert objects == [{"name": "input/sample.png"}]
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"] == "https://example.supabase.co/storage/v1/object/list/ocr-assets"
    assert calls[0]["json"] == {
        "prefix": "user-123/job-1",
        "limit": 50,
        "offset": 10,
        "sortBy": {"column": "name", "order": "asc"},
    }


def test_remove_objects_deletes_multiple_paths(monkeypatch):
    """Storage remove helper는 여러 경로를 한 번에 삭제 요청해야 한다."""
    client = build_client()
    calls: list[dict[str, object]] = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return StubResponse({})

    monkeypatch.setattr(client._session, "request", fake_request)

    client.remove_objects(["user-123/job-1/input/a.png", "user-123/job-1/outputs/b.png"])

    assert calls[0]["method"] == "DELETE"
    assert calls[0]["url"] == "https://example.supabase.co/storage/v1/object/ocr-assets"
    assert calls[0]["json"] == {
        "prefixes": [
            "user-123/job-1/input/a.png",
            "user-123/job-1/outputs/b.png",
        ]
    }


def test_remove_objects_skips_empty_batches(monkeypatch):
    """빈 삭제 배치는 API 호출 없이 조용히 끝나야 한다."""
    client = build_client()
    calls: list[dict[str, object]] = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return StubResponse({})

    monkeypatch.setattr(client._session, "request", fake_request)

    client.remove_objects([])

    assert calls == []
