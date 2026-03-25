import importlib
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
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
    "opf": "http://www.idpf.org/2007/opf/",
}
STYLE_GUIDE_HWPX_PATH = Path(__file__).resolve().parents[2] / "templates" / "style_guide.hwpx"
HWPFORGE_TEMPLATE_JSON_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "hwpforge_generated_canonical_sample.json"
)


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


def copy_style_guide_bundle(target_path: Path) -> Path:
    """canonical style guide HWPX를 임시 경로로 복사한다."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(STYLE_GUIDE_HWPX_PATH.read_bytes())
    return target_path


def copy_hwpforge_template_json(target_path: Path) -> Path:
    """direct HwpForge writer용 템플릿 JSON을 임시 경로로 복사한다."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(HWPFORGE_TEMPLATE_JSON_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return target_path


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


def read_style_guide_xml(inner_path: str):
    """style guide HWPX 안 XML을 파싱해 반환한다."""
    with ZipFile(STYLE_GUIDE_HWPX_PATH, "r") as archive:
        return etree.fromstring(archive.read(inner_path))


def direct_paragraphs(root) -> list:
    """section root 직계 문단만 반환한다."""
    return root.findall("hp:p", NS)


def list_archive_names(hwpx_path: Path) -> list[str]:
    """HWPX zip 안의 엔트리 목록을 정렬해 반환한다."""
    with ZipFile(hwpx_path, "r") as archive:
        return sorted(archive.namelist())


def collect_header_id_sets(header_root) -> tuple[set[str], set[str], set[str]]:
    """header 정의의 charPr/paraPr/style ID 집합을 반환한다."""
    return (
        {node.get("id") for node in header_root.findall(".//hh:charPr", NS)},
        {node.get("id") for node in header_root.findall(".//hh:paraPr", NS)},
        {node.get("id") for node in header_root.findall(".//hh:style", NS)},
    )


def collect_manifest_items(content_root) -> list[tuple[str, str, str | None]]:
    """content.hpf manifest item의 핵심 속성을 정렬해 반환한다."""
    items: list[tuple[str, str, str | None]] = []
    for node in content_root.findall(".//opf:item", NS):
        items.append((node.get("id", ""), node.get("href", ""), node.get("media-type")))
    return sorted(items)


def serialize_xml_for_compare(element) -> bytes:
    """공백 차이를 제거한 canonical XML 바이트를 반환한다."""
    return etree.tostring(element, method="c14n")


def make_runtime_paths(module, tmp_path, monkeypatch):
    """exporter 테스트용 runtime 환경을 만든다."""
    app_root = tmp_path / "02_main"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    copy_hwpforge_template_json(app_root / "templates" / "hwpx" / HWPFORGE_TEMPLATE_JSON_PATH.name)
    copy_style_guide_bundle(tmp_path / "templates" / "style_guide.hwpx")
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
    with pytest.raises(module.HwpxTemplateError) as exc_info:
        module._resolve_hwpx_runtime(
            app_root=app_root,
            configured_skill_dir=str(configured_dir),
            codex_home=tmp_path / "missing-codex-home",
            home_dir=tmp_path / "missing-home",
        )
    assert exc_info.value.code == module.TEMPLATE_RUNTIME_MISSING_CODE
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


