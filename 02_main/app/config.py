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
    openai_key_encryption_secret: str | None
    database_url: str | None
    auth: AuthSettings
    billing: BillingSettings
    openai_base_url: str | None = None
    nano_banana_model: str | None = None
    nano_banana_project_id: str | None = None
    nano_banana_location: str | None = None
    nano_banana_prompt_version: str = "csat_v1"
    hwpx_skill_dir: str | None = None
    app_url: str | None = None
    cors_allow_origins: tuple[str, ...] = ()

SUPPORTED_NANO_BANANA_PROMPT_VERSIONS = ("csat_v1",)


def _load_env_file(root_path: Path) -> dict[str, str]:
    """백엔드 런타임 기준인 root_path/.env 파일을 읽어 설정 후보를 만든다."""
    env_candidates = [root_path / ".env"]
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


def _get_nano_banana_prompt_version(env_values: dict[str, str]) -> str:
    """지원하는 Nano Banana 프롬프트 버전만 허용한다."""
    version = _get_setting(env_values, "NANO_BANANA_PROMPT_VERSION") or "csat_v1"
    if version in SUPPORTED_NANO_BANANA_PROMPT_VERSIONS:
        return version
    raise ValueError(f"Unsupported NANO_BANANA_PROMPT_VERSION: {version}")


def get_settings(root_path: Path) -> AppSettings:
    """OCR API가 필요로 하는 인증/과금 설정 묶음을 반환한다."""
    env_values = _load_env_file(root_path)

    return AppSettings(
        openai_api_key=_get_setting(env_values, "OPENAI_API_KEY"),
        openai_base_url=_normalize_url(_get_setting(env_values, "OPENAI_BASE_URL")),
        openai_key_encryption_secret=_get_setting(env_values, "OPENAI_KEY_ENCRYPTION_SECRET"),
        nano_banana_model=_get_setting(env_values, "NANO_BANANA_MODEL"),
        nano_banana_project_id=_get_setting(env_values, "NANO_BANANA_PROJECT_ID"),
        nano_banana_location=_get_setting(env_values, "NANO_BANANA_LOCATION"),
        nano_banana_prompt_version=_get_nano_banana_prompt_version(env_values),
        database_url=_get_setting(env_values, "DATABASE_URL"),
        hwpx_skill_dir=_get_setting(env_values, "HWPX_SKILL_DIR"),
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

