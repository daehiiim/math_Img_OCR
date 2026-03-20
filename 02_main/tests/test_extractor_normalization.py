from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline import extractor


class FakeResponse:
    """테스트용 HTTP 응답을 흉내 낸다."""

    def __init__(self, payload: dict, *, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ""

    def json(self) -> dict:
        return self._payload


def test_analyze_region_with_gpt_normalizes_first_problem_number_and_math_markup(monkeypatch):
    """OCR 결과는 첫 문제 번호만 제거하고 수식 표기는 HWP 친화 형식으로 정규화한다."""

    def fake_post(*args, **kwargs):
        model_payload = {
            "text_blocks": [
                "1. \\triangle ABC에서 \\angle A = 30^\\circ 이다",
                "12) \\mathrm{AB} = \\text{CD}",
            ],
            "formulas": [
                "<math>\\triangle ABC</math>",
                "<math>\\angle A = 30^\\circ</math>",
            ],
            "stylizable_images": [{"bbox": [1, 2, 3, 4], "kind": "geometry"}],
        }
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(model_payload, ensure_ascii=False),
                        }
                    }
                ]
            },
            headers={"x-request-id": "req-123"},
        )

    monkeypatch.setattr(extractor.requests, "post", fake_post)

    result = extractor.analyze_region_with_gpt(
        Path("unused"),
        b"image-bytes",
        "mixed",
        api_key="sk-test",
        include_image_detection=True,
    )

    assert result["ocr_text"] == "△ABC에서 ∠A = 30° 이다\n12) AB = CD"
    assert result["mathml"] == "<math>△ABC</math>\n<math>∠A = 30°</math>"
    assert result["has_stylizable_image"] is True
    assert result["image_bbox"] == [1, 2, 3, 4]
    assert result["image_kind"] == "geometry"


def test_analyze_region_with_gpt_preserves_numbered_lines_after_first_line(monkeypatch):
    """첫 줄 이후의 번호 매기기는 본문 정보로 유지해야 한다."""

    def fake_post(*args, **kwargs):
        model_payload = {
            "text_blocks": [
                "3. 함수 f(x)에 대하여",
                "1. 첫 번째 조건",
                "2) 두 번째 조건",
            ],
            "formulas": [],
            "stylizable_images": [],
        }
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(model_payload, ensure_ascii=False),
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(extractor.requests, "post", fake_post)

    result = extractor.analyze_region_with_gpt(
        Path("unused"),
        b"image-bytes",
        "mixed",
        api_key="sk-test",
    )

    assert result["ocr_text"] == "함수 f(x)에 대하여\n1. 첫 번째 조건\n2) 두 번째 조건"


def test_generate_explanation_with_gpt_normalizes_math_markup(monkeypatch):
    """해설 문장은 유지하고 수식 표기만 정규화한다."""

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "1. 따라서 <math>\\triangle ABC</math> 와 <math>\\angle AOB = 30^\\circ</math> 를 사용한다.",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(extractor.requests, "post", fake_post)

    result = extractor.generate_explanation_with_gpt(
        Path("unused"),
        b"image-bytes",
        "ocr text",
        "<math>\\triangle ABC</math>",
        api_key="sk-test",
    )

    assert result == "1. 따라서 <math>△ABC</math> 와 <math>∠AOB = 30°</math> 를 사용한다."
