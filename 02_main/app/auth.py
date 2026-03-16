from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import jwt
import requests
from fastapi import Header, HTTPException
from jwt import ExpiredSignatureError, InvalidSignatureError, InvalidTokenError

from app.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
ASYMMETRIC_ALGORITHMS = {"ES256", "RS256"}
JWKS_CACHE_TTL_SECONDS = 300
JWKS_REQUEST_TIMEOUT_SECONDS = 5
EXPECTED_JWK_KTY = {"ES256": "EC", "RS256": "RSA"}


@dataclass(frozen=True)
class JwksCacheEntry:
    document: dict[str, Any]
    fetched_at: int


HttpRequester = Callable[..., Any]
_JWKS_CACHE: dict[str, JwksCacheEntry] = {}


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    access_token: str


def _decode_jwt_segment(segment: str) -> dict[str, Any]:
    """JWT 세그먼트를 base64url 디코딩해 JSON 객체로 바꾼다."""
    padding = "=" * (-len(segment) % 4)
    decoded = base64.urlsafe_b64decode(f"{segment}{padding}".encode("ascii"))
    return json.loads(decoded.decode("utf-8"))


def _parse_bearer_token(authorization: str | None) -> str:
    """Authorization 헤더에서 Bearer 토큰만 추출한다."""
    if not authorization:
        raise ValueError("missing authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ValueError("invalid bearer token")
    return token.strip()


def _read_jwt_header(token: str) -> dict[str, Any]:
    """JWT 헤더를 안전하게 읽어 알고리즘 분기 기준을 만든다."""
    try:
        header_segment, _, _ = token.split(".")
    except ValueError as error:
        raise ValueError("invalid token format") from error

    try:
        return _decode_jwt_segment(header_segment)
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("invalid token format") from error


def _decode_hs256_supabase_jwt(token: str, jwt_secret: str) -> dict[str, Any]:
    """레거시 HS256 토큰을 로컬 HMAC 방식으로 검증한다."""
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as error:
        raise ValueError("invalid token format") from error

    header = _decode_jwt_segment(header_segment)
    if header.get("alg") != "HS256":
        raise ValueError("unsupported token algorithm")

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(
        jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    padding = "=" * (-len(signature_segment) % 4)
    actual_signature = base64.urlsafe_b64decode(f"{signature_segment}{padding}".encode("ascii"))
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("invalid token signature")

    payload = _decode_jwt_segment(payload_segment)
    expires_at = payload.get("exp")
    if expires_at is not None and int(expires_at) <= int(time.time()):
        raise ValueError("expired token")
    if not payload.get("sub"):
        raise ValueError("missing subject")
    return payload


def _build_jwks_url(supabase_url: str | None) -> str:
    """Supabase 프로젝트 URL에서 JWKS 엔드포인트를 만든다."""
    normalized = str(supabase_url or "").strip().rstrip("/")
    if not normalized:
        raise ValueError("SUPABASE_URL is not configured")
    return f"{normalized}/auth/v1/.well-known/jwks.json"


def _fetch_jwks_document(jwks_url: str, requester: HttpRequester) -> dict[str, Any]:
    """원격 JWKS 문서를 읽고 기본 구조를 검증한다."""
    try:
        response = requester(jwks_url, timeout=JWKS_REQUEST_TIMEOUT_SECONDS)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        elif int(getattr(response, "status_code", 200)) >= 400:
            raise RuntimeError("jwks request failed")
        document = response.json()
    except Exception as error:
        raise ValueError("authentication configuration is unavailable") from error

    if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
        raise ValueError("authentication configuration is unavailable")
    return document


def _load_jwks_document(
    supabase_url: str | None,
    requester: HttpRequester,
    *,
    force_refresh: bool,
) -> dict[str, Any]:
    """TTL 캐시를 고려해 JWKS 문서를 읽거나 새로고침한다."""
    jwks_url = _build_jwks_url(supabase_url)
    cache_entry = _JWKS_CACHE.get(jwks_url)
    now = int(time.time())
    if cache_entry and not force_refresh and now - cache_entry.fetched_at < JWKS_CACHE_TTL_SECONDS:
        return cache_entry.document

    document = _fetch_jwks_document(jwks_url, requester)
    _JWKS_CACHE[jwks_url] = JwksCacheEntry(document=document, fetched_at=now)
    return document


def _matches_jwk(key: dict[str, Any], algorithm: str) -> bool:
    """토큰 알고리즘과 호환되는 JWKS 키만 선택한다."""
    expected_kty = EXPECTED_JWK_KTY.get(algorithm)
    key_use = str(key.get("use") or "").strip().lower()
    key_alg = str(key.get("alg") or "").strip()
    key_kty = str(key.get("kty") or "").strip()
    if key_use and key_use != "sig":
        return False
    if expected_kty and key_kty and key_kty != expected_kty:
        return False
    if key_alg and key_alg != algorithm:
        return False
    return True


def _select_jwk_candidates(document: dict[str, Any], algorithm: str, kid: str | None) -> list[dict[str, Any]]:
    """알고리즘과 kid 기준으로 검증 후보 키 목록을 추린다."""
    matching_keys = [
        key for key in document.get("keys", []) if isinstance(key, dict) and _matches_jwk(key, algorithm)
    ]
    if kid:
        return [key for key in matching_keys if str(key.get("kid") or "").strip() == kid]
    return matching_keys


def _build_public_key(key: dict[str, Any], algorithm: str) -> Any:
    """JWKS 항목을 PyJWT가 검증 가능한 공개키 객체로 변환한다."""
    try:
        jwk_json = json.dumps(key)
        if algorithm == "ES256":
            return jwt.algorithms.ECAlgorithm.from_jwk(jwk_json)
        if algorithm == "RS256":
            return jwt.algorithms.RSAAlgorithm.from_jwk(jwk_json)
    except Exception as error:
        raise ValueError("authentication configuration is unavailable") from error
    raise ValueError("unsupported token algorithm")


def _decode_with_jwk(token: str, key: dict[str, Any], algorithm: str) -> dict[str, Any]:
    """단일 JWKS 키로 비대칭 JWT를 검증한다."""
    try:
        return jwt.decode(
            token,
            key=_build_public_key(key, algorithm),
            algorithms=[algorithm],
            options={"verify_aud": False},
        )
    except ExpiredSignatureError as error:
        raise ValueError("expired token") from error
    except InvalidSignatureError as error:
        raise ValueError("invalid token signature") from error
    except InvalidTokenError as error:
        raise ValueError("invalid token") from error


def _decode_asymmetric_supabase_jwt(
    token: str,
    header: dict[str, Any],
    supabase_url: str | None,
    requester: HttpRequester,
) -> dict[str, Any]:
    """JWKS 캐시와 강제 새로고침을 이용해 비대칭 JWT를 검증한다."""
    algorithm = str(header.get("alg") or "").strip()
    kid = str(header.get("kid") or "").strip() or None
    last_error: ValueError | None = None

    for force_refresh in (False, True):
        document = _load_jwks_document(supabase_url, requester, force_refresh=force_refresh)
        candidates = _select_jwk_candidates(document, algorithm, kid)
        if not candidates:
            last_error = ValueError("signing key not found")
            continue
        for key in candidates:
            try:
                return _decode_with_jwk(token, key, algorithm)
            except ValueError as error:
                if str(error) in {"invalid token signature", "signing key not found"}:
                    last_error = error
                    continue
                raise

    if last_error is None:
        raise ValueError("signing key not found")
    raise last_error


def decode_supabase_jwt(
    token: str,
    jwt_secret: str | None = None,
    supabase_url: str | None = None,
    requester: HttpRequester | None = None,
) -> dict[str, Any]:
    """Supabase JWT를 알고리즘별로 검증하고 payload를 반환한다."""
    header = _read_jwt_header(token)
    algorithm = str(header.get("alg") or "").strip()
    active_requester = requester or requests.get

    if algorithm in ASYMMETRIC_ALGORITHMS:
        payload = _decode_asymmetric_supabase_jwt(token, header, supabase_url, active_requester)
    elif algorithm == "HS256":
        if not jwt_secret:
            raise ValueError("HS256 fallback is unavailable")
        payload = _decode_hs256_supabase_jwt(token, jwt_secret)
    else:
        raise ValueError("unsupported token algorithm")

    if not payload.get("sub"):
        raise ValueError("missing subject")
    return payload


def build_authenticated_user(
    authorization: str | None,
    jwt_secret: str | None = None,
    supabase_url: str | None = None,
    requester: HttpRequester | None = None,
) -> AuthenticatedUser:
    """Authorization 헤더를 검증해 애플리케이션 사용자 컨텍스트를 만든다."""
    token = _parse_bearer_token(authorization)
    payload = decode_supabase_jwt(
        token,
        jwt_secret=jwt_secret,
        supabase_url=supabase_url,
        requester=requester,
    )
    return AuthenticatedUser(user_id=str(payload["sub"]), access_token=token)


def require_authenticated_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    """요청 헤더를 검증해 현재 로그인 사용자를 반환한다."""
    settings = get_settings(ROOT)
    if not settings.auth.supabase_url and not settings.auth.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="authentication is not configured")

    try:
        return build_authenticated_user(
            authorization,
            jwt_secret=settings.auth.supabase_jwt_secret,
            supabase_url=settings.auth.supabase_url,
        )
    except ValueError as error:
        detail = str(error)
        if detail in {"SUPABASE_URL is not configured", "authentication configuration is unavailable"}:
            raise HTTPException(status_code=500, detail="authentication is not configured") from error
        raise HTTPException(status_code=401, detail=detail) from error
