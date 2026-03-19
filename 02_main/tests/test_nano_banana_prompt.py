import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.extractor import build_nano_banana_prompt


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
