import importlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


def _reload_main_module():
    """환경변수 변경 후 main 모듈을 새 설정으로 다시 읽는다."""
    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    return importlib.import_module("app.main")


def test_resolve_cors_settings_uses_local_defaults_in_development(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGIN_REGEX", raising=False)

    main_module = _reload_main_module()
    allowed_origins, allow_origin_regex = main_module.resolve_cors_settings()

    assert "http://localhost:5173" in allowed_origins
    assert "http://127.0.0.1:4173" in allowed_origins
    assert allow_origin_regex == main_module.DEFAULT_LOCAL_CORS_ORIGIN_REGEX


def test_resolve_cors_settings_disables_local_regex_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://mathtohwp.vercel.app")
    monkeypatch.delenv("CORS_ALLOW_ORIGIN_REGEX", raising=False)

    main_module = _reload_main_module()
    allowed_origins, allow_origin_regex = main_module.resolve_cors_settings()

    assert allowed_origins == ["https://mathtohwp.vercel.app"]
    assert allow_origin_regex is None
