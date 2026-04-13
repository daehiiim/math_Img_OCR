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


def test_analyze_region_with_gpt_prefers_ordered_segments_for_raw_and_display_fields(monkeypatch):
    """ordered segment가 있으면 raw transcript는 보존하고 legacy OCR만 파생해야 한다."""

    def fake_post(*args, **kwargs):
        model_payload = {
            "ordered_segments": [
                {"type": "text", "content": "1. 정답은 ", "source_order": 0},
                {"type": "math", "content": "\\frac{3}{2}", "source_order": 1},
                {"type": "text", "content": " 이다.\n① ", "source_order": 2},
                {"type": "math", "content": "1", "source_order": 3},
                {"type": "text", "content": " ② ", "source_order": 4},
                {"type": "math", "content": "3/2", "source_order": 5},
            ],
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

    assert result["raw_transcript"] == "1. 정답은 <math>\\frac{3}{2}</math> 이다.\n① <math>1</math> ② <math>3/2</math>"
    assert result["ocr_text"] == "정답은 <math>3/2</math> 이다.\n① <math>1</math> ② <math>3/2</math>"
    assert result["ordered_segments"] == [
        {"type": "text", "content": "1. 정답은 ", "source_order": 0},
        {"type": "math", "content": "\\frac{3}{2}", "source_order": 1},
        {"type": "text", "content": " 이다.\n① ", "source_order": 2},
        {"type": "math", "content": "1", "source_order": 3},
        {"type": "text", "content": " ② ", "source_order": 4},
        {"type": "math", "content": "3/2", "source_order": 5},
    ]


def test_generate_explanation_with_gpt_returns_structured_answer_payload(monkeypatch):
    """해설 생성은 Markdown+LaTeX와 검증용 정답 정보를 함께 반환한다."""

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "explanation_lines": [
                                        "1. 따라서 <math>\\triangle ABC</math> 와 <math>\\angle AOB = 30^\\circ</math> 를 사용한다."
                                    ],
                                    "final_answer_index": 3,
                                    "final_answer_value": "<math>\\frac{9}{4}</math>",
                                    "confidence": 0.87,
                                    "reason_summary": "닮음비를 이용해 값을 결정한다.",
                                },
                                ensure_ascii=False,
                            ),
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

    assert result == {
        "explanation_lines": ["1. 따라서 $\\triangle ABC$ 와 $\\angle AOB = 30^\\circ$ 를 사용한다."],
        "final_answer_index": 3,
        "final_answer_value": "$\\frac{9}{4}$",
        "confidence": 0.87,
        "reason_summary": "닮음비를 이용해 값을 결정한다.",
    }
