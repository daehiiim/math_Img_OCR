import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.schema import (
    ExtractorContext,
    FigureContext,
    JobPipelineContext,
    RegionContext,
    RegionPipelineContext,
)


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "hwpforge_generated_canonical_sample.json"


class DummyWarnings:
    """테스트용 경고 수집기를 흉내 낸다."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def add(self, code: str, detail: str) -> None:
        """경고 항목을 순서대로 저장한다."""
        self.items.append((code, detail))


def make_png_fixture(root_path: Path) -> str:
    """HwpForge export IR 테스트용 이미지 파일을 만든다."""
    image_path = root_path / "assets" / "q1.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
            "0000000C4944415408D763F8FFFF3F0005FE02FEA7D6059B0000000049454E44AE426082"
        )
    )
    return "assets/q1.png"


def make_reference_like_job(image_path: str) -> JobPipelineContext:
    """수식과 보기, 해설이 함께 있는 문항 fixture를 만든다."""
    return JobPipelineContext(
        job_id="job-reference-1",
        file_name="uploaded_image.png",
        image_url="user-123/job-reference-1/input/uploaded_image.png",
        image_width=459,
        image_height=213,
        status="completed",
        created_at="2026-03-18T00:00:00+00:00",
        updated_at="2026-03-18T00:00:00+00:00",
        regions=[
            RegionPipelineContext(
                context=RegionContext(
                    id="q1",
                    polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
                    type="mixed",
                    order=1,
                ),
                extractor=ExtractorContext(
                    ocr_text="\n".join(
                        [
                            "△ABC에서 AB 위의 점 E와 AC 위의 점 D에 대하여",
                            "∠ABC = ∠ADE이고, AB = 14cm, AE = 6cm, AD = 8cm,",
                            "DC = x(cm)일 때, x의 값은? [4점]",
                            "① <math>1</math> ② <math>3/2</math> ③ <math>9/4</math> ④ <math>7/3</math> ⑤ <math>5/2</math>",
                        ]
                    ),
                    explanation="\n".join(
                        [
                            "주어진 조건에서 E는 AB 위, D는 AC 위에 있으므로",
                            "<math>ANGLE  BAC`=` ANGLE DAE</math> 이다. 또한 <math>ANGLE  ABC`=` ANGLE  ADE</math> 이므로",
                            "삼각형 <math>ABC</math> 와 삼각형 <math>ADE</math> 는 서로 닮음이다.",
                        ]
                    ),
                ),
                figure=FigureContext(image_crop_url=image_path),
                status="completed",
                success=True,
            )
        ],
    )


def load_template_document() -> dict:
    """검증된 HwpForge sample JSON fixture를 읽어 온다."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_build_hwpforge_export_ir_collects_images_and_choices(tmp_path):
    """IR builder는 보기 5개와 BinData 이미지 참조를 함께 만들어야 한다."""
    from app.pipeline.hwpforge_json_builder import build_hwpforge_export_ir

    root_path = tmp_path / "runtime"
    image_path = make_png_fixture(root_path)
    bindata_dir = tmp_path / "build" / "BinData"
    bindata_dir.mkdir(parents=True, exist_ok=True)
    warnings = DummyWarnings()

    export_ir, images_info = build_hwpforge_export_ir(
        root_path=root_path,
        job=make_reference_like_job(image_path),
        bindata_dir=bindata_dir,
        year="2031",
        warnings=warnings,
    )

    assert warnings.items == []
    assert export_ir["year"] == "2031"
    assert export_ir["regions"][0]["choices"] == ["1", "3/2", "9/4", "7/3", "5/2"]
    assert export_ir["regions"][0]["image"]["bindata_id"] == "image2"
    assert images_info == [{"id": "image2", "filename": "image2.png", "ext": "png"}]


def test_build_exported_document_keeps_problem_image_choice_explanation_order():
    """JSON builder는 문항-이미지-보기-해설 순서와 수식 script를 유지해야 한다."""
    from app.pipeline.hwpforge_json_builder import build_exported_document_from_template

    template_document = load_template_document()
    export_ir = {
        "year": "2031",
        "regions": [
            {
                "number": 1,
                "stem": "닮음 관계를 이용해 y의 값을 구하시오.",
                "choices": ["2", "5/3", "11/4", "8/3", "7/2"],
                "image": {"bindata_id": "image2", "ext": "png"},
                "explanation_lines": [
                    "주어진 조건에서 E는 AB 위, D는 AC 위에 있으므로",
                    "<math>ANGLE QPR = ANGLE SRT</math> 이다. 또한 <math>ANGLE PQR = ANGLE STR</math> 이므로",
                    "삼각형 <math>PQR</math> 와 삼각형 <math>SRT</math> 는 서로 닮음이다.",
                ],
            }
        ],
    }

    exported = build_exported_document_from_template(template_document, export_ir)
    paragraphs = exported["document"]["sections"][0]["paragraphs"]

    assert paragraphs[0]["runs"][3]["content"]["Text"] == "1."
    assert paragraphs[0]["runs"][4]["content"]["Text"] == "닮음 관계를 이용해 y의 값을 구하시오."
    assert paragraphs[2]["runs"][0]["content"]["Image"]["path"] == "BinData/image2"
    assert [run["content"]["Control"]["Equation"]["script"] for run in paragraphs[3]["runs"] if "Control" in run["content"]] == [
        "2",
        "5/3",
        "11/4",
        "8/3",
        "7/2",
    ]
    assert paragraphs[5]["runs"][0]["content"]["Text"] == "[해설]"
    assert paragraphs[7]["runs"][0]["content"]["Text"] == "주어진 조건에서 E는 AB 위, D는 AC 위에 있으므로"
    assert [run["content"]["Control"]["Equation"]["script"] for run in paragraphs[8]["runs"] if "Control" in run["content"]] == [
        "ANGLE QPR = ANGLE SRT",
        "ANGLE PQR = ANGLE STR",
    ]


