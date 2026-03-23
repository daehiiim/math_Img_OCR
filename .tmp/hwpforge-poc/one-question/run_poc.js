const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const ROOT = "D:\\03_PROJECT\\05_mathOCR";
const WORK_SUBDIR = process.env.HWPFORGE_POC_WORK_SUBDIR || "one-question";
const WORK_DIR = path.join(ROOT, ".tmp", "hwpforge-poc", WORK_SUBDIR);
const SAMPLE_PATH =
  process.env.HWPFORGE_POC_SAMPLE_PATH || path.join(ROOT, "templates", "generated-canonical-sample.hwpx");
const MCP_LOCAL_BIN = path.join(
  WORK_DIR,
  "node_modules",
  "@hwpforge",
  "mcp",
  "bin",
  "hwpforge-mcp.js",
);
const REQUEST_TIMEOUT_MS = 120000;
const STEM_REPLACEMENT =
  process.env.HWPFORGE_POC_STEM || "[PoC] preserving patch stem 검증 문장";
const EXPLANATION_REPLACEMENT =
  process.env.HWPFORGE_POC_EXPLANATION || "[PoC] preserving patch explanation 검증 문장";
const CHANGE_EQUATIONS = process.env.HWPFORGE_POC_CHANGE_EQUATIONS === "1";

/**
 * 작업에 필요한 경로를 한곳에서 관리한다.
 */
function buildPaths() {
  return {
    workDir: WORK_DIR,
    artifactsDir: path.join(WORK_DIR, "artifacts"),
    logsDir: path.join(WORK_DIR, "logs"),
    baselinePath: path.join(WORK_DIR, "baseline.hwpx"),
    patchedPath: path.join(WORK_DIR, "patched.hwpx"),
    originalJsonPath: path.join(WORK_DIR, "section0.original.json"),
    editedJsonPath: path.join(WORK_DIR, "section0.edited.json"),
    patchedJsonPath: path.join(WORK_DIR, "section0.patched.json"),
    summaryPath: path.join(WORK_DIR, "run-summary.json"),
    toolsPath: path.join(WORK_DIR, "artifacts", "tools.json"),
    slotReportPath: path.join(WORK_DIR, "artifacts", "slot-report.json"),
    baselineInspectPath: path.join(WORK_DIR, "artifacts", "inspect-baseline.json"),
    patchedInspectPath: path.join(WORK_DIR, "artifacts", "inspect-patched.json"),
    stderrLogPath: path.join(WORK_DIR, "logs", "hwpforge-stderr.log"),
  };
}

/**
 * 디렉터리 구조를 준비한다.
 */
function ensureDirs(paths) {
  [paths.workDir, paths.artifactsDir, paths.logsDir].forEach((dir) => {
    fs.mkdirSync(dir, { recursive: true });
  });
}

/**
 * JSON 파일을 보기 좋은 형식으로 저장한다.
 */
function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

/**
 * UTF-8 JSON 파일을 읽어 객체로 반환한다.
 */
function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

/**
 * baseline 샘플을 작업본으로 복사한다.
 */
function copyBaseline(paths) {
  fs.copyFileSync(SAMPLE_PATH, paths.baselinePath);
}

/**
 * 문자열이 편집 가능한 본문 텍스트 후보인지 판정한다.
 */
function isEditableTextSlot(slot) {
  const text = String(slot.original_text || "").trim();
  if (!text) return false;
  if (/^\[해설\]$/.test(text)) return false;
  if (/^<.+>$/.test(text)) return false;
  if (/^[0-9①-⑤.\s]+$/.test(text)) return false;
  return /[가-힣A-Za-z]/.test(text);
}

/**
 * 우선순위 패턴으로 적절한 text slot을 찾는다.
 */
function findSlotByPatterns(slots, patterns, usedPaths) {
  return slots.find((slot) => {
    const text = String(slot.original_text || "");
    return !usedPaths.has(slot.path) && patterns.some((pattern) => pattern.test(text));
  });
}

/**
 * 문제 본문에 해당하는 text slot을 고른다.
 */
function selectStemSlot(slots, usedPaths) {
  const preferred = [/x의 값/, /△ABC/, /AD = 8cm/, /\[4점\]/];
  return (
    findSlotByPatterns(slots, preferred, usedPaths) ||
    slots.find((slot) => !usedPaths.has(slot.path) && isEditableTextSlot(slot))
  );
}