def test_export_hwpx_auto_engine_uses_hwpforge_section_when_helper_succeeds(tmp_path, monkeypatch):
    """auto 모드에서 helper가 성공하면 HwpForge section 교체 경로를 타야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    direct_calls: list[Path] = []
    roundtrip_calls: list[Path] = []

    def fake_settings(_root):
        """테스트용 export engine 설정을 반환한다."""
        return SimpleNamespace(hwpx_skill_dir=None, hwpx_export_engine="auto", hwpforge_mcp_path="dummy")

    def fake_direct_writer(
        root_path: Path,
        job,
        bindata_dir: Path,
        output_dir: Path,
        year: str,
        warnings,
        runtime_path: str | None,
        app_root: Path,
    ):
        """직접 writer 성공만 시뮬레이션한다."""
        direct_calls.append(output_dir)
        bindata_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / "section0.direct.xml"
        output_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(STYLE_GUIDE_HWPX_PATH, "r") as archive:
            target_path.write_bytes(archive.read("Contents/section0.xml"))
        return target_path, []

    monkeypatch.setattr(module, "get_settings", fake_settings)
    monkeypatch.setattr(module, "build_section_via_hwpforge", fake_direct_writer)
    monkeypatch.setattr(module, "inspect_and_validate_hwpx_via_hwpforge", lambda *_args: None)

    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)

    assert hwpx_path.exists()
    assert len(direct_calls) == 1
    assert roundtrip_calls == []


def test_export_hwpx_auto_engine_falls_back_to_legacy_when_helper_fails(tmp_path, monkeypatch):
    """auto 모드에서 direct writer 실패는 즉시 legacy fallback으로 흡수해야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"

    def fake_settings(_root):
        """테스트용 export engine 설정을 반환한다."""
        return SimpleNamespace(hwpx_skill_dir=None, hwpx_export_engine="auto", hwpforge_mcp_path="dummy")

    monkeypatch.setattr(module, "get_settings", fake_settings)
    monkeypatch.setattr(
        module,
        "build_section_via_hwpforge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("direct failed")),
    )

    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)

    assert hwpx_path.exists()
    section_xml = ZipFile(hwpx_path, "r").read("Contents/section0.xml").decode("utf-8")
    assert "문제 본문" in section_xml


def test_export_hwpx_hwpforge_mode_raises_when_helper_fails(tmp_path, monkeypatch):
    """hwpforge 강제 모드에서는 helper 실패를 그대로 실패로 올려야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"

    def fake_settings(_root):
        """테스트용 export engine 설정을 반환한다."""
        return SimpleNamespace(hwpx_skill_dir=None, hwpx_export_engine="hwpforge", hwpforge_mcp_path="dummy")

    monkeypatch.setattr(module, "get_settings", fake_settings)
    monkeypatch.setattr(
        module,
        "build_section_via_hwpforge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(module.HwpxTemplateError("HWPFORGE_SECTION_BUILD_FAILED", "forced hwpforge failure")),
    )

    with pytest.raises(ValueError, match="문서 템플릿을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."):
        module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)


def test_export_hwpx_uses_style_guide_secpr_exactly(tmp_path, monkeypatch):
    """section secPr/pagePr/masterPage는 style guide와 완전히 같아야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)
    section_root = read_archive_xml(hwpx_path, "Contents/section0.xml")
    style_section_root = read_style_guide_xml("Contents/section0.xml")
    generated_sec_pr = section_root.find(".//hp:secPr", NS)
    style_sec_pr = style_section_root.find(".//hp:secPr", NS)
    assert serialize_xml_for_compare(generated_sec_pr) == serialize_xml_for_compare(style_sec_pr)


def test_export_hwpx_header_matches_style_guide_id_sets_exactly(tmp_path, monkeypatch):
    """header의 charPr/paraPr/style ID 집합은 style guide와 완전히 같아야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    generated_header = read_archive_xml(hwpx_path, "Contents/header.xml")
    style_header = read_style_guide_xml("Contents/header.xml")
    assert collect_header_id_sets(generated_header) == collect_header_id_sets(style_header)


def test_export_hwpx_contains_style_guide_masterpages_exactly(tmp_path, monkeypatch):
    """생성 산출물의 masterpage는 style guide canonical과 완전히 같아야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)
    style_guide_names = list_archive_names(STYLE_GUIDE_HWPX_PATH)
    assert "Contents/masterpage0.xml" in style_guide_names
    assert "Contents/masterpage1.xml" in style_guide_names
    generated_masterpage0 = read_archive_xml(hwpx_path, "Contents/masterpage0.xml")
    generated_masterpage1 = read_archive_xml(hwpx_path, "Contents/masterpage1.xml")
    style_masterpage0 = read_style_guide_xml("Contents/masterpage0.xml")
    style_masterpage1 = read_style_guide_xml("Contents/masterpage1.xml")
    assert serialize_xml_for_compare(generated_masterpage0) == serialize_xml_for_compare(style_masterpage0)
    assert serialize_xml_for_compare(generated_masterpage1) == serialize_xml_for_compare(style_masterpage1)


