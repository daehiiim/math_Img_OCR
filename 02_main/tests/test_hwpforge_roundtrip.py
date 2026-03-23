import importlib
import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.append(str(Path(__file__).resolve().parents[1]))


def load_roundtrip_module():
    """roundtrip 모듈을 매 테스트마다 새로 import한다."""
    sys.modules.pop("app.pipeline.hwpforge_roundtrip", None)
    return importlib.import_module("app.pipeline.hwpforge_roundtrip")


def test_resolve_hwpforge_runtime_prefers_vendored_linux_binary(tmp_path):
    """배포용 vendored binary가 있으면 .tmp PoC보다 먼저 선택해야 한다."""
    module = load_roundtrip_module()
    app_root = tmp_path / "02_main"
    vendored_binary = (
        app_root
        / "vendor"
        / "hwpforge-mcp"
        / "node_modules"
        / "@hwpforge"
        / "mcp-linux-x64"
        / "bin"
        / "hwpforge-mcp"
    )
    vendored_binary.parent.mkdir(parents=True, exist_ok=True)
    vendored_binary.write_text("stub", encoding="utf-8")

    resolved = module.resolve_hwpforge_runtime(app_root=app_root)

    assert resolved.executable_path == vendored_binary
    assert resolved.command == (str(vendored_binary),)


def test_resolve_hwpforge_template_json_path_prefers_app_template_asset(tmp_path):
    """direct writer template JSON은 app 템플릿 자산을 우선 사용해야 한다."""
    module = load_roundtrip_module()
    app_root = tmp_path / "02_main"
    template_json_path = app_root / "templates" / "hwpx" / module.DIRECT_TEMPLATE_JSON_NAME
    template_json_path.parent.mkdir(parents=True, exist_ok=True)
    template_json_path.write_text('{"document":{"sections":[{"paragraphs":[]}]},"styles":{}}', encoding="utf-8")

    resolved = module.resolve_hwpforge_template_json_path(app_root=app_root)

    assert resolved == template_json_path


def test_build_section_via_hwpforge_writes_generated_section(tmp_path, monkeypatch):
    """direct writer는 template JSON과 generated hwpx에서 section0.xml을 반환해야 한다."""
    module = load_roundtrip_module()
    app_root = tmp_path / "02_main"
    template_json_path = app_root / "templates" / "hwpx" / module.DIRECT_TEMPLATE_JSON_NAME
    template_json_path.parent.mkdir(parents=True, exist_ok=True)
    template_json_path.write_text('{"document":{"sections":[{"paragraphs":[]}]},"styles":{}}', encoding="utf-8")
    output_dir = tmp_path / "work"
    bindata_dir = output_dir / "BinData"
    warnings = type("DummyWarnings", (), {"add": lambda self, code, detail: None})()

    monkeypatch.setattr(
        module,
        "resolve_hwpforge_runtime",
        lambda app_root, runtime_path: module.HwpForgeRuntime(Path("/fake/hwpforge"), ("/fake/hwpforge",)),
    )
    monkeypatch.setattr(
        module,
        "build_hwpforge_export_ir",
        lambda root_path, job, bindata_dir, year, warnings: (
            {"year": year, "regions": []},
            [{"id": "image2", "filename": "image2.png", "ext": "png"}],
        ),
    )
    monkeypatch.setattr(
        module,
        "build_exported_document_from_template",
        lambda template_document, export_ir: {"document": {"sections": [{"paragraphs": [{"runs": []}]}]}},
    )

    class FakeSession:
        """MCP 세션 대신 generated hwpx zip만 남기는 테스트 대역이다."""

        def __init__(self, runtime, work_dir, stderr_path):
            self.work_dir = work_dir

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def call_tool(self, tool_name, arguments, error_code):
            if tool_name == "hwpforge_from_json":
                generated_hwpx_path = Path(arguments["output_path"])
                generated_hwpx_path.parent.mkdir(parents=True, exist_ok=True)
                with ZipFile(generated_hwpx_path, "w") as archive:
                    archive.writestr(
                        "Contents/section0.xml",
                        '<hp:section xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"/>',
                    )
            return {"data": {"valid": True}}

    monkeypatch.setattr(module, "_McpSession", FakeSession)

    section_path, images_info = module.build_section_via_hwpforge(
        root_path=tmp_path / "runtime",
        job=object(),
        bindata_dir=bindata_dir,
        output_dir=output_dir,
        year="2031",
        warnings=warnings,
        runtime_path="dummy",
        app_root=app_root,
    )

    assert section_path.exists()
    assert "section" in section_path.read_text(encoding="utf-8")
    assert images_info == [{"id": "image2", "filename": "image2.png", "ext": "png"}]
