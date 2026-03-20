import importlib
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from lxml import etree
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.schema import (
    ExtractorContext,
    FigureContext,
    JobPipelineContext,
    RegionContext,
    RegionPipelineContext,
)

REQUIRED_RUNTIME_FILES = (
    Path("scripts/xml_primitives.py"),
    Path("scripts/exam_helpers.py"),
    Path("scripts/hwpx_utils.py"),
    Path("templates/base/mimetype"),
    Path("templates/base/BinData/image1.bmp"),
    Path("templates/base/Contents/header.xml"),
    Path("templates/base/Contents/content.hpf"),
    Path("templates/base/Contents/masterpage0.xml"),
    Path("templates/base/Contents/masterpage1.xml"),
    Path("templates/base/Contents/section0.xml"),
)
OPTIONAL_RUNTIME_FILES = (
    Path("templates/base/settings.xml"),
    Path("templates/base/version.xml"),
    Path("templates/base/META-INF/container.rdf"),
    Path("templates/base/META-INF/container.xml"),
    Path("templates/base/META-INF/manifest.xml"),
    Path("templates/base/Preview/PrvImage.png"),
    Path("templates/base/Preview/PrvText.txt"),
)
NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}
REFERENCE_HWPX_PATH = Path(__file__).resolve().parents[2] / "templates" / "result_answer.hwpx"


def make_png_bytes(width: int = 32, height: int = 24) -> bytes:
    """테스트용 PNG 바이트를 만든다."""
    image = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def load_exporter_module():
    """exporter 모듈을 매 테스트마다 새로 import한다."""
    sys.modules.pop("app.pipeline.exporter", None)
    return importlib.import_module("app.pipeline.exporter")


def copy_runtime_bundle(target_dir: Path) -> Path:
    """vendored runtime bundle을 임시 경로로 복사한다."""
    source_dir = Path(__file__).resolve().parents[1] / "vendor" / "hwpxskill-math"
    for relative_path in REQUIRED_RUNTIME_FILES + OPTIONAL_RUNTIME_FILES:
        source_path = source_dir / relative_path
        destination_path = target_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(source_path.read_bytes())
    return target_dir


def make_export_job(image_path: str) -> JobPipelineContext:
    """최소 HWPX export fixture를 만든다."""
    return JobPipelineContext(
        job_id="job-export-1",
        file_name="uploaded_image.png",
        image_url="user-123/job-export-1/input/uploaded_image.png",
        image_width=32,
        image_height=24,
        status="completed",
        created_at="2026-03-18T00:00:00+00:00",
        updated_at="2026-03-18T00:00:00+00:00",
        regions=[
            RegionPipelineContext(
                context=RegionContext(
                    id="q1",
                    polygon=[[0, 0], [8, 0], [8, 8], [0, 8]],
                    type="diagram",
                    order=1,
                ),
                extractor=ExtractorContext(
                    ocr_text="문제 본문",
                    explanation="해설 본문",
                ),
                figure=FigureContext(image_crop_url=image_path),
                status="completed",
                success=True,
            )
        ],
    )


def make_reference_like_job(image_path: str) -> JobPipelineContext:
    """`result_answer`와 유사한 문항 구조 fixture를 만든다."""
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


def read_archive_xml(hwpx_path: Path, inner_path: str):
    """HWPX zip 안 XML을 파싱해 반환한다."""
    with ZipFile(hwpx_path, "r") as archive:
        return etree.fromstring(archive.read(inner_path))


def read_reference_xml(inner_path: str):
    """레퍼런스 HWPX 안 XML을 파싱해 반환한다."""
    with ZipFile(REFERENCE_HWPX_PATH, "r") as archive:
        return etree.fromstring(archive.read(inner_path))


def direct_paragraphs(root) -> list:
    """section root 직계 문단만 반환한다."""
    return root.findall("hp:p", NS)


def count_header_defs(header_root) -> tuple[int, int, int]:
    """header 정의 개수를 반환한다."""
    return (
        len(header_root.findall(".//hh:charPr", NS)),
        len(header_root.findall(".//hh:paraPr", NS)),
        len(header_root.findall(".//hh:style", NS)),
    )


def make_runtime_paths(module, tmp_path, monkeypatch):
    """exporter 테스트용 runtime 환경을 만든다."""
    app_root = tmp_path / "02_main"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    monkeypatch.setattr(module, "ROOT", app_root)
    monkeypatch.setattr(module, "_get_codex_home", lambda: tmp_path / "missing-codex-home")
    monkeypatch.setattr(module, "_get_home_dir", lambda: tmp_path / "missing-home")
    root_path = tmp_path / "runtime"
    image_relative_path = Path("assets/q1.png")
    image_path = root_path / image_relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes(width=459, height=213))
    return root_path, image_relative_path


def test_exporter_module_import_is_lazy():
    """exporter import는 runtime 없이 성공해야 한다."""
    module = load_exporter_module()
    assert callable(module.export_hwpx)


