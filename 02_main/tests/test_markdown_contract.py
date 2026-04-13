from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.markdown_contract import (
    MARKDOWN_VERSION,
    bridge_legacy_markup_to_markdown,
    markdown_to_hwp_legacy_markup,
    ordered_segments_to_markdown,
)


def test_ordered_segments_to_markdown_preserves_problem_number_and_latex() -> None:
    """ordered segment 기반 Markdown은 plain text와 문제 번호를 그대로 보존해야 한다."""
    markdown = ordered_segments_to_markdown(
        [
            {"type": "text", "content": "1. 문제 본문 ", "source_order": 0},
            {"type": "math", "content": r"\frac{1}{2}", "source_order": 1},
            {"type": "text", "content": " 입니다.", "source_order": 2},
        ]
    )

    assert markdown == r"1. 문제 본문 $\frac{1}{2}$ 입니다."
    assert MARKDOWN_VERSION == "mathocr_markdown_latex_v2"


def test_bridge_legacy_markup_to_markdown_keeps_plain_text_and_converts_math() -> None:
    """구형 `<math>` 본문은 plain text를 건드리지 않고 Markdown 수식으로만 바꿔야 한다."""
    markdown = bridge_legacy_markup_to_markdown("1. 정답은 <math>\\frac{1}{2}</math> 입니다.")

    assert markdown == r"1. 정답은 $\frac{1}{2}$ 입니다."


def test_markdown_to_hwp_legacy_markup_converts_latex_only_for_export() -> None:
    """export 단계에서는 Markdown 수식을 HWP 친화 `<math>` 스크립트로만 바꿔야 한다."""
    restored = markdown_to_hwp_legacy_markup(r"정답은 $\frac{1}{2}$ 와 $\triangle ABC$ 입니다.")

    assert restored == "정답은 <math>1/2</math> 와 <math>△ ABC</math> 입니다."