def test_export_hwpx_uses_style_guide_even_when_vendored_base_changes(tmp_path, monkeypatch):
    """vendor base가 변해도 canonical source는 style guide여야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    vendored_section = (
        tmp_path / "02_main" / "vendor" / "hwpxskill-math" / "templates" / "base" / "Contents" / "section0.xml"
    )
    vendored_masterpage = (
        tmp_path / "02_main" / "vendor" / "hwpxskill-math" / "templates" / "base" / "Contents" / "masterpage0.xml"
    )
    vendored_section.write_text("<broken-section/>", encoding="utf-8")
    vendored_masterpage.write_text("<broken-masterpage/>", encoding="utf-8")
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)
    generated_section = read_archive_xml(hwpx_path, "Contents/section0.xml")
    generated_masterpage = read_archive_xml(hwpx_path, "Contents/masterpage0.xml")
    style_section = read_style_guide_xml("Contents/section0.xml")
    style_masterpage = read_style_guide_xml("Contents/masterpage0.xml")
    assert serialize_xml_for_compare(generated_section.find(".//hp:secPr", NS)) == serialize_xml_for_compare(
        style_section.find(".//hp:secPr", NS)
    )
    assert serialize_xml_for_compare(generated_masterpage) == serialize_xml_for_compare(style_masterpage)


def test_export_hwpx_uses_app_local_canonical_template_in_flat_runtime(tmp_path, monkeypatch):
    """컨테이너처럼 app 루트에만 canonical template가 있어도 export가 되어야 한다."""
    module = load_exporter_module()
    app_root = tmp_path / "app"
    copy_runtime_bundle(app_root / "vendor" / "hwpxskill-math")
    copy_style_guide_bundle(app_root / "templates" / "style_guide.hwpx")
    monkeypatch.setattr(module, "ROOT", app_root)
    monkeypatch.setattr(module, "_get_codex_home", lambda: tmp_path / "missing-codex-home")
    monkeypatch.setattr(module, "_get_home_dir", lambda: tmp_path / "missing-home")
    root_path = tmp_path / "runtime"
    image_relative_path = Path("assets/q1.png")
    image_path = root_path / image_relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(make_png_bytes(width=459, height=213))

    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), tmp_path / "exports")

    assert hwpx_path.exists()
    assert "Contents/masterpage0.xml" in list_archive_names(hwpx_path)


def test_export_hwpx_uses_fixed_title(tmp_path, monkeypatch):
    """export된 HWPX의 제목은 생성결과로 고정되어야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    content_root = read_archive_xml(hwpx_path, "Contents/content.hpf")
    title = content_root.find(".//opf:title", {"opf": "http://www.idpf.org/2007/opf/"})

    assert title is not None
    assert title.text == "생성결과"


def test_export_hwpx_content_manifest_matches_style_guide_except_title_and_images(tmp_path, monkeypatch):
    """content.hpf는 title과 추가 이미지 manifest만 제외하고 style guide와 같아야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    generated_content = read_archive_xml(hwpx_path, "Contents/content.hpf")
    style_content = read_style_guide_xml("Contents/content.hpf")
    generated_title = generated_content.find(".//opf:title", NS)
    style_title = style_content.find(".//opf:title", NS)
    generated_title.text = style_title.text
    generated_items = collect_manifest_items(generated_content)
    style_items = collect_manifest_items(style_content)
    dynamic_items = [
        item
        for item in generated_items
        if item[1].startswith("BinData/image") and item[1] != "BinData/image1.BMP" and item[1] != "BinData/image1.bmp"
    ]
    assert all(item[1].startswith("BinData/image") for item in dynamic_items)
    assert [item for item in generated_items if item not in dynamic_items] == style_items


def test_export_hwpx_first_block_preserves_reference_controls(tmp_path, monkeypatch):
    """첫 문단은 title table과 secPr scaffold를 그대로 가져야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    first_para = direct_paragraphs(read_archive_xml(hwpx_path, "Contents/section0.xml"))[0]
    style_first_para = direct_paragraphs(read_style_guide_xml("Contents/section0.xml"))[0]
    runs = first_para.findall("hp:run", NS)
    assert first_para.get("paraPrIDRef") == style_first_para.get("paraPrIDRef")
    assert first_para.get("styleIDRef") == style_first_para.get("styleIDRef")
    assert first_para.find(".//hp:tbl", NS) is not None
    assert first_para.find(".//hp:line", NS) is not None
    assert first_para.find(".//hp:rect", NS) is not None
    assert len(runs) == 4
    assert "".join(runs[2].xpath(".//hp:t/text()", namespaces=NS)).strip() == "1."


