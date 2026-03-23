from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from app.pipeline.hwpforge_json_builder import (
    build_exported_document_from_template,
    build_hwpforge_export_ir,
)

APP_ROOT = Path(__file__).resolve().parents[2]
MCP_PROTOCOL_VERSION = "2025-03-26"
HWPFORGE_RUNTIME_UNAVAILABLE_CODE = "HWPFORGE_RUNTIME_UNAVAILABLE"
HWPFORGE_SECTION_BUILD_FAILED_CODE = "HWPFORGE_SECTION_BUILD_FAILED"
HWPX_VALIDATE_FAILED_CODE = "HWPX_VALIDATE_FAILED"
DIRECT_TEMPLATE_JSON_NAME = "hwpforge_generated_canonical_sample.json"
VENDORED_RUNTIME_CANDIDATES = (
    Path("vendor/hwpforge-mcp/node_modules/@hwpforge/mcp-linux-x64/bin/hwpforge-mcp"),
    Path("vendor/hwpforge-mcp/node_modules/@hwpforge/mcp-linux-arm64/bin/hwpforge-mcp"),
    Path("vendor/hwpforge-mcp/node_modules/@hwpforge/mcp-win32-x64/bin/hwpforge-mcp.exe"),
    Path("vendor/hwpforge-mcp/node_modules/@hwpforge/mcp/bin/hwpforge-mcp.js"),
)
MCP_EXE_PATTERN = ".tmp/hwpforge-poc/*/node_modules/@hwpforge/mcp-win32-x64/bin/hwpforge-mcp.exe"
MCP_JS_PATTERN = ".tmp/hwpforge-poc/*/node_modules/@hwpforge/mcp/bin/hwpforge-mcp.js"
DIRECT_TEMPLATE_JSON_CANDIDATES = (
    Path("templates/hwpx") / DIRECT_TEMPLATE_JSON_NAME,
    Path("tests/fixtures") / DIRECT_TEMPLATE_JSON_NAME,
)


@dataclass(frozen=True)
class HwpForgeRuntime:
    """HwpForge MCP 실행 정보를 보관한다."""

    executable_path: Path
    command: tuple[str, ...]