/**
 * 해설 본문에 해당하는 text slot을 고른다.
 */
function selectExplanationSlot(slots, usedPaths) {
  const preferred = [/주어진 조건/, /닮음/, /또한/];
  const direct = findSlotByPatterns(slots, preferred, usedPaths);
  if (direct) return direct;

  const markerIndex = slots.findIndex((slot) => String(slot.original_text || "").trim() === "[해설]");
  if (markerIndex >= 0) {
    return slots
      .slice(markerIndex + 1)
      .find((slot) => !usedPaths.has(slot.path) && isEditableTextSlot(slot));
  }

  return slots.find((slot) => !usedPaths.has(slot.path) && isEditableTextSlot(slot));
}

/**
 * semantic path 문자열을 탐색 가능한 토큰 배열로 변환한다.
 */
function parseSemanticPath(pathText) {
  const tokens = [];
  const parts = pathText.split(".");
  const pattern = /([^[\]]+)|\[(\d+)\]/g;
  parts.forEach((part) => {
    let match;
    while ((match = pattern.exec(part)) !== null) {
      if (match[1]) tokens.push(match[1]);
      if (match[2]) tokens.push(Number(match[2]));
    }
  });
  return tokens;
}

/**
 * preservation token을 실제 JSON 노드로 해석한다.
 */
function resolveSemanticToken(current, token, isLeaf) {
  if (typeof token === "number") return current[token];
  if (current && Object.prototype.hasOwnProperty.call(current, token)) {
    return isLeaf ? { parent: current, key: token } : current[token];
  }

  if (current && current.content) {
    if (token === "text" && Object.prototype.hasOwnProperty.call(current.content, "Text")) {
      return isLeaf ? { parent: current.content, key: "Text" } : current.content.Text;
    }
    if (token === "table" && current.content.Table) return current.content.Table;
    if (token === "control" && current.content.Control) return current.content.Control;
    if (token === "image" && current.content.Image) return current.content.Image;
  }

  const aliasMap = {
    textbox: "TextBox",
    field: "Field",
    equation: "Equation",
    line: "Line",
    rect: "Rect",
    ellipse: "Ellipse",
    polygon: "Polygon",
  };
  const alias = aliasMap[token];
  if (alias && current && Object.prototype.hasOwnProperty.call(current, alias)) {
    return isLeaf ? { parent: current, key: alias } : current[alias];
  }

  return undefined;
}

/**
 * ExportedSection의 section 내부 scalar 값을 path 기준으로 수정한다.
 */
function setSectionScalar(section, semanticPath, replacement) {
  const tokens = parseSemanticPath(semanticPath);
  let current = section;

  for (let index = 0; index < tokens.length - 1; index += 1) {
    current = resolveSemanticToken(current, tokens[index], false);
    if (current === undefined || current === null) {
      throw new Error(`경로를 찾을 수 없습니다: ${semanticPath}`);
    }
  }

  const leaf = tokens[tokens.length - 1];
  const resolvedLeaf = resolveSemanticToken(current, leaf, true);
  if (!resolvedLeaf || typeof resolvedLeaf.parent[resolvedLeaf.key] !== "string") {
    throw new Error(`문자열 leaf가 아닙니다: ${semanticPath}`);
  }

  resolvedLeaf.parent[resolvedLeaf.key] = replacement;
}

/**
 * preservation slot 목록을 사람이 보기 좋은 형태로 정리한다.
 */
function buildSlotReport(slots) {
  return slots.map((slot, index) => ({
    index,
    path: slot.path,
    original_text: slot.original_text,
    has_inline_markup: slot.has_inline_markup,
  }));
}

/**
 * stdio 기반 MCP JSON-RPC 클라이언트다.
 */
class McpClient {
  constructor(command, args, cwd, stderrPath) {
    this.command = command;
    this.args = args;
    this.cwd = cwd;
    this.stderrPath = stderrPath;
    this.buffer = "";
    this.nextId = 1;
    this.pending = new Map();
    this.protocolVersion = null;
    this.proc = null;
  }

