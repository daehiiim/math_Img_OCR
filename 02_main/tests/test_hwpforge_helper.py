import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.pipeline.hwpforge_helper import (
    HWPFORGE_RUNTIME_UNAVAILABLE,
    HwpForgeDocumentRequest,
    HwpForgeHelperError,
    build_hwpforge_paragraph,
    equation_segment,
    generate_hwpx_with_hwpforge,
    text_segment,
)


class DummyCompletedProcess:
    """subprocess.run 대체용 완료 객체다."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def make_app_root(tmp_path: Path) -> Path:
    """helper 테스트용 최소 app 루트 구조를 만든다."""
    app_root = tmp_path / "02_main"
    helper_script = app_root / "scripts" / "hwpforge_doc_helper.js"
    sample_hwpx = tmp_path / "templates" / "generated-canonical-sample.hwpx"
    helper_script.parent.mkdir(parents=True, exist_ok=True)
    helper_script.write_text("// test helper\n", encoding="utf-8")
    sample_hwpx.parent.mkdir(parents=True, exist_ok=True)
    sample_hwpx.write_bytes(b"sample")
    return app_root


def make_request(output_path: Path) -> HwpForgeDocumentRequest:
    """검증용 helper 요청 객체를 만든다."""
    return HwpForgeDocumentRequest(
        output_hwpx_path=output_path,
        stem="테스트 문제 본문",
        choices=("1", "2", "3", "4", "5"),
        explanation_paragraphs=(
            build_hwpforge_paragraph(text_segment("첫째 줄")),
            build_hwpforge_paragraph(
                text_segment("삼각형"),
                equation_segment("ABC"),
                text_segment("는 닮음"),
            ),
        ),
        year="2030",
    )


def test_generate_hwpx_with_hwpforge_returns_structured_result(tmp_path, monkeypatch):
    """helper 응답이 성공이면 요약 dataclass를 반환해야 한다."""
    app_root = make_app_root(tmp_path)
    env_mcp_path = tmp_path / "runtime" / "hwpforge-mcp.js"
    env_mcp_path.parent.mkdir(parents=True, exist_ok=True)
    env_mcp_path.write_text("// mcp\n", encoding="utf-8")
    seen_payloads: list[dict[str, object]] = []

    def fake_run(args, cwd, capture_output, text, check, encoding):
        request_path = Path(args[3])
        response_path = Path(args[5])
        seen_payloads.append(__import__("json").loads(request_path.read_text(encoding="utf-8")))
        response_path.write_text(
            (
                '{\n'
                '  "success": true,\n'
                '  "data": {\n'
                f'    "output_hwpx_path": "{tmp_path.as_posix()}/exports/out.hwpx",\n'
                '    "paragraphs": 9,\n'
                '    "tables": 1,\n'
                '    "images": 0,\n'
                '    "summary": "1 sections, 9 paragraphs, 1 tables, 0 images, 0 charts"\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        return DummyCompletedProcess(returncode=0)

    monkeypatch.setenv("HWPFORGE_MCP_PATH", str(env_mcp_path))
    monkeypatch.setattr("app.pipeline.hwpforge_helper.shutil.which", lambda _: "C:/node.exe")
    monkeypatch.setattr("app.pipeline.hwpforge_helper.subprocess.run", fake_run)

    result = generate_hwpx_with_hwpforge(
        make_request(tmp_path / "exports" / "out.hwpx"),
        app_root=app_root,
    )

    assert result.output_hwpx_path == tmp_path / "exports" / "out.hwpx"
    assert result.paragraphs == 9
    assert result.tables == 1
    assert result.images == 0
    assert seen_payloads[0]["stem"] == "테스트 문제 본문"
    assert seen_payloads[0]["choices"] == ["1", "2", "3", "4", "5"]
    assert seen_payloads[0]["year"] == "2030"


def test_generate_hwpx_with_hwpforge_raises_structured_error_on_failure(tmp_path, monkeypatch):
    """helper가 실패 응답을 쓰면 구조화 예외를 던져야 한다."""
    app_root = make_app_root(tmp_path)
    env_mcp_path = tmp_path / "runtime" / "hwpforge-mcp.js"
    env_mcp_path.parent.mkdir(parents=True, exist_ok=True)
    env_mcp_path.write_text("// mcp\n", encoding="utf-8")

    def fake_run(args, cwd, capture_output, text, check, encoding):
        response_path = Path(args[5])
        response_path.write_text(
            (
                '{\n'
                '  "success": false,\n'
                '  "error": {\n'
                '    "code": "HWPX_VALIDATE_FAILED",\n'
                '    "message": "generated hwpx is invalid"\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        return DummyCompletedProcess(returncode=1, stderr="helper failed")

    monkeypatch.setenv("HWPFORGE_MCP_PATH", str(env_mcp_path))
    monkeypatch.setattr("app.pipeline.hwpforge_helper.shutil.which", lambda _: "C:/node.exe")
    monkeypatch.setattr("app.pipeline.hwpforge_helper.subprocess.run", fake_run)

    with pytest.raises(HwpForgeHelperError) as exc_info:
        generate_hwpx_with_hwpforge(make_request(tmp_path / "exports" / "out.hwpx"), app_root=app_root)

    assert exc_info.value.code == "HWPX_VALIDATE_FAILED"
    assert "generated hwpx is invalid" in str(exc_info.value)


def test_generate_hwpx_with_hwpforge_reports_missing_runtime(tmp_path, monkeypatch):
    """MCP 경로를 찾지 못하면 준비 실패 오류를 돌려야 한다."""
    app_root = make_app_root(tmp_path)
    monkeypatch.delenv("HWPFORGE_MCP_PATH", raising=False)
    monkeypatch.setattr("app.pipeline.hwpforge_helper.shutil.which", lambda _: "C:/node.exe")

    with pytest.raises(HwpForgeHelperError) as exc_info:
        generate_hwpx_with_hwpforge(make_request(tmp_path / "exports" / "out.hwpx"), app_root=app_root)

    assert exc_info.value.code == HWPFORGE_RUNTIME_UNAVAILABLE
    assert "hwpforge mcp runtime not found" in str(exc_info.value)
