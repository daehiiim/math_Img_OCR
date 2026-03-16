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
                "SUPABASE_STORAGE_BUCKET=ocr-assets",
                "SUPABASE_SERVICE_ROLE_KEY=file-service-role-key",
                "POLAR_ACCESS_TOKEN=file-polar-access-token",
                "POLAR_WEBHOOK_SECRET=file-polar-webhook-secret",
                "POLAR_SERVER=sandbox",
                "POLAR_PRODUCT_SINGLE_ID=prod_single",
                "POLAR_PRODUCT_STARTER_ID=prod_starter",
                "POLAR_PRODUCT_PRO_ID=prod_pro",
            ]
        ),
        encoding="utf-8",
    )

    settings = get_settings(tmp_path)

    assert settings.openai_api_key == "file-openai-key"
    assert settings.auth.supabase_url == "https://example.supabase.co"
    assert settings.auth.supabase_anon_key == "file-anon-key"
    assert settings.auth.supabase_jwt_secret == "file-jwt-secret"
    assert settings.auth.supabase_storage_bucket == "ocr-assets"
    assert settings.auth.supabase_service_role_key == "file-service-role-key"
    assert settings.billing.polar_access_token == "file-polar-access-token"
    assert settings.billing.polar_webhook_secret == "file-polar-webhook-secret"
    assert settings.billing.polar_server == "sandbox"
    assert settings.billing.polar_product_single_id == "prod_single"
    assert settings.billing.polar_product_starter_id == "prod_starter"
    assert settings.billing.polar_product_pro_id == "prod_pro"


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


def test_get_settings_reads_database_url(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DATABASE_URL=postgresql://postgres:secret@db.example.supabase.co:5432/postgres",
        encoding="utf-8",
    )

    settings = get_settings(tmp_path)

    assert settings.database_url == "postgresql://postgres:secret@db.example.supabase.co:5432/postgres"
