import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def test_get_settings_reads_env_file(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=file-openai-key",
                "SUPABASE_URL=https://example.supabase.co",
                "SUPABASE_ANON_KEY=file-anon-key",
                "SUPABASE_JWT_SECRET=file-jwt-secret",
                "STRIPE_SECRET_KEY=file-stripe-secret",
                "STRIPE_WEBHOOK_SECRET=file-webhook-secret",
            ]
        ),
        encoding="utf-8",
    )

    settings = get_settings(tmp_path)

    assert settings.openai_api_key == "file-openai-key"
    assert settings.auth.supabase_url == "https://example.supabase.co"
    assert settings.auth.supabase_anon_key == "file-anon-key"
    assert settings.auth.supabase_jwt_secret == "file-jwt-secret"
    assert settings.billing.stripe_secret_key == "file-stripe-secret"
    assert settings.billing.stripe_webhook_secret == "file-webhook-secret"


def test_get_settings_prefers_environment_variables(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=file-openai-key",
                "SUPABASE_URL=https://file.supabase.co",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    monkeypatch.setenv("SUPABASE_URL", "https://env.supabase.co")

    settings = get_settings(tmp_path)

    assert settings.openai_api_key == "env-openai-key"
    assert settings.auth.supabase_url == "https://env.supabase.co"