class HwpForgeRoundtripError(Exception):
    """HwpForge roundtrip 실패 코드와 세부 정보를 보관한다."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _normalize_runtime_path(app_root: Path, raw_path: str | None) -> Path | None:
    """설정 경로를 app root 기준 절대 경로로 정규화한다."""
    if raw_path is None or not raw_path.strip():
        return None
    candidate = Path(raw_path).expanduser()
    return candidate if candidate.is_absolute() else app_root / candidate


def _iter_runtime_candidates(app_root: Path, configured_runtime_path: str | None) -> list[Path]:
    """설정값과 로컬 PoC 경로를 합친 MCP 후보 목록을 반환한다."""
    candidates: list[Path] = []
    configured_path = _normalize_runtime_path(app_root, configured_runtime_path)
    if configured_path is not None:
        candidates.append(configured_path)
    for relative_path in VENDORED_RUNTIME_CANDIDATES:
        candidates.append(app_root / relative_path)
    candidates.extend(sorted(app_root.parent.glob(MCP_EXE_PATTERN)))
    candidates.extend(sorted(app_root.parent.glob(MCP_JS_PATTERN)))
    return list(dict.fromkeys(candidates))


def _build_runtime_command(executable_path: Path) -> tuple[str, ...]:
    """실행 파일 확장자에 맞는 subprocess 인자 목록을 만든다."""
    if executable_path.suffix.lower() == ".js":
        return ("node", str(executable_path))
    return (str(executable_path),)


def _iter_template_json_candidates(app_root: Path) -> list[Path]:
    """직접 writer가 사용할 template JSON 후보 경로를 반환한다."""
    return [app_root / relative_path for relative_path in DIRECT_TEMPLATE_JSON_CANDIDATES]


def resolve_hwpforge_template_json_path(app_root: Path = APP_ROOT) -> Path:
    """direct HwpForge writer용 template JSON 경로를 찾는다."""
    candidates = _iter_template_json_candidates(app_root)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    checked = "; ".join(str(path) for path in candidates) or "<none>"
    raise HwpForgeRoundtripError(
        HWPFORGE_SECTION_BUILD_FAILED_CODE,
        f"HwpForge template json not found. checked: {checked}",
    )


def resolve_hwpforge_runtime(
    app_root: Path = APP_ROOT,
    configured_runtime_path: str | None = None,
) -> HwpForgeRuntime:
    """사용 가능한 HwpForge MCP 실행 경로를 찾는다."""
    candidates = _iter_runtime_candidates(app_root, configured_runtime_path)
    for candidate in candidates:
        if candidate.exists():
            return HwpForgeRuntime(candidate, _build_runtime_command(candidate))
    checked = "; ".join(str(path) for path in candidates) or "<none>"
    raise HwpForgeRoundtripError(
        HWPFORGE_RUNTIME_UNAVAILABLE_CODE,
        f"HwpForge MCP runtime not found. checked: {checked}",
    )


def _extract_tool_payload(result: dict[str, Any], tool_name: str, error_code: str) -> dict[str, Any]:
    """tool 응답의 JSON payload를 파싱한다."""
    for item in result.get("content", []):
        text = item.get("text")
        if isinstance(text, str):
            payload = json.loads(text)
            if payload.get("code") and payload.get("message"):
                raise HwpForgeRoundtripError(
                    error_code,
                    f"{tool_name} failed: {payload['code']} {payload['message']}",
                )
            return payload
    raise HwpForgeRoundtripError(error_code, f"{tool_name} returned no text payload")


class _McpSession:
    """stdio JSON-RPC로 HwpForge MCP를 호출한다."""

    def __init__(self, runtime: HwpForgeRuntime, work_dir: Path, stderr_path: Path) -> None:
        self._runtime = runtime
        self._work_dir = work_dir
        self._stderr_path = stderr_path
        self._next_id = 1
        self._proc: subprocess.Popen[str] | None = None
        self._stderr_file: Any | None = None

    def __enter__(self) -> "_McpSession":
        """세션 시작 후 initialize를 수행한다."""
        self._start()
        self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mathocr-hwpforge-roundtrip", "version": "0.1.0"},
            },
            HWPFORGE_SECTION_BUILD_FAILED_CODE,
        )
        self._notify("notifications/initialized", {})
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        """세션 종료 시 프로세스를 정리한다."""
        self.close()

    def _start(self) -> None:
        """MCP subprocess를 실행한다."""
        self._stderr_path.parent.mkdir(parents=True, exist_ok=True)
        self._stderr_file = self._stderr_path.open("a", encoding="utf-8")
        self._proc = subprocess.Popen(
            list(self._runtime.command),
            cwd=str(self._work_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr_file,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=False,
        )

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        """id가 없는 JSON-RPC 알림을 보낸다."""
        self._write_message({"jsonrpc": "2.0", "method": method, "params": params})

    def _write_message(self, payload: dict[str, Any]) -> None:
        """stdin에 JSON-RPC 한 줄 메시지를 쓴다."""
        if self._proc is None or self._proc.stdin is None:
            raise HwpForgeRoundtripError(HWPFORGE_SECTION_BUILD_FAILED_CODE, "MCP stdin is unavailable")
        self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _request(self, method: str, params: dict[str, Any], error_code: str) -> dict[str, Any]:
        """응답이 필요한 JSON-RPC 요청을 보낸다."""
        request_id = self._next_id
        self._next_id += 1
        self._write_message({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        return self._read_response(request_id, error_code)

    def _read_response(self, request_id: int, error_code: str) -> dict[str, Any]:
        """해당 request id의 JSON-RPC 응답을 읽는다."""
        if self._proc is None or self._proc.stdout is None:
            raise HwpForgeRoundtripError(error_code, "MCP stdout is unavailable")
        while True:
            raw_line = self._proc.stdout.readline()
            if raw_line == "":
                raise HwpForgeRoundtripError(error_code, "HwpForge MCP closed without a response")
            line = raw_line.strip()
            if not line:
                continue
            message = json.loads(line)
            if message.get("id") != request_id:
                continue
            if message.get("error"):
                raise HwpForgeRoundtripError(error_code, json.dumps(message["error"], ensure_ascii=False))
            return message.get("result", {})

    def call_tool(self, tool_name: str, arguments: dict[str, Any], error_code: str) -> dict[str, Any]:
        """tool 호출 후 JSON payload를 반환한다."""
        result = self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            error_code,
        )
        return _extract_tool_payload(result, tool_name, error_code)

    def close(self) -> None:
        """열린 리소스를 순서대로 정리한다."""
        if self._proc is not None and self._proc.stdin is not None:
            self._proc.stdin.close()
        if self._proc is not None:
            self._proc.kill()
        if self._stderr_file is not None:
            self._stderr_file.close()


def _extract_section_xml(roundtrip_hwpx_path: Path, section_output_path: Path) -> Path:
    """roundtrip HWPX에서 section0.xml만 분리해 저장한다."""
    with ZipFile(roundtrip_hwpx_path, "r") as archive:
        try:
            section_bytes = archive.read("Contents/section0.xml")
        except KeyError as error:
            raise HwpForgeRoundtripError(
                HWPFORGE_SECTION_BUILD_FAILED_CODE,
                "roundtrip hwpx missing Contents/section0.xml",
            ) from error
    section_output_path.write_bytes(section_bytes)
    return section_output_path


def _inspect_and_validate_generated_hwpx(session: _McpSession, hwpx_path: Path) -> None:
    """생성된 HWPX를 inspect + validate로 공통 검증한다."""
    session.call_tool(
        "hwpforge_inspect",
        {"file_path": str(hwpx_path)},
        HWPFORGE_SECTION_BUILD_FAILED_CODE,
    )
    session.call_tool(
        "hwpforge_validate",
        {"file_path": str(hwpx_path)},
        HWPX_VALIDATE_FAILED_CODE,
    )


def build_section_from_structure_via_hwpforge(
    structure: dict[str, Any],
    output_dir: Path,
    runtime_path: str | None = None,
) -> Path:
    """ExportedDocument JSON 구조에서 section0.xml만 직접 생성한다."""
    runtime = resolve_hwpforge_runtime(APP_ROOT, runtime_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    roundtrip_hwpx_path = output_dir / "hwpforge.direct.hwpx"
    section_path = output_dir / "section0.hwpforge.xml"
    stderr_path = output_dir / "hwpforge.stderr.log"
    structure_text = json.dumps(structure, ensure_ascii=False)
    with _McpSession(runtime, output_dir, stderr_path) as session:
        session.call_tool(
            "hwpforge_from_json",
            {"structure": structure_text, "output_path": str(roundtrip_hwpx_path)},
            HWPFORGE_SECTION_BUILD_FAILED_CODE,
        )
        _inspect_and_validate_generated_hwpx(session, roundtrip_hwpx_path)
    return _extract_section_xml(roundtrip_hwpx_path, section_path)


def roundtrip_section_via_hwpforge(
    base_hwpx_path: Path,
    output_dir: Path,
    runtime_path: str | None = None,
) -> Path:
    """baseline HWPX를 HwpForge로 roundtrip한 뒤 section0.xml만 반환한다."""
    runtime = resolve_hwpforge_runtime(APP_ROOT, runtime_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "hwpforge.roundtrip.json"
    roundtrip_hwpx_path = output_dir / "hwpforge.roundtrip.hwpx"
    section_path = output_dir / "section0.hwpforge.xml"
    stderr_path = output_dir / "hwpforge.stderr.log"
    with _McpSession(runtime, output_dir, stderr_path) as session:
        session.call_tool(
            "hwpforge_to_json",
            {"file_path": str(base_hwpx_path), "output_path": str(json_path)},
            HWPFORGE_SECTION_BUILD_FAILED_CODE,
        )
        structure = json_path.read_text(encoding="utf-8")
        session.call_tool(
            "hwpforge_from_json",
            {"structure": structure, "output_path": str(roundtrip_hwpx_path)},
            HWPFORGE_SECTION_BUILD_FAILED_CODE,
        )
        _inspect_and_validate_generated_hwpx(session, roundtrip_hwpx_path)
    return _extract_section_xml(roundtrip_hwpx_path, section_path)


def build_section_via_hwpforge(
    root_path: Path,
    job: Any,
    bindata_dir: Path,
    output_dir: Path,
    year: str,
    warnings: Any,
    runtime_path: str | None = None,
    app_root: Path = APP_ROOT,
) -> tuple[Path, list[dict[str, str]]]:
    """export IR을 HwpForge JSON으로 변환해 직접 section0.xml을 생성한다."""
    runtime = resolve_hwpforge_runtime(app_root, runtime_path)
    template_json_path = resolve_hwpforge_template_json_path(app_root)
    template_document = json.loads(template_json_path.read_text(encoding="utf-8"))
    bindata_dir.mkdir(parents=True, exist_ok=True)
    export_ir, images_info = build_hwpforge_export_ir(
        root_path=root_path,
        job=job,
        bindata_dir=bindata_dir,
        year=year,
        warnings=warnings,
    )
    exported_document = build_exported_document_from_template(template_document, export_ir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "hwpforge.direct.json"
    generated_hwpx_path = output_dir / "hwpforge.direct.hwpx"
    section_path = output_dir / "section0.direct.xml"
    stderr_path = output_dir / "hwpforge.direct.stderr.log"
    structure_text = json.dumps(exported_document, ensure_ascii=False)
    json_path.write_text(structure_text, encoding="utf-8")
    with _McpSession(runtime, output_dir, stderr_path) as session:
        session.call_tool(
            "hwpforge_from_json",
            {"structure": structure_text, "output_path": str(generated_hwpx_path)},
            HWPFORGE_SECTION_BUILD_FAILED_CODE,
        )
        session.call_tool(
            "hwpforge_inspect",
            {"file_path": str(generated_hwpx_path)},
            HWPFORGE_SECTION_BUILD_FAILED_CODE,
        )
        session.call_tool(
            "hwpforge_validate",
            {"file_path": str(generated_hwpx_path)},
            HWPX_VALIDATE_FAILED_CODE,
        )
    return _extract_section_xml(generated_hwpx_path, section_path), images_info


def inspect_and_validate_hwpx_via_hwpforge(
    hwpx_path: Path,
    runtime_path: str | None = None,
) -> None:
    """최종 HWPX를 HwpForge inspect + validate로 다시 확인한다."""
    runtime = resolve_hwpforge_runtime(APP_ROOT, runtime_path)
    work_dir = hwpx_path.parent / "hwpforge-final-check"
    stderr_path = work_dir / "hwpforge.stderr.log"
    work_dir.mkdir(parents=True, exist_ok=True)
    with _McpSession(runtime, work_dir, stderr_path) as session:
        session.call_tool(
            "hwpforge_inspect",
            {"file_path": str(hwpx_path)},
            HWPFORGE_SECTION_BUILD_FAILED_CODE,
        )
        session.call_tool(
            "hwpforge_validate",
            {"file_path": str(hwpx_path)},
            HWPX_VALIDATE_FAILED_CODE,
        )
