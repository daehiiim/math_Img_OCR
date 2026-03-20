import types
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.extractor import (
    _get_nano_banana_settings,
    _get_openai_api_key,
    build_nano_banana_prompt,
    generate_styled_image_with_nano_banana,
)


def _install_fake_google_genai(monkeypatch, captured: dict) -> None:
    """google-genai import 경로를 테스트용 가짜 모듈로 주입한다."""

    fake_google = types.ModuleType("google")
    fake_genai = types.ModuleType("google.genai")
    fake_types = types.ModuleType("google.genai.types")

    class FakeContent:
        """generate_content 호출 payload를 담는 테스트용 Content다."""

        def __init__(self, role: str, parts: list[object]) -> None:
            self.role = role
            self.parts = parts

    class FakePart:
        """텍스트와 바이너리 part 생성을 흉내 낸다."""

        @staticmethod
        def from_text(*, text: str) -> dict[str, str]:
            return {"type": "text", "text": text}

        @staticmethod
        def from_bytes(*, data: bytes, mime_type: str) -> dict[str, object]:
            return {"type": "bytes", "data": data, "mime_type": mime_type}

    class FakeModels:
        """generate_content 호출 인자를 캡처하고 이미지 응답을 반환한다."""

        def generate_content(self, **kwargs):
            captured["generate_content_kwargs"] = kwargs
            inline_data = type("InlineData", (), {"mime_type": "image/png", "data": b"fake-png"})()
            part = type("Part", (), {"inline_data": inline_data})()
            content = type("Content", (), {"parts": [part]})()
            candidate = type("Candidate", (), {"content": content})()
            return type("Response", (), {"candidates": [candidate]})()

    class FakeClient:
        """Client 초기화 인자를 캡처한다."""

        def __init__(self, **kwargs) -> None:
            captured["client_kwargs"] = kwargs
            self.models = FakeModels()

    fake_types.Content = FakeContent
    fake_types.Part = FakePart
    fake_genai.Client = FakeClient
    fake_genai.types = fake_types
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)


def test_build_nano_banana_prompt_includes_geometry_constraints():
    prompt = build_nano_banana_prompt("geometry", "csat_v1")

    assert "Korean CSAT exam style" in prompt
    assert "parallel line markers" in prompt
    assert "tick marks" in prompt
    assert "2D line art" in prompt


def test_build_nano_banana_prompt_includes_illustration_constraints():
    prompt = build_nano_banana_prompt("illustration", "csat_v1")

    assert "textbook-style monochrome illustration" in prompt
    assert "major contours" in prompt
    assert "Keep the count and direction of people or objects" in prompt


def test_build_nano_banana_prompt_falls_back_to_generic_when_kind_is_unknown():
    prompt = build_nano_banana_prompt("unknown-kind", "csat_v1")

    assert "Keep only the visual information needed to solve the math problem" in prompt
    assert "Do not add answer choice numbers" in prompt


def test_build_nano_banana_prompt_supports_math_general_geometry_rules():
    prompt = build_nano_banana_prompt("geometry", "math_general_v1")

    assert "general math worksheet or textbook-style image" in prompt
    assert "Preserve labels, numbers, angle markers" in prompt
    assert "Do not add answer choice numbers" in prompt


def test_build_nano_banana_prompt_raises_when_prompt_asset_is_missing(tmp_path, monkeypatch):
    missing_assets_dir = tmp_path / "missing-prompts"
    monkeypatch.setattr("app.pipeline.extractor.NANO_BANANA_PROMPTS_DIR", missing_assets_dir)

    with pytest.raises(ValueError, match="NANO_BANANA_PROMPT_ASSET_MISSING"):
        build_nano_banana_prompt("geometry", "csat_v1")


def test_get_openai_api_key_does_not_read_legacy_api_key_env(tmp_path):
    legacy_path = tmp_path / "apiKey.env"
    legacy_path.write_text(
        "OPENAI_API_KEY=legacy-openai-key",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        _get_openai_api_key(tmp_path)


def test_get_nano_banana_settings_does_not_read_legacy_api_key_env(tmp_path):
    legacy_path = tmp_path / "apiKey.env"
    legacy_path.write_text(
        "\n".join(
            [
                "NANO_BANANA_MODEL=legacy-model",
                "NANO_BANANA_PROJECT_ID=legacy-project",
                "NANO_BANANA_LOCATION=us-central1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="NANO_BANANA_MODEL"):
        _get_nano_banana_settings(tmp_path)


def test_get_nano_banana_settings_requires_gemini_api_key_for_gemini_provider(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "NANO_BANANA_PROVIDER=gemini_api",
                "NANO_BANANA_MODEL=gemini-2.5-flash-image-preview",
                "NANO_BANANA_PROMPT_VERSION=csat_v1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        _get_nano_banana_settings(tmp_path)


def test_get_nano_banana_settings_rejects_unsupported_provider(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "NANO_BANANA_PROVIDER=invalid-provider",
                "NANO_BANANA_MODEL=gemini-2.5-flash-image-preview",
                "NANO_BANANA_PROMPT_VERSION=csat_v1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported NANO_BANANA_PROVIDER: invalid-provider"):
        _get_nano_banana_settings(tmp_path)


def test_generate_styled_image_with_nano_banana_uses_math_general_prompt_assets(
    tmp_path,
    monkeypatch,
):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "NANO_BANANA_PROVIDER=gemini_api",
                "NANO_BANANA_MODEL=gemini-2.5-flash-image-preview",
                "NANO_BANANA_PROMPT_VERSION=math_general_v1",
                "GEMINI_API_KEY=test-gemini-api-key",
            ]
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    _install_fake_google_genai(monkeypatch, captured)

    result = generate_styled_image_with_nano_banana(
        tmp_path,
        b"input-image",
        prompt_kind="generic",
    )

    assert result == b"fake-png"
    text_part = captured["generate_content_kwargs"]["contents"][0].parts[0]["text"]
    assert "general math worksheet or textbook-style image" in text_part
    assert "Keep only the problem-solving visual information" in text_part


@pytest.mark.parametrize(
    ("provider", "extra_lines", "expected_client_kwargs"),
    [
        (
            "vertex",
            [
                "NANO_BANANA_PROJECT_ID=test-project",
                "NANO_BANANA_LOCATION=us-central1",
            ],
            {
                "vertexai": True,
                "project": "test-project",
                "location": "us-central1",
            },
        ),
        (
            "gemini_api",
            ["GEMINI_API_KEY=test-gemini-api-key"],
            {"api_key": "test-gemini-api-key"},
        ),
    ],
)
def test_generate_styled_image_with_nano_banana_initializes_provider_specific_client(
    tmp_path,
    monkeypatch,
    provider,
    extra_lines,
    expected_client_kwargs,
):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                f"NANO_BANANA_PROVIDER={provider}",
                "NANO_BANANA_MODEL=gemini-2.5-flash-image-preview",
                "NANO_BANANA_PROMPT_VERSION=csat_v1",
                *extra_lines,
            ]
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    _install_fake_google_genai(monkeypatch, captured)

    result = generate_styled_image_with_nano_banana(
        tmp_path,
        b"input-image",
        prompt_kind="geometry",
    )

    assert result == b"fake-png"
    assert captured["client_kwargs"] == expected_client_kwargs
    assert captured["generate_content_kwargs"]["model"] == "gemini-2.5-flash-image-preview"