def test_export_hwpx_uses_style_guide_picture_and_choice_paragraphs(tmp_path, monkeypatch):
    """그림과 보기는 style guide direct paragraph style을 그대로 써야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    paragraphs = direct_paragraphs(read_archive_xml(hwpx_path, "Contents/section0.xml"))
    style_paragraphs = direct_paragraphs(read_style_guide_xml("Contents/section0.xml"))
    picture_para = paragraphs[2]
    choice_para = paragraphs[3]
    eq_scripts = choice_para.xpath(".//hp:equation/hp:script/text()", namespaces=NS)
    assert picture_para.get("paraPrIDRef") == style_paragraphs[2].get("paraPrIDRef")
    assert picture_para.get("styleIDRef") == style_paragraphs[2].get("styleIDRef")
    assert choice_para.get("paraPrIDRef") == style_paragraphs[3].get("paraPrIDRef")
    assert choice_para.get("styleIDRef") == style_paragraphs[3].get("styleIDRef")
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
    style_mixed_para = direct_paragraphs(read_style_guide_xml("Contents/section0.xml"))[8]
    runs = mixed_para.findall("hp:run", NS)
    equations = mixed_para.findall(".//hp:equation", NS)
    texts = mixed_para.xpath(".//hp:t/text()", namespaces=NS)
    assert mixed_para.get("paraPrIDRef") == style_mixed_para.get("paraPrIDRef")
    assert mixed_para.get("styleIDRef") == style_mixed_para.get("styleIDRef")
    assert len(runs) == 1
    assert len(equations) == 2
    assert any("이다. 또한" in text for text in texts)
    assert all(node.get("font") == "HYhwpEQ" for node in equations)


def test_export_hwpx_explanation_inline_equations_use_compact_width_for_short_scripts(tmp_path, monkeypatch):
    """짧은 inline 수식은 긴 각도식 width를 그대로 재사용하면 안 된다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    section_root = read_archive_xml(hwpx_path, "Contents/section0.xml")

    widths_by_script = {
        node.findtext("hp:script", default="", namespaces=NS): int(node.find("hp:sz", NS).get("width"))
        for node in section_root.findall(".//hp:equation", NS)
    }

    assert widths_by_script["ABC"] < widths_by_script["ANGLE BAC= ANGLE DAE"]
    assert widths_by_script["ADE"] < widths_by_script["ANGLE ABC= ANGLE ADE"]


