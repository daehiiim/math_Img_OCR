from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_NAME = "generated-canonical-sample.hwpx"
HWPFORGE_RUNTIME_UNAVAILABLE = "HWPFORGE_RUNTIME_UNAVAILABLE"
HWPFORGE_SECTION_BUILD_FAILED = "HWPFORGE_SECTION_BUILD_FAILED"
HWPX_VALIDATE_FAILED = "HWPX_VALIDATE_FAILED"
LOCAL_MCP_RELATIVE_PATHS = (
    Path(".tmp/hwpforge-poc/from-json-equation/node_modules/@hwpforge/mcp/bin/hwpforge-mcp.js"),
    Path(".tmp/hwpforge-poc/one-question/node_modules/@hwpforge/mcp/bin/hwpforge-mcp.js"),
    Path(".tmp/hwpforge-poc/text-variant-geo/node_modules/@hwpforge/mcp/bin/hwpforge-mcp.js"),
)


@dataclass(frozen=True)
class HwpForgeSegment:
    """HwpForge 문단 한 조각을 텍스트/수식 단위로 표현한다."""

    kind: str
    value: str


@dataclass(frozen=True)
class HwpForgeParagraph:
    """HwpForge helper가 생성할 문단의 segment 목록을 보관한다."""

    segments: tuple[HwpForgeSegment, ...]


@dataclass(frozen=True)
class HwpForgeDocumentRequest:
    """sample 기반 HwpForge 문서 생성 입력값을 보관한다."""

    output_hwpx_path: Path
    stem: str
    choices: tuple[str, ...]
    explanation_paragraphs: tuple[HwpForgeParagraph, ...]
    problem_number: int = 1
    year: str | None = None
    sample_hwpx_path: Path | None = None
    mcp_script_path: Path | None = None
    work_dir: Path | None = None


@dataclass(frozen=True)
class HwpForgeDocumentResult:
    """helper 실행 후 생성된 HWPX 요약값을 보관한다."""

    output_hwpx_path: Path
    paragraphs: int
    tables: int
    images: int
    summary: str


