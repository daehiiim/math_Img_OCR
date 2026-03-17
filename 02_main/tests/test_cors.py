import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))


def _load_main_module(monkeypatch, *, app_url: str | None, cors_allow_origins: str | None = None):
    if app_url is None:
        monkeypatch.delenv("APP_URL", raising=False)
    else:
        monkeypatch.setenv("APP_URL", app_url)

    if cors_allow_origins is None:
        monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", cors_allow_origins)

    sys.modules.pop("app.main", None)
    import app.main as main_module

    return importlib.reload(main_module)


def test_cors_allows_app_url_when_explicit_origins_are_missing(monkeypatch):
    main_module = _load_main_module(monkeypatch, app_url="https://mathtohwp.vercel.app/", cors_allow_origins=None)
    client = TestClient(main_module.app)

    response = client.options(
        "/billing/catalog",
        headers={
            "Origin": "https://mathtohwp.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://mathtohwp.vercel.app"


def test_cors_rejects_localhost_without_explicit_allow_list(monkeypatch):
    main_module = _load_main_module(monkeypatch, app_url="https://mathtohwp.vercel.app/", cors_allow_origins=None)
    client = TestClient(main_module.app)

    response = client.options(
        "/billing/catalog",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