def test_export_hwpx_explanation_inline_equations_use_compact_box_metrics(tmp_path, monkeypatch):
    """해설 mixed 수식은 한글이 재계산한 compact 박스 크기로 저장돼야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    paragraphs = direct_paragraphs(read_archive_xml(hwpx_path, "Contents/section0.xml"))

    explanation_equations = []
    for paragraph in paragraphs:
        if paragraph.get("paraPrIDRef") == "0" and paragraph.get("styleIDRef") == "0":
            explanation_equations.extend(paragraph.findall(".//hp:equation", NS))

    assert explanation_equations
    assert all(node.find("hp:sz", NS).get("height") == "975" for node in explanation_equations)
    assert all(node.get("baseLine") == "86" for node in explanation_equations)


def test_export_hwpx_repairs_direct_hwpforge_widths_using_canonical_samples(tmp_path, monkeypatch):
    """direct HwpForge 결과가 장문 폭으로 풀리면 canonical 샘플 기준으로 다시 보정해야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"

    class FakeSettings:
        """직접 writer 강제 실행용 테스트 설정을 제공한다."""

        hwpx_skill_dir = None
        hwpx_export_engine = "hwpforge"
        hwpforge_mcp_path = "C:/tooling/hwpforge-mcp.exe"

    def fake_direct_writer(
        root_path: Path,
        job,
        bindata_dir: Path,
        output_dir: Path,
        year: str,
        warnings,
        runtime_path: str | None,
        app_root: Path,
    ):
        """width가 과도하게 큰 section0.xml을 의도적으로 만든다."""
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / "section0.direct.xml"
        with ZipFile(STYLE_GUIDE_HWPX_PATH, "r") as archive:
            section_root = etree.fromstring(archive.read("Contents/section0.xml"))
        for equation in section_root.findall(".//hp:equation", NS):
            size = equation.find("hp:sz", NS)
            if size is not None:
                size.set("width", "8386")
        target_path.write_bytes(etree.tostring(section_root, encoding="UTF-8", xml_declaration=True))
        return target_path, []

    monkeypatch.setattr(module, "get_settings", lambda _root: FakeSettings())
    monkeypatch.setattr(module, "build_section_via_hwpforge", fake_direct_writer)
    monkeypatch.setattr(module, "inspect_and_validate_hwpx_via_hwpforge", lambda *_args: None)

    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    generated_section = read_archive_xml(hwpx_path, "Contents/section0.xml")
    style_section = read_style_guide_xml("Contents/section0.xml")
    generated_widths = {
        node.findtext("hp:script", default="", namespaces=NS): int(node.find("hp:sz", NS).get("width"))
        for node in generated_section.findall(".//hp:equation", NS)
    }
    style_widths = {
        node.findtext("hp:script", default="", namespaces=NS): int(node.find("hp:sz", NS).get("width"))
        for node in style_section.findall(".//hp:equation", NS)
    }

    assert generated_widths["ABC"] == style_widths["ABC"]
    assert generated_widths["ADE"] == style_widths["ADE"]
    assert generated_widths["ABC"] < generated_widths["ANGLE  BAC`=` ANGLE DAE"]
    assert generated_widths["ADE"] < generated_widths["ANGLE  ABC`=` ANGLE  ADE"]


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
    """section/masterpage의 paraPr/charPr/style ref는 header 정의 안에 있어야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    header_root = read_archive_xml(hwpx_path, "Contents/header.xml")
    section_root = read_archive_xml(hwpx_path, "Contents/section0.xml")
    masterpage0_root = read_archive_xml(hwpx_path, "Contents/masterpage0.xml")
    masterpage1_root = read_archive_xml(hwpx_path, "Contents/masterpage1.xml")
    valid_para_ids = {node.get("id") for node in header_root.findall(".//hh:paraPr", NS)}
    valid_char_ids = {node.get("id") for node in header_root.findall(".//hh:charPr", NS)}
    valid_style_ids = {node.get("id") for node in header_root.findall(".//hh:style", NS)}
    roots = [section_root, masterpage0_root, masterpage1_root]
    used_para_ids = {node.get("paraPrIDRef") for root in roots for node in root.findall(".//hp:p", NS)}
    used_char_ids = {node.get("charPrIDRef") for root in roots for node in root.findall(".//hp:run", NS)}
    used_style_ids = {node.get("styleIDRef") for root in roots for node in root.findall(".//hp:p", NS)}
    assert used_para_ids <= valid_para_ids
    assert used_char_ids <= valid_char_ids
    assert used_style_ids <= valid_style_ids


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


def test_export_hwpx_normalizes_problem_numbers_and_latex_scripts(tmp_path, monkeypatch):
    """OCR 원문 번호와 LaTeX 잔재가 최종 HWPX에 남지 않아야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)
    export_job = JobPipelineContext(
        job_id="job-export-3",
        file_name="uploaded_image.png",
        image_url="user-123/job-export-3/input/uploaded_image.png",
        image_width=32,
        image_height=24,
        status="failed",
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
                            "3. △ABC에서 AB 위의 점 E와 AC 위의 점 D에 대하여",
                            "2) 보조 조건을 확인하시오.",
                        ]
                    ),
                    explanation="\n".join(
                        [
                            "주어진 조건에서 <math>\\triangle ABC</math> 와 <math>\\angle DAE</math> 를 확인한다.",
                            "<math>\\frac{1}{2}</math> 와 <math>degree</math> 표기도 정규화한다.",
                        ]
                    ),
                ),
                figure=FigureContext(image_crop_url=image_relative_path.as_posix()),
                status="completed",
                success=True,
            )
        ],
    )
    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, export_job, export_dir)
    section_root = read_archive_xml(hwpx_path, "Contents/section0.xml")
    scripts = section_root.xpath(".//hp:script/text()", namespaces=NS)
    section_xml = ZipFile(hwpx_path, "r").read("Contents/section0.xml").decode("utf-8")

    assert "3." not in section_xml
    assert "1." in section_xml
    assert "2) 보조 조건을 확인하시오." in section_xml
    assert any("△" in script and "ABC" in script for script in scripts)
    assert any("∠" in script and "DAE" in script for script in scripts)
    assert all("\\triangle" not in script for script in scripts)
    assert all("\\angle" not in script for script in scripts)
    assert all("\\frac" not in script for script in scripts)
    assert any("°" in script for script in scripts)
    assert all("degree" not in script for script in scripts)


