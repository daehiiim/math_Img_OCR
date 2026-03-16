import sys
import time
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.auth as auth_module
from app.auth import AuthenticatedUser, build_authenticated_user
from tests.auth_test_utils import (
    StubJwksResponse,
    build_es256_key_pair,
    build_es256_token,
    build_hs256_token,
)


def test_build_authenticated_user_accepts_valid_supabase_jwt():
    token = build_hs256_token("jwt-secret", "user-123")

    user = build_authenticated_user(f"Bearer {token}", "jwt-secret")

    assert user == AuthenticatedUser(user_id="user-123", access_token=token)


def test_build_authenticated_user_rejects_expired_token():
    token = build_hs256_token("jwt-secret", "user-123", expires_at=int(time.time()) - 5)

    with pytest.raises(ValueError, match="expired"):
        build_authenticated_user(f"Bearer {token}", "jwt-secret")


def test_build_authenticated_user_accepts_valid_es256_jwks_token(monkeypatch):
    private_key, jwk = build_es256_key_pair("kid-es256-valid")
    token = build_es256_token(private_key, "kid-es256-valid", "user-es256")
    calls: list[str] = []

    def fake_get(url: str, timeout: int = 5):
        calls.append(url)
        return StubJwksResponse({"keys": [jwk]})

    monkeypatch.setattr(auth_module.requests, "get", fake_get)

    user = build_authenticated_user(
        f"Bearer {token}",
        supabase_url="https://project-valid.supabase.co",
    )

    assert user == AuthenticatedUser(user_id="user-es256", access_token=token)
    assert calls == ["https://project-valid.supabase.co/auth/v1/.well-known/jwks.json"]


def test_build_authenticated_user_rejects_expired_es256_token(monkeypatch):
    private_key, jwk = build_es256_key_pair("kid-es256-expired")
    token = build_es256_token(private_key, "kid-es256-expired", "user-es256", expires_at=int(time.time()) - 5)

    monkeypatch.setattr(
        auth_module.requests,
        "get",
        lambda url, timeout=5: StubJwksResponse({"keys": [jwk]}),
    )

    with pytest.raises(ValueError, match="expired"):
        build_authenticated_user(
            f"Bearer {token}",
            supabase_url="https://project-expired.supabase.co",
        )


def test_build_authenticated_user_rejects_invalid_es256_signature(monkeypatch):
    signing_key, _ = build_es256_key_pair("kid-es256-invalid")
    _, other_jwk = build_es256_key_pair("kid-es256-invalid")
    token = build_es256_token(signing_key, "kid-es256-invalid", "user-es256")

    monkeypatch.setattr(
        auth_module.requests,
        "get",
        lambda url, timeout=5: StubJwksResponse({"keys": [other_jwk]}),
    )

    with pytest.raises(ValueError, match="signature"):
        build_authenticated_user(
            f"Bearer {token}",
            supabase_url="https://project-invalid.supabase.co",
        )


def test_build_authenticated_user_refreshes_jwks_on_unknown_kid(monkeypatch):
    private_key, jwk = build_es256_key_pair("kid-rotated")
    token = build_es256_token(private_key, "kid-rotated", "user-es256")
    responses = iter(
        [
            StubJwksResponse({"keys": []}),
            StubJwksResponse({"keys": [jwk]}),
        ]
    )
    calls: list[str] = []

    def fake_get(url: str, timeout: int = 5):
        calls.append(url)
        return next(responses)

    monkeypatch.setattr(auth_module.requests, "get", fake_get)

    user = build_authenticated_user(
        f"Bearer {token}",
        supabase_url="https://project-refresh.supabase.co",
    )

    assert user.user_id == "user-es256"
    assert len(calls) == 2


def test_build_authenticated_user_rejects_unknown_kid_after_refresh(monkeypatch):
    private_key, _ = build_es256_key_pair("kid-missing")
    token = build_es256_token(private_key, "kid-missing", "user-es256")
    calls: list[str] = []

    def fake_get(url: str, timeout: int = 5):
        calls.append(url)
        return StubJwksResponse({"keys": []})

    monkeypatch.setattr(auth_module.requests, "get", fake_get)

    with pytest.raises(ValueError, match="signing key"):
        build_authenticated_user(
            f"Bearer {token}",
            supabase_url="https://project-missing.supabase.co",
        )

    assert len(calls) == 2


def test_build_authenticated_user_accepts_hs256_fallback_when_secret_exists():
    token = build_hs256_token("jwt-secret", "user-legacy")

    user = build_authenticated_user(
        f"Bearer {token}",
        jwt_secret="jwt-secret",
        supabase_url="https://project-hs256.supabase.co",
    )

    assert user == AuthenticatedUser(user_id="user-legacy", access_token=token)


def test_build_authenticated_user_rejects_hs256_without_secret():
    token = build_hs256_token("jwt-secret", "user-legacy")

    with pytest.raises(ValueError, match="HS256"):
        build_authenticated_user(
            f"Bearer {token}",
            supabase_url="https://project-hs256-missing.supabase.co",
        )