def test_resolve_hwpx_runtime_prefers_configured_skill_dir(tmp_path):
    """설정 경로가 유효하면 가장 먼저 선택해야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    configured_dir = copy_runtime_bundle(tmp_path / "configured-skill")
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    runtime = module._resolve_hwpx_runtime(
        app_root=app_root,
        configured_skill_dir=str(configured_dir),
        codex_home=tmp_path / "codex-home",
        home_dir=tmp_path / "home",
    )
    assert runtime.skill_dir == configured_dir


def test_resolve_hwpx_runtime_uses_vendored_fallback(tmp_path):
    """설정 경로가 없으면 vendored bundle을 쓴다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    vendored_dir = copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    runtime = module._resolve_hwpx_runtime(
        app_root=app_root,
        configured_skill_dir=None,
        codex_home=tmp_path / "codex-home",
        home_dir=tmp_path / "home",
    )
    assert runtime.skill_dir == vendored_dir


def test_resolve_hwpx_runtime_reports_checked_paths_and_missing_files(tmp_path):
    """모든 후보가 실패하면 경로와 누락 파일을 함께 보여줘야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "02_main"
    configured_dir = tmp_path / "missing-configured"
    with pytest.raises(FileNotFoundError) as exc_info:
        module._resolve_hwpx_runtime(
            app_root=app_root,
            configured_skill_dir=str(configured_dir),
            codex_home=tmp_path / "missing-codex-home",
            home_dir=tmp_path / "missing-home",
        )
    message = str(exc_info.value)
    assert "HWPX export runtime not found." in message
    assert str(configured_dir) in message
    assert "templates/base/Contents/masterpage0.xml" in message
    assert "templates/base/BinData/image1.bmp" in message


def test_export_hwpx_creates_valid_file_using_vendored_runtime(tmp_path, monkeypatch):
    """vendored runtime만으로 유효한 HWPX를 생성해야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)
    with ZipFile(hwpx_path, "r") as archive:
        names = archive.namelist()
    assert hwpx_path.exists()
    assert "Contents/masterpage0.xml" in names
    assert "Contents/masterpage1.xml" in names
    assert any(name.startswith("BinData/image") and name != "BinData/image1.bmp" for name in names)


def test_export_hwpx_uses_reference_masterpages_and_page_layout(tmp_path, monkeypatch):
    """masterpage와 page layout은 result_answer 기준을 유지해야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)
    section_root = read_archive_xml(hwpx_path, "Contents/section0.xml")
    sec_pr = section_root.find(".//hp:secPr", NS)
    page_pr = sec_pr.find("hp:pagePr", NS)
    margin = page_pr.find("hp:margin", NS)
    refs = [node.get("idRef") for node in sec_pr.findall("hp:masterPage", NS)]
    col_pr = section_root.find(".//hp:colPr", NS)
    assert sec_pr.get("masterPageCnt") == "2"
    assert page_pr.get("width") == "77102"
    assert page_pr.get("height") == "111685"
    assert margin.get("header") == "6803"
    assert margin.get("footer") == "2551"
    assert refs == ["masterpage0", "masterpage1"]
    assert col_pr.get("sameGap") == "3316"


def test_export_hwpx_header_matches_result_answer_template_counts(tmp_path, monkeypatch):
    """header 정의 개수는 result_answer와 같아야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    generated_header = read_archive_xml(hwpx_path, "Contents/header.xml")
    reference_header = read_reference_xml("Contents/header.xml")
    assert count_header_defs(generated_header) == count_header_defs(reference_header)


def test_export_hwpx_first_block_preserves_reference_controls(tmp_path, monkeypatch):
    """첫 문단은 title table과 secPr scaffold를 그대로 가져야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    first_para = direct_paragraphs(read_archive_xml(hwpx_path, "Contents/section0.xml"))[0]
    runs = first_para.findall("hp:run", NS)
    assert first_para.get("paraPrIDRef") == "29"
    assert first_para.get("styleIDRef") == "1"
    assert first_para.find(".//hp:tbl", NS) is not None
    assert first_para.find(".//hp:line", NS) is not None
    assert first_para.find(".//hp:rect", NS) is not None
    assert len(runs) == 4
    assert "".join(runs[2].xpath(".//hp:t/text()", namespaces=NS)).strip() == "1."


def test_export_hwpx_uses_reference_picture_and_choice_paragraphs(tmp_path, monkeypatch):
    """그림과 보기는 direct paragraph 구조를 유지해야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    paragraphs = direct_paragraphs(read_archive_xml(hwpx_path, "Contents/section0.xml"))
    picture_para = paragraphs[2]
    choice_para = paragraphs[3]
    eq_scripts = choice_para.xpath(".//hp:equation/hp:script/text()", namespaces=NS)
    assert picture_para.get("paraPrIDRef") == "34"
    assert picture_para.get("styleIDRef") == "1"
    assert choice_para.get("paraPrIDRef") == "11"
    assert choice_para.get("styleIDRef") == "4"
    assert len(choice_para.findall("hp:run", NS)) == 1
    assert eq_scripts == ["1", "3/2", "9/4", "7/3", "5/2"]