class HwpForgeHelperError(Exception):
    """예측 가능한 HwpForge helper 오류를 코드와 함께 전달한다."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def build_hwpforge_paragraph(*segments: HwpForgeSegment) -> HwpForgeParagraph:
    """segment 가변 인자를 문단 dataclass로 감싼다."""
    return HwpForgeParagraph(segments=tuple(segments))


def text_segment(value: str) -> HwpForgeSegment:
    """일반 텍스트 segment를 만든다."""
    return HwpForgeSegment(kind="text", value=value)


def equation_segment(value: str) -> HwpForgeSegment:
    """한글 수식 script segment를 만든다."""
    return HwpForgeSegment(kind="equation", value=value)


def generate_hwpx_with_hwpforge(
    request: HwpForgeDocumentRequest,
    *,
    app_root: Path = ROOT,
) -> HwpForgeDocumentResult:
    """Node helper를 호출해 sample 기반 HWPX 문서를 생성한다."""
    if request.work_dir is not None:
        request.work_dir.mkdir(parents=True, exist_ok=True)
        return _generate_hwpx_with_work_dir(request, request.work_dir, app_root)
    with tempfile.TemporaryDirectory() as tmpdir_str:
        return _generate_hwpx_with_work_dir(request, Path(tmpdir_str), app_root)


def _generate_hwpx_with_work_dir(
    request: HwpForgeDocumentRequest,
    work_dir: Path,
    app_root: Path,
) -> HwpForgeDocumentResult:
    """요청/응답 파일을 만들고 helper 프로세스를 실행한다."""
    request_path = work_dir / "hwpforge-request.json"
    response_path = work_dir / "hwpforge-response.json"
    request_path.write_text(
        json.dumps(_build_request_payload(request, app_root), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    completed = _run_hwpforge_helper(app_root, request_path, response_path)
    return _parse_hwpforge_response(response_path, completed)


def _build_request_payload(request: HwpForgeDocumentRequest, app_root: Path) -> dict[str, object]:
    """Node helper가 읽을 JSON payload를 직렬화한다."""
    return {
        "output_hwpx_path": str(request.output_hwpx_path),
        "sample_hwpx_path": str(_resolve_sample_hwpx_path(request, app_root)),
        "mcp_script_path": str(_resolve_mcp_script_path(request, app_root)),
        "problem_number": request.problem_number,
        "year": request.year,
        "stem": request.stem,
        "choices": list(request.choices),
        "explanation_paragraphs": [
            {"segments": [{"kind": segment.kind, "value": segment.value} for segment in paragraph.segments]}
            for paragraph in request.explanation_paragraphs
        ],
    }


def _resolve_sample_hwpx_path(request: HwpForgeDocumentRequest, app_root: Path) -> Path:
    """sample baseline HWPX 경로를 정규화한다."""
    sample_path = request.sample_hwpx_path or (app_root.parent / "templates" / DEFAULT_SAMPLE_NAME)
    if sample_path.exists():
        return sample_path
    raise HwpForgeHelperError(
        HWPFORGE_RUNTIME_UNAVAILABLE,
        f"hwpforge sample hwpx not found: {sample_path}",
    )


def _resolve_mcp_script_path(request: HwpForgeDocumentRequest, app_root: Path) -> Path:
    """사용 가능한 로컬 HwpForge MCP 진입점을 찾는다."""
    if request.mcp_script_path is not None and request.mcp_script_path.exists():
        return request.mcp_script_path
    env_path = _resolve_env_mcp_path()
    if env_path is not None:
        return env_path
    checked_paths: list[str] = []
    for candidate in _iter_mcp_candidates(app_root.parent):
        checked_paths.append(str(candidate))
        if candidate.exists():
            return candidate
    raise HwpForgeHelperError(
        HWPFORGE_RUNTIME_UNAVAILABLE,
        "hwpforge mcp runtime not found: " + "; ".join(checked_paths),
    )


def _resolve_env_mcp_path() -> Path | None:
    """환경변수로 전달된 MCP 경로가 있으면 우선 사용한다."""
    raw_value = os.getenv("HWPFORGE_MCP_PATH")
    if raw_value is None or not raw_value.strip():
        return None
    candidate = Path(raw_value.strip()).expanduser()
    return candidate if candidate.exists() else None


def _iter_mcp_candidates(repo_root: Path) -> tuple[Path, ...]:
    """저장소 안에서 바로 확인 가능한 MCP 후보 경로를 만든다."""
    candidates = [repo_root / relative_path for relative_path in LOCAL_MCP_RELATIVE_PATHS]
    return tuple(dict.fromkeys(candidates))


def _run_hwpforge_helper(app_root: Path, request_path: Path, response_path: Path) -> subprocess.CompletedProcess[str]:
    """Node helper 프로세스를 실행하고 stdout/stderr를 수집한다."""
    node_path = shutil.which("node")
    if node_path is None:
        raise HwpForgeHelperError(HWPFORGE_RUNTIME_UNAVAILABLE, "node runtime not found")
    helper_script_path = app_root / "scripts" / "hwpforge_doc_helper.js"
    if not helper_script_path.exists():
        raise HwpForgeHelperError(
            HWPFORGE_RUNTIME_UNAVAILABLE,
            f"hwpforge helper script missing: {helper_script_path}",
        )
    return subprocess.run(
        [node_path, str(helper_script_path), "--request", str(request_path), "--response", str(response_path)],
        cwd=str(app_root.parent),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def _parse_hwpforge_response(
    response_path: Path,
    completed: subprocess.CompletedProcess[str],
) -> HwpForgeDocumentResult:
    """helper 응답 JSON과 프로세스 종료 코드를 함께 검증한다."""
    payload = _read_response_payload(response_path, completed)
    if completed.returncode != 0 or not payload.get("success", False):
        error = payload.get("error", {})
        raise HwpForgeHelperError(
            str(error.get("code", HWPFORGE_SECTION_BUILD_FAILED)),
            str(error.get("message", completed.stderr.strip() or completed.stdout.strip() or "helper failed")),
        )
    data = payload.get("data", {})
    return HwpForgeDocumentResult(
        output_hwpx_path=Path(str(data["output_hwpx_path"])),
        paragraphs=int(data["paragraphs"]),
        tables=int(data["tables"]),
        images=int(data["images"]),
        summary=str(data["summary"]),
    )


def _read_response_payload(
    response_path: Path,
    completed: subprocess.CompletedProcess[str],
) -> dict[str, object]:
    """helper가 남긴 response 파일을 읽고 실패 시 공통 오류로 바꾼다."""
    if response_path.exists():
        return json.loads(response_path.read_text(encoding="utf-8"))
    raise HwpForgeHelperError(
        HWPFORGE_SECTION_BUILD_FAILED,
        completed.stderr.strip() or completed.stdout.strip() or "helper response missing",
    )