def test_build_exported_document_converts_problem_stem_math_into_mixed_runs():
    """문제 본문 `<math>`는 literal text가 아니라 text/equation run으로 분해돼야 한다."""
    from app.pipeline.hwpforge_json_builder import build_exported_document_from_template

    exported = build_exported_document_from_template(
        load_template_document(),
        {
            "year": "2031",
            "regions": [
                {
                    "number": 1,
                    "stem": "길이 <math>AB</math> 와 점 <math>E</math> 를 구하라.",
                    "choices": None,
                    "image": None,
                    "explanation_lines": [],
                }
            ],
        },
    )

    problem_runs = exported["document"]["sections"][0]["paragraphs"][0]["runs"]

    assert [run["content"]["Text"] for run in problem_runs[4:] if "Text" in run["content"]] == [
        "길이 ",
        " 와 점 ",
        " 를 구하라.",
    ]
    assert [run["content"]["Control"]["Equation"]["script"] for run in problem_runs[4:] if "Control" in run["content"]] == [
        "AB",
        "E",
    ]
    assert all("<math>" not in run["content"].get("Text", "") for run in problem_runs[4:])


def test_build_exported_document_resizes_equation_widths_from_script_length():
    """짧은 수식과 긴 수식은 템플릿 고정 폭이 아니라 script 길이에 따라 다른 폭을 가져야 한다."""
    from app.pipeline.hwpforge_json_builder import build_exported_document_from_template

    exported = build_exported_document_from_template(
        load_template_document(),
        {
            "year": "2031",
            "regions": [
                {
                    "number": 1,
                    "stem": "닮음 관계를 이용해 값을 구하시오.",
                    "choices": [
                        "E",
                        "3 over 2",
                        "AB : AD = BC : AE",
                        "x = 21 over 4 - 8 = 9 over 4",
                        "AC",
                    ],
                    "image": None,
                    "explanation_lines": [
                        "<math>AB</math> 와 <math>x = 21 over 4 - 8 = 9 over 4</math> 를 비교한다.",
                    ],
                }
            ],
        },
    )

    paragraphs = exported["document"]["sections"][0]["paragraphs"]
    choice_widths = {
        run["content"]["Control"]["Equation"]["script"]: run["content"]["Control"]["Equation"]["width"]
        for run in paragraphs[2]["runs"]
        if "Control" in run["content"]
    }
    explanation_widths = {
        run["content"]["Control"]["Equation"]["script"]: run["content"]["Control"]["Equation"]["width"]
        for run in paragraphs[6]["runs"]
        if "Control" in run["content"]
    }

    assert choice_widths["AC"] < choice_widths["AB : AD = BC : AE"]
    assert choice_widths["AB : AD = BC : AE"] < choice_widths["x = 21 over 4 - 8 = 9 over 4"]
    assert explanation_widths["AB"] < explanation_widths["x = 21 over 4 - 8 = 9 over 4"]


def test_clone_paragraph_drops_stale_linesegarray_cache():
    """문단 복제본은 stale linesegarray cache를 들고 가지 않아야 한다."""
    from app.pipeline.hwpforge_json_builder import _clone_paragraph

    paragraph = {
        "runs": [],
        "para_shape_id": 0,
        "column_break": False,
        "page_break": False,
        "style_id": 0,
        "linesegarray": {"stale": True},
    }

    cloned = _clone_paragraph(paragraph)

    assert "linesegarray" in paragraph
    assert "linesegarray" not in cloned


def test_build_hwpforge_export_ir_prefers_markdown_fields_when_present(tmp_path):
    """Markdown 필드가 있으면 legacy text 대신 그 값을 export IR에 써야 한다."""
    from app.pipeline.hwpforge_json_builder import build_hwpforge_export_ir

    root_path = tmp_path / "runtime"
    image_path = make_png_fixture(root_path)
    bindata_dir = tmp_path / "build" / "BinData"
    bindata_dir.mkdir(parents=True, exist_ok=True)
    warnings = DummyWarnings()
    job = make_reference_like_job(image_path)
    job.regions[0].extractor.problem_markdown = "\n".join(
        [
            "닮음 관계를 이용해 값을 구하시오.",
            "① $2$ ② $5/3$ ③ $11/4$ ④ $8/3$ ⑤ $7/2$",
        ]
    )
    job.regions[0].extractor.explanation_markdown = "\n".join(
        [
            "첫째 줄",
            "$ANGLE QPR = ANGLE SRT$ 이다.",
        ]
    )

    export_ir, _images_info = build_hwpforge_export_ir(
        root_path=root_path,
        job=job,
        bindata_dir=bindata_dir,
        year="2031",
        warnings=warnings,
    )

    assert warnings.items == []
    assert export_ir["regions"][0]["stem"] == "닮음 관계를 이용해 값을 구하시오."
    assert export_ir["regions"][0]["choices"] == ["2", "5/3", "11/4", "8/3", "7/2"]
    assert export_ir["regions"][0]["explanation_lines"] == ["첫째 줄", "<math>ANGLE QPR = ANGLE SRT</math> 이다."]
