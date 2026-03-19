import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.extractor import _get_nano_banana_settings, _get_openai_api_key, build_nano_banana_prompt


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