  /**
   * MCP 서버 프로세스를 실행하고 stdio를 연결한다.
   */
  start() {
    this.proc = spawn(this.command, this.args, {
      cwd: this.cwd,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    this.proc.stdout.on("data", (chunk) => this.consumeStdout(chunk));
    this.proc.stderr.on("data", (chunk) => {
      fs.appendFileSync(this.stderrPath, chunk);
    });
    this.proc.on("exit", (code, signal) => this.handleExit(code, signal));
    this.proc.on("error", (error) => this.rejectAll(error));
  }

  /**
   * 프로세스 종료 시 대기 중인 요청을 모두 실패 처리한다.
   */
  handleExit(code, signal) {
    const reason = new Error(`MCP 서버가 종료되었습니다. code=${code} signal=${signal}`);
    this.rejectAll(reason);
  }

  /**
   * 대기 중인 요청에 동일한 에러를 전파한다.
   */
  rejectAll(error) {
    this.pending.forEach(({ reject, timer }) => {
      clearTimeout(timer);
      reject(error);
    });
    this.pending.clear();
  }

  /**
   * stdout 바이트 스트림을 줄 단위 JSON 메시지로 분리한다.
   */
  consumeStdout(chunk) {
    this.buffer += chunk.toString("utf8");
    const lines = this.buffer.split(/\r?\n/);
    this.buffer = lines.pop() || "";
    lines
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .forEach((line) => this.handleMessage(JSON.parse(line)));
  }

  /**
   * 응답 메시지를 요청 ID에 맞게 resolve 또는 reject 한다.
   */
  handleMessage(message) {
    if (message.id === undefined || !this.pending.has(message.id)) return;

    const pending = this.pending.get(message.id);
    clearTimeout(pending.timer);
    this.pending.delete(message.id);

    if (message.error) {
      pending.reject(new Error(JSON.stringify(message.error)));
      return;
    }

    pending.resolve(message.result);
  }

  /**
   * JSON-RPC 요청을 전송한다.
   */
  request(method, params) {
    return new Promise((resolve, reject) => {
      const id = this.nextId;
      const payload = { jsonrpc: "2.0", id, method };
      if (params !== undefined) payload.params = params;

      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`요청 타임아웃: ${method}`));
      }, REQUEST_TIMEOUT_MS);

      this.pending.set(id, { resolve, reject, timer });
      this.nextId += 1;
      this.writeMessage(payload);
    });
  }

  /**
   * JSON-RPC 알림 메시지를 전송한다.
   */
  notify(method, params) {
    const payload = { jsonrpc: "2.0", method };
    if (params !== undefined) payload.params = params;
    this.writeMessage(payload);
  }

  /**
   * JSON 메시지를 줄 단위 스트림으로 인코딩한다.
   */
  writeMessage(payload) {
    this.proc.stdin.write(`${JSON.stringify(payload)}\n`, "utf8");
  }

  /**
   * initialize 핸드셰이크를 수행하고 협상된 버전을 저장한다.
   */
  async initialize() {
    const versions = ["2025-03-26", "2024-11-05"];

    for (const version of versions) {
      try {
        const result = await this.request("initialize", {
          protocolVersion: version,
          capabilities: {},
          clientInfo: { name: "hwpforge-poc", version: "0.1.0" },
        });
        this.protocolVersion = result.protocolVersion || version;
        this.notify("notifications/initialized");
        return result;
      } catch (error) {
        if (version === versions[versions.length - 1]) throw error;
      }
    }
  }

  /**
   * 서버가 제공하는 tool 목록을 가져온다.
   */
  async listTools() {
    return this.request("tools/list", {});
  }

  /**
   * 특정 MCP tool을 호출한다.
   */
  async callTool(name, args) {
    return this.request("tools/call", { name, arguments: args });
  }

  /**
   * 서버 stdin을 닫고 프로세스를 종료한다.
   */
  close() {
    if (!this.proc) return;
    this.proc.stdin.end();
    this.proc.kill();
  }
}

/**
 * MCP tool 결과의 첫 번째 text payload를 JSON으로 변환한다.
 */
function parseToolPayload(result) {
  const content = Array.isArray(result.content) ? result.content : [];
  const textItem = content.find((item) => typeof item.text === "string");
  if (!textItem) throw new Error("tool 응답에서 text payload를 찾지 못했습니다.");
  return JSON.parse(textItem.text);
}

/**
 * tool 에러를 계획용 에러 코드로 정규화한다.
 */
