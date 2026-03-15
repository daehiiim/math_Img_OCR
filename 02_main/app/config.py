from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuthSettings:
    supabase_url: str | None
    supabase_anon_key: str | None
    supabase_jwt_secret: str | None


@dataclass(frozen=True)
class BillingSettings:
    stripe_secret_key: str | None
    stripe_webhook_secret: str | None


@dataclass(frozen=True)
class AppSettings:
    openai_api_key: str | None
    auth: AuthSettings
    billing: BillingSettings


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


def get_settings(root_path: Path) -> AppSettings:
    """OCR API가 필요로 하는 인증/과금 설정 묶음을 반환한다."""
    env_values = _load_env_file(root_path)

    return AppSettings(
        openai_api_key=_get_setting(env_values, "OPENAI_API_KEY"),
        auth=AuthSettings(
            supabase_url=_get_setting(env_values, "SUPABASE_URL"),
            supabase_anon_key=_get_setting(env_values, "SUPABASE_ANON_KEY"),
            supabase_jwt_secret=_get_setting(env_values, "SUPABASE_JWT_SECRET"),
        ),
        billing=BillingSettings(
            stripe_secret_key=_get_setting(env_values, "STRIPE_SECRET_KEY"),
            stripe_webhook_secret=_get_setting(env_values, "STRIPE_WEBHOOK_SECRET"),
        ),
    )
