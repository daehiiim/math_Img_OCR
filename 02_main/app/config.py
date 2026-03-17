from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuthSettings:
    supabase_url: str | None
    supabase_anon_key: str | None
    supabase_jwt_secret: str | None
    supabase_storage_bucket: str | None
    supabase_service_role_key: str | None


@dataclass(frozen=True)
class BillingSettings:
    polar_access_token: str | None
    polar_webhook_secret: str | None
    polar_server: str | None
    polar_product_single_id: str | None
    polar_product_starter_id: str | None
    polar_product_pro_id: str | None


@dataclass(frozen=True)
class AppSettings:
    openai_api_key: str | None
    database_url: str | None
    auth: AuthSettings
    billing: BillingSettings
    app_url: str | None = None
    cors_allow_origins: tuple[str, ...] = ()


def _load_env_file(root_path: Path) -> dict[str, str]:
    """프로젝트 루트의 .env.example 또는 apiKey.env 형식을 읽어 설정 후보를 만든다."""
    env_candidates = [root_path / ".env", root_path / "apiKey.env"]
    values: dict[str, str] = {}

    for path in env_candidates:
        if not path.exists():
            continue

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def _get_setting(env_values: dict[str, str], key: str) -> str | None:
    """환경변수와 파일 값을 같은 규칙으로 조회한다."""
    value = os.getenv(key) or env_values.get(key)
    if value is None or not value.strip():
        return None
    return value.strip()


def _normalize_url(value: str | None) -> str | None:
    """URL 설정값의 마지막 슬래시를 제거한다."""
    if value is None:
        return None
    normalized = value.strip().rstrip("/")
    return normalized or None


def _get_multi_setting(env_values: dict[str, str], key: str) -> tuple[str, ...]:
    """쉼표 구분 URL 설정값을 정규화된 튜플로 반환한다."""
    raw_value = _get_setting(env_values, key)
    if raw_value is None:
        return ()

    values = []
    for entry in raw_value.split(","):
        normalized = _normalize_url(entry)
        if normalized:
            values.append(normalized)
    return tuple(values)


def get_settings(root_path: Path) -> AppSettings:
    """OCR API가 필요로 하는 인증/과금 설정 묶음을 반환한다."""
    env_values = _load_env_file(root_path)

    return AppSettings(
        openai_api_key=_get_setting(env_values, "OPENAI_API_KEY"),
        database_url=_get_setting(env_values, "DATABASE_URL"),
        app_url=_normalize_url(_get_setting(env_values, "APP_URL")),
        cors_allow_origins=_get_multi_setting(env_values, "CORS_ALLOW_ORIGINS"),
        auth=AuthSettings(
            supabase_url=_get_setting(env_values, "SUPABASE_URL"),
            supabase_anon_key=_get_setting(env_values, "SUPABASE_ANON_KEY"),
            supabase_jwt_secret=_get_setting(env_values, "SUPABASE_JWT_SECRET"),
            supabase_storage_bucket=_get_setting(env_values, "SUPABASE_STORAGE_BUCKET"),
            supabase_service_role_key=_get_setting(env_values, "SUPABASE_SERVICE_ROLE_KEY"),
        ),
        billing=BillingSettings(
            polar_access_token=_get_setting(env_values, "POLAR_ACCESS_TOKEN"),
            polar_webhook_secret=_get_setting(env_values, "POLAR_WEBHOOK_SECRET"),
            polar_server=_get_setting(env_values, "POLAR_SERVER"),
            polar_product_single_id=_get_setting(env_values, "POLAR_PRODUCT_SINGLE_ID"),
            polar_product_starter_id=_get_setting(env_values, "POLAR_PRODUCT_STARTER_ID"),
            polar_product_pro_id=_get_setting(env_values, "POLAR_PRODUCT_PRO_ID"),
        ),
    )