function normalizeToolError(toolName, payload) {
  if (!payload || !payload.code || !payload.message) return null;

  if (toolName === "hwpforge_to_json" && payload.code === "PATCH_ERROR") {
    return {
      code: "HWPFORGE_EXPORT_UNSUPPORTED",
      message: "이 샘플은 현재 HwpForge preserving patch 경로에서 직접 편집할 수 없는 구조입니다.",
      detail: payload,
    };
  }

  if (toolName === "hwpforge_patch" && payload.code === "PATCH_ERROR") {
    const lowered = `${payload.message} ${payload.hint || ""}`.toLowerCase();
    const structural = /style-store|master page|structural change/.test(lowered);
    return {
      code: structural ? "HWPFORGE_PATCH_SCOPE_UNSUPPORTED" : "HWPFORGE_PATCH_INVALID",
      message: structural
        ? "현재 HwpForge patch 경로는 텍스트 이외 변경을 허용하지 않습니다."
        : "패치 결과 HWPX가 유효하지 않아 현재 양식 보존 경로로 사용할 수 없습니다.",
      detail: payload,
    };
  }

  return {
    code: "HWPFORGE_PATCH_INVALID",
    message: payload.message,
    detail: payload,
  };
}

/**
 * raw MCP 응답과 파싱된 payload를 모두 파일로 남긴다.
 */
function persistToolArtifacts(rawPath, parsedPath, result, payload) {
  writeJson(rawPath, result);
  writeJson(parsedPath, payload);
}

/**
 * tool 호출을 수행하고 구조화된 에러를 검사한다.
 */
async function callToolAndSave(client, name, args, baseName, paths) {
  const rawPath = path.join(paths.artifactsDir, `${baseName}.raw.json`);
  const parsedPath = path.join(paths.artifactsDir, `${baseName}.parsed.json`);
  const result = await client.callTool(name, args);
  const payload = parseToolPayload(result);
  persistToolArtifacts(rawPath, parsedPath, result, payload);

  const normalized = normalizeToolError(name, payload);
  if (normalized) throw normalized;
  return payload;
}

/**
 * POC 실패 정보를 요약용 객체로 변환한다.
 */
function toFailure(error) {
  if (error && error.code && error.message) return error;

  return {
    code: "HWPFORGE_RUNTIME_UNAVAILABLE",
    message: "HwpForge 실행 환경을 준비하지 못했습니다. npm 배포물 또는 네트워크 상태를 확인해야 합니다.",
    detail: { raw: String(error && error.message ? error.message : error) },
  };
}

/**
 * 선택된 slot 두 곳을 section JSON에 반영한다.
 */
function applyReplacements(exported, selected) {
  setSectionScalar(exported.section, selected.stem.path, STEM_REPLACEMENT);
  setSectionScalar(exported.section, selected.explanation.path, EXPLANATION_REPLACEMENT);
  buildEquationChanges().forEach(({ path: semanticPath, value }) => {
    setSectionScalar(exported.section, semanticPath, value);
  });
}

/**
 * 선택적 수식 변경 목록을 반환한다.
 */
function buildEquationChanges() {
  if (!CHANGE_EQUATIONS) return [];

  return [
    { path: "paragraphs[3].runs[5].control.equation.script", value: "2" },
    { path: "paragraphs[3].runs[6].control.equation.script", value: "5 over 3" },
    { path: "paragraphs[3].runs[7].control.equation.script", value: "11 over 4" },
    { path: "paragraphs[3].runs[8].control.equation.script", value: "8 over 3" },
    { path: "paragraphs[3].runs[9].control.equation.script", value: "7 over 2" },
    { path: "paragraphs[8].runs[2].control.equation.script", value: "ANGLE QPR= ANGLE SRT" },
    { path: "paragraphs[8].runs[3].control.equation.script", value: "ANGLE PQR= ANGLE STR" },
    { path: "paragraphs[9].runs[3].control.equation.script", value: "PQR" },
    { path: "paragraphs[9].runs[4].control.equation.script", value: "SRT" },
  ];
}

/**
 * 로컬 설치된 MCP 실행 경로를 검증하고 명령 배열을 만든다.
 */