def test_export_hwpx_choice_equations_keep_reference_inline_attrs(tmp_path, monkeypatch):
    """보기 수식은 reference inline 속성을 유지해야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    choice_para = direct_paragraphs(read_archive_xml(hwpx_path, "Contents/section0.xml"))[3]
    equations = choice_para.findall(".//hp:equation", NS)
    assert all(node.get("font") == "HYhwpEQ" for node in equations)
    assert all(node.find("hp:pos", NS).get("flowWithText") == "1" for node in equations)
    assert all(node.find("hp:sz", NS).get("width") != "0" for node in equations)
    assert all(node.find("hp:sz", NS).get("height") != "0" for node in equations)


def test_export_hwpx_explanation_mixed_line_keeps_single_run_structure(tmp_path, monkeypatch):
    """해설 mixed line은 run 1개 안에 text/equation child를 같이 가져야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    mixed_para = direct_paragraphs(read_archive_xml(hwpx_path, "Contents/section0.xml"))[8]
    runs = mixed_para.findall("hp:run", NS)
    equations = mixed_para.findall(".//hp:equation", NS)
    texts = mixed_para.xpath(".//hp:t/text()", namespaces=NS)
    assert mixed_para.get("paraPrIDRef") == "4"
    assert mixed_para.get("styleIDRef") == "0"
    assert len(runs) == 1
    assert len(equations) == 2
    assert any("이다. 또한" in text for text in texts)
    assert all(node.get("font") == "HYhwpEQ" for node in equations)


def test_export_hwpx_renders_current_year_and_current_page_only_footer(tmp_path, monkeypatch):
    """연도는 현재값으로 치환하고 footer는 현재 페이지만 남겨야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "_build_render_context", lambda: module.TemplateRenderContext(year="2031"))
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    section_root = read_archive_xml(hwpx_path, "Contents/section0.xml")
    with ZipFile(hwpx_path, "r") as archive:
        masterpage0_xml = archive.read("Contents/masterpage0.xml").decode("utf-8")
        masterpage1_xml = archive.read("Contents/masterpage1.xml").decode("utf-8")
    texts = " ".join(section_root.xpath(".//hp:t/text()", namespaces=NS))
    assert "2031학년도" in texts
    assert 'numType="PAGE"' in masterpage0_xml
    assert 'numType="PAGE"' in masterpage1_xml
    assert ">20<" not in masterpage0_xml
    assert ">20<" not in masterpage1_xml


def test_export_hwpx_section_uses_only_header_defined_style_refs(tmp_path, monkeypatch):
    """section/masterpage style ref는 header 정의 안에 있어야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    header_root = read_archive_xml(hwpx_path, "Contents/header.xml")
    section_root = read_archive_xml(hwpx_path, "Contents/section0.xml")
    valid_para_ids = {node.get("id") for node in header_root.findall(".//hh:paraPr", NS)}
    valid_char_ids = {node.get("id") for node in header_root.findall(".//hh:charPr", NS)}
    used_para_ids = {node.get("paraPrIDRef") for node in section_root.findall(".//hp:p", NS)}
    used_char_ids = {node.get("charPrIDRef") for node in section_root.findall(".//hp:run", NS)}
    assert used_para_ids <= valid_para_ids
    assert used_char_ids <= valid_char_ids


def test_export_hwpx_skips_empty_failed_regions_and_renumbers_items(tmp_path, monkeypatch):
    """빈 실패 영역은 건너뛰고 문제 번호를 다시 매겨야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_job = JobPipelineContext(
        job_id="job-export-2",
        file_name="uploaded_image.png",
        image_url="user-123/job-export-2/input/uploaded_image.png",
        image_width=32,
        image_height=24,
        status="failed",
        created_at="2026-03-18T00:00:00+00:00",
        updated_at="2026-03-18T00:00:00+00:00",
        regions=[
            RegionPipelineContext(
                context=RegionContext(id="q1", polygon=[[0, 0], [8, 0], [8, 8], [0, 8]], type="mixed", order=1),
                extractor=ExtractorContext(ocr_text="첫 번째 문제", explanation="첫 번째 해설"),
                figure=FigureContext(image_crop_url=image_relative_path.as_posix()),
                status="completed",
                success=True,
            ),
            RegionPipelineContext(
                context=RegionContext(id="q2", polygon=[[9, 0], [16, 0], [16, 8], [9, 8]], type="mixed", order=2),
                extractor=ExtractorContext(),
                figure=FigureContext(),
                status="failed",
                success=False,
                error_reason="ocr failed",
            ),
            RegionPipelineContext(
                context=RegionContext(id="q3", polygon=[[17, 0], [24, 0], [24, 8], [17, 8]], type="mixed", order=3),
                extractor=ExtractorContext(ocr_text="세 번째 문제"),
                figure=FigureContext(),
                status="failed",
                success=False,
                error_reason="image failed",
            ),
        ],
    )
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, export_job, export_dir)
    section_xml = ZipFile(hwpx_path, "r").read("Contents/section0.xml").decode("utf-8")
    assert "첫 번째 문제" in section_xml
    assert "세 번째 문제" in section_xml
    assert "2." in section_xml
    assert "3." not in section_xml