def test_resolve_hwpforge_cli_path_prefers_configured_binary(tmp_path):
    """설정 경로의 hwpforge 실행 파일이 있으면 그 경로를 그대로 써야 한다."""
    sys.modules.pop("app.pipeline.hwpforge_roundtrip", None)
    helper_module = importlib.import_module("app.pipeline.hwpforge_roundtrip")
    configured_cli = tmp_path / "bin" / "hwpforge.exe"
    configured_cli.parent.mkdir(parents=True, exist_ok=True)
    configured_cli.write_text("stub", encoding="utf-8")

    resolved = helper_module.resolve_hwpforge_runtime(
        app_root=tmp_path / "02_main",
        configured_runtime_path=str(configured_cli),
    )

    assert resolved.executable_path == configured_cli


def test_export_hwpx_falls_back_when_hwpforge_bundle_build_fails(tmp_path, monkeypatch):
    """helper bundle 준비가 실패해도 reference renderer fallback으로 export가 완료되어야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)

    class FakeSettings:
        hwpx_skill_dir = None
        hwpx_export_engine = "auto"
        hwpforge_mcp_path = "C:/tooling/hwpforge-mcp.exe"

    monkeypatch.setattr(module, "get_settings", lambda _root: FakeSettings())
    monkeypatch.setattr(
        module,
        "roundtrip_section_via_hwpforge",
        lambda *_args: (_ for _ in ()).throw(module.HwpForgeRoundtripError("HWPFORGE_SECTION_BUILD_FAILED", "boom")),
    )

    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_export_job(image_relative_path.as_posix()), export_dir)
    section_xml = ZipFile(hwpx_path, "r").read("Contents/section0.xml").decode("utf-8")

    assert hwpx_path.exists()
    assert "문제 본문" in section_xml


def test_export_hwpx_prefers_hwpforge_bundle_when_available(tmp_path, monkeypatch):
    """direct writer helper가 성공하면 그 section 결과를 최종 산출물에 써야 한다."""
    module = load_exporter_module()
    root_path, image_relative_path = make_runtime_paths(module, tmp_path, monkeypatch)

    class FakeSettings:
        hwpx_skill_dir = None
        hwpx_export_engine = "auto"
        hwpforge_mcp_path = "C:/tooling/hwpforge-mcp.exe"

    helper_calls: list[Path] = []

    def fake_direct_writer(
        root_path: Path,
        job,
        bindata_dir: Path,
        output_dir: Path,
        year: str,
        warnings,
        runtime_path: str | None,
        app_root: Path,
    ):
        """helper section 경로만 고정 marker와 함께 시뮬레이션한다."""
        helper_calls.append(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / "section0.direct.xml"
        with ZipFile(STYLE_GUIDE_HWPX_PATH, "r") as archive:
            section_xml = archive.read("Contents/section0.xml").decode("utf-8")
        target_path.write_text(section_xml.replace("</hs:sec>", "<!--direct-writer-marker--></hs:sec>"), encoding="utf-8")
        return target_path, []

    monkeypatch.setattr(module, "get_settings", lambda _root: FakeSettings())
    monkeypatch.setattr(module, "build_section_via_hwpforge", fake_direct_writer)
    monkeypatch.setattr(module, "inspect_and_validate_hwpx_via_hwpforge", lambda *_args: None)

    export_dir = tmp_path / "exports"
    hwpx_path = module.export_hwpx(root_path, make_reference_like_job(image_relative_path.as_posix()), export_dir)
    section_xml = ZipFile(hwpx_path, "r").read("Contents/section0.xml").decode("utf-8")

    assert len(helper_calls) == 1
    assert "direct-writer-marker" in section_xml