function resolveMcpRuntime() {
  if (!fs.existsSync(MCP_LOCAL_BIN)) {
    throw new Error(`로컬 MCP 실행 파일이 없습니다: ${MCP_LOCAL_BIN}`);
  }

  return {
    command: process.execPath,
    args: [MCP_LOCAL_BIN],
  };
}

/**
 * 전체 POC를 순서대로 실행하고 산출물을 저장한다.
 */
async function run() {
  const paths = buildPaths();
  const summary = {
    sample_path: SAMPLE_PATH,
    work_dir: paths.workDir,
    npm_package: "@hwpforge/mcp@0.5.0",
    statuses: {
      scenarioA_baseline_inspect: false,
      scenarioB_section_export: false,
      scenarioC_patch_success: false,
      scenarioD_reparse_success: false,
    },
  };

  ensureDirs(paths);
  copyBaseline(paths);
  fs.writeFileSync(paths.stderrLogPath, "", "utf8");

  const runtime = resolveMcpRuntime();
  summary.runtime = runtime;
  const client = new McpClient(runtime.command, runtime.args, paths.workDir, paths.stderrLogPath);
  client.start();

  try {
    summary.initialize = await client.initialize();
    const tools = await client.listTools();
    writeJson(paths.toolsPath, tools);

    summary.baseline_inspect = await callToolAndSave(
      client,
      "hwpforge_inspect",
      { file_path: paths.baselinePath },
      "inspect-baseline",
      paths,
    );
    writeJson(paths.baselineInspectPath, summary.baseline_inspect);
    summary.statuses.scenarioA_baseline_inspect = true;

    summary.section_export = await callToolAndSave(
      client,
      "hwpforge_to_json",
      { file_path: paths.baselinePath, section: 0, output_path: paths.originalJsonPath },
      "to-json-baseline",
      paths,
    );
    summary.statuses.scenarioB_section_export = true;

    const exported = readJson(paths.originalJsonPath);
    const slots = exported.preservation && Array.isArray(exported.preservation.text_slots)
      ? exported.preservation.text_slots
      : [];
    writeJson(paths.slotReportPath, buildSlotReport(slots));

    if (slots.length === 0) {
      throw {
        code: "HWPFORGE_EXPORT_UNSUPPORTED",
        message: "이 샘플은 현재 HwpForge preserving patch 경로에서 직접 편집할 수 없는 구조입니다.",
        detail: { reason: "preservation text slots not found" },
      };
    }

    const usedPaths = new Set();
    const stem = selectStemSlot(slots, usedPaths);
    if (!stem) throw new Error("문제 본문 slot을 찾지 못했습니다.");
    usedPaths.add(stem.path);

    const explanation = selectExplanationSlot(slots, usedPaths);
    if (!explanation) throw new Error("해설 본문 slot을 찾지 못했습니다.");
    usedPaths.add(explanation.path);

    summary.selected_slots = {
      stem: { path: stem.path, original_text: stem.original_text },
      explanation: { path: explanation.path, original_text: explanation.original_text },
    };

    applyReplacements(exported, { stem, explanation });
    writeJson(paths.editedJsonPath, exported);

    summary.patch = await callToolAndSave(
      client,
      "hwpforge_patch",
      {
        base_path: paths.baselinePath,
        section: 0,
        section_json_path: paths.editedJsonPath,
        output_path: paths.patchedPath,
      },
      "patch-section0",
      paths,
    );
    summary.statuses.scenarioC_patch_success = true;

    summary.patched_inspect = await callToolAndSave(
      client,
      "hwpforge_inspect",
      { file_path: paths.patchedPath },
      "inspect-patched",
      paths,
    );
    writeJson(paths.patchedInspectPath, summary.patched_inspect);

    summary.patched_export = await callToolAndSave(
      client,
      "hwpforge_to_json",
      { file_path: paths.patchedPath, section: 0, output_path: paths.patchedJsonPath },
      "to-json-patched",
      paths,
    );
    summary.statuses.scenarioD_reparse_success = true;
    summary.success = true;
  } catch (error) {
    summary.success = false;
    summary.failure = toFailure(error);
    writeJson(paths.summaryPath, summary);
    client.close();
    throw error;
  }

  writeJson(paths.summaryPath, summary);
  client.close();
}

run().catch((error) => {
  const failure = toFailure(error);
  console.error(JSON.stringify(failure, null, 2));
  process.exit(1);
});
