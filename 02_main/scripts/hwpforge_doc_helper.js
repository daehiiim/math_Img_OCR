const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const HWPFORGE_SECTION_BUILD_FAILED = "HWPFORGE_SECTION_BUILD_FAILED";
const HWPX_VALIDATE_FAILED = "HWPX_VALIDATE_FAILED";

/**
 * JSON 파일을 UTF-8로 읽는다.
 */
function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

/**
 * JSON 파일을 보기 좋은 형태로 기록한다.
 */
function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

/**
 * 단순 JSON deep clone을 수행한다.
 */
function cloneValue(value) {
  return JSON.parse(JSON.stringify(value));
}

/**
 * 필수 CLI 인자를 파싱한다.
 */
function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    result[argv[index]] = argv[index + 1];
  }
  if (!result["--request"] || !result["--response"]) {
    throw new Error("usage: node hwpforge_doc_helper.js --request <json> --response <json>");
  }
  return { requestPath: result["--request"], responsePath: result["--response"] };
}

/**
 * helper 요청 JSON의 최소 필드를 검증한다.
 */
function validateRequest(request) {
  if (!request.sample_hwpx_path || !request.output_hwpx_path || !request.mcp_script_path) {
    throw new Error("sample_hwpx_path, output_hwpx_path, mcp_script_path are required");
  }
  if (!request.stem || !Array.isArray(request.choices) || request.choices.length !== 5) {
    throw new Error("stem and exactly 5 choices are required");
  }
}

/**
 * stdio 기반 MCP JSON-RPC 클라이언트다.
 */
class McpClient {
  constructor(command, args, cwd) {
    this.command = command;
    this.args = args;
    this.cwd = cwd;
    this.buffer = "";
    this.nextId = 1;
    this.pending = new Map();
    this.proc = null;
  }

  /**
   * MCP 서버 프로세스를 실행한다.
   */
  start() {
    this.proc = spawn(this.command, this.args, {
      cwd: this.cwd,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
    this.proc.stdout.on("data", (chunk) => this.consumeStdout(chunk));
    this.proc.stderr.on("data", () => {});
    this.proc.on("error", (error) => this.rejectAll(error));
    this.proc.on("exit", (code, signal) => {
      this.rejectAll(new Error(`MCP server exited code=${code} signal=${signal}`));
    });
  }

  /**
   * 대기 중인 요청을 모두 실패 처리한다.
   */
  rejectAll(error) {
    this.pending.forEach(({ reject, timer }) => {
      clearTimeout(timer);
      reject(error);
    });
    this.pending.clear();
  }

  /**
   * stdout 줄 단위 JSON 메시지를 누적 처리한다.
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
   * 응답 ID에 맞는 Promise를 resolve/reject 한다.
   */
  handleMessage(message) {
    if (message.id === undefined || !this.pending.has(message.id)) {
      return;
    }
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
   * JSON-RPC 요청을 보낸다.
   */
  request(method, params) {
    return new Promise((resolve, reject) => {
      const id = this.nextId;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`request timeout: ${method}`));
      }, 120000);
      this.pending.set(id, { resolve, reject, timer });
      this.nextId += 1;
      this.proc.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`, "utf8");
    });
  }

  /**
   * 알림 메시지를 보낸다.
   */
  notify(method, params) {
    this.proc.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method, params })}\n`, "utf8");
  }

  /**
   * initialize 핸드셰이크를 수행한다.
   */
  async initialize() {
    await this.request("initialize", {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "mathocr-hwpforge-helper", version: "0.1.0" },
    });
    this.notify("notifications/initialized");
  }

  /**
   * MCP tool을 호출한다.
   */
  async callTool(name, args) {
    return this.request("tools/call", { name, arguments: args });
  }

  /**
   * 서버 프로세스를 종료한다.
   */
  close() {
    if (!this.proc) {
      return;
    }
    this.proc.stdin.end();
    this.proc.kill();
  }
}

/**
 * MCP tool payload를 JSON으로 파싱한다.
 */
function parseToolPayload(result) {
  const textItem = (result.content || []).find((item) => typeof item.text === "string");
  if (!textItem) {
    throw new Error("tool response text payload is missing");
  }
  return JSON.parse(textItem.text);
}

/**
 * tool 응답이 구조화 에러면 예외로 바꾼다.
 */
function expectToolSuccess(toolName, result) {
  const payload = parseToolPayload(result);
  if (payload && payload.code && payload.message) {
    throw new Error(`${toolName}: ${payload.code} ${payload.message}`);
  }
  return payload;
}

/**
 * 공통 text run을 만든다.
 */
function buildTextRun(templateRun, value) {
  const run = cloneValue(templateRun);
  run.content = { Text: value };
  return run;
}

/**
 * 공통 equation run을 만든다.
 */
function buildEquationRun(templateRun, script, width) {
  const run = cloneValue(templateRun);
  run.content.Control.Equation.script = script;
  run.content.Control.Equation.width = width;
  return run;
}

/**
 * 수식 폭 계산용 길이 지표를 만든다.
 */
function measureEquationScript(script) {
  return String(script || "").replace(/\s+/g, "").length;
}

/**
 * 템플릿 수식을 기준으로 폭을 선형 추정한다.
 */
function estimateEquationWidth(templateRuns, script, fallbackWidth) {
  const samples = templateRuns
    .map((run) => ({
      metric: measureEquationScript(run.content.Control.Equation.script),
      width: Number(run.content.Control.Equation.width || 0),
    }))
    .filter((sample) => sample.metric > 0 && sample.width > 0)
    .sort((left, right) => left.metric - right.metric);
  const targetMetric = measureEquationScript(script);
  if (samples.length === 0 || targetMetric <= 0) {
    return fallbackWidth;
  }
  if (samples.length === 1) {
    return Math.max(525, Math.round((samples[0].width * targetMetric) / samples[0].metric));
  }
  const low = samples[0];
  const high = samples[samples.length - 1];
  if (low.metric === high.metric) {
    return Math.max(525, low.width);
  }
  const slope = (high.width - low.width) / (high.metric - low.metric);
  const intercept = low.width - slope * low.metric;
  return Math.max(525, Math.round(slope * targetMetric + intercept));
}

/**
 * 문제 본문 문단을 샘플 기반으로 만든다.
 */
function buildProblemParagraph(template, number, stem, year) {
  const paragraph = cloneValue(template);
  const titleRuns = paragraph.runs[0].content.Table.rows[0].cells[0].paragraphs[0].runs;
  titleRuns[0].content.Text = String(titleRuns[0].content.Text || "").replace(/\d{4}학년도/, `${year}학년도`);
  paragraph.runs[3].content.Text = `${number}.`;
  paragraph.runs[4].content.Text = stem;
  return paragraph;
}

/**
 * 보기 문단을 샘플 기반으로 만든다.
 */
function buildChoiceParagraph(template, choices) {
  const paragraph = cloneValue(template);
  const equationRuns = paragraph.runs.filter((run) => run.content && run.content.Control && run.content.Control.Equation);
  choices.forEach((choice, index) => {
    const templateRun = equationRuns[Math.min(index, equationRuns.length - 1)];
    const width = estimateEquationWidth(equationRuns, choice, templateRun.content.Control.Equation.width);
    paragraph.runs[5 + index] = buildEquationRun(templateRun, choice, width);
  });
  return paragraph;
}

/**
 * explanation 본문 문단 배열을 구성한다.
 */
function buildExplanationParagraphs(templates, paragraphs) {
  if (!paragraphs.length) {
    return [];
  }
  const built = [cloneValue(templates.label), cloneValue(templates.blank)];
  paragraphs.forEach((paragraph) => {
    if (!paragraph.segments.length || paragraph.segments.every((segment) => !segment.value)) {
      built.push(cloneValue(templates.blank));
      return;
    }
    if (paragraph.segments.length === 1 && paragraph.segments[0].kind === "text") {
      built.push(buildPlainParagraph(templates.plain, paragraph.segments[0].value));
      return;
    }
    built.push(buildMixedParagraph(templates.mixed, paragraph.segments));
  });
  return built;
}

/**
 * plain 해설 문단을 복제한다.
 */
function buildPlainParagraph(template, text) {
  const paragraph = cloneValue(template);
  paragraph.runs = [buildTextRun(template.runs[0], text)];
  return paragraph;
}

/**
 * mixed 해설 문단을 텍스트/수식 segment로 다시 만든다.
 */
function buildMixedParagraph(template, segments) {
  const paragraph = cloneValue(template);
  const textTemplate = template.runs.find((run) => run.content && Object.prototype.hasOwnProperty.call(run.content, "Text"));
  const equationTemplates = template.runs.filter(
    (run) => run.content && run.content.Control && run.content.Control.Equation,
  );
  paragraph.runs = segments.map((segment) => {
    if (segment.kind === "equation") {
      const templateRun = equationTemplates[0];
      const width = estimateEquationWidth(equationTemplates, segment.value, templateRun.content.Control.Equation.width);
      return buildEquationRun(templateRun, segment.value, width);
    }
    return buildTextRun(textTemplate, segment.value);
  });
  return paragraph;
}

/**
 * 샘플 document JSON을 현재 요청 본문으로 교체한다.
 */
function buildPatchedDocument(exportedDocument, request) {
  const document = cloneValue(exportedDocument);
  const section = document.document.sections[0];
  const paragraphs = section.paragraphs;
  const year = request.year || "2026";
  const nextParagraphs = [
    buildProblemParagraph(paragraphs[0], request.problem_number || 1, request.stem, year),
    cloneValue(paragraphs[1]),
    cloneValue(paragraphs[2]),
    buildChoiceParagraph(paragraphs[3], request.choices),
    cloneValue(paragraphs[4]),
    ...buildExplanationParagraphs(
      {
        label: paragraphs[5],
        blank: paragraphs[6],
        plain: paragraphs[7],
        mixed: paragraphs[8],
      },
      request.explanation_paragraphs || [],
    ),
  ];
  section.paragraphs = nextParagraphs;
  return document;
}

/**
 * tool 요약에서 핵심 수치를 꺼낸다.
 */
function collectMetrics(inspectPayload) {
  return {
    paragraphs: Number(inspectPayload.data.total_paragraphs || 0),
    tables: Number(inspectPayload.data.total_tables || 0),
    images: Number(inspectPayload.data.total_images || 0),
    summary: String(inspectPayload.summary || ""),
  };
}

/**
 * helper 성공 응답을 만든다.
 */
function buildSuccessResponse(request, inspectPayload) {
  const metrics = collectMetrics(inspectPayload);
  return {
    success: true,
    data: {
      output_hwpx_path: request.output_hwpx_path,
      paragraphs: metrics.paragraphs,
      tables: metrics.tables,
      images: metrics.images,
      summary: metrics.summary,
    },
  };
}

/**
 * helper 실패 응답을 만든다.
 */
function buildFailureResponse(code, message, detail) {
  return { success: false, error: { code, message, detail } };
}

/**
 * 전체 helper 워크플로를 실행한다.
 */
async function runHelper(request) {
  validateRequest(request);
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "mathocr-hwpforge-"));
  const originalJsonPath = path.join(workDir, "document.original.json");
  const editedJsonPath = path.join(workDir, "document.edited.json");
  const client = new McpClient(process.execPath, [request.mcp_script_path], workDir);
  client.start();
  try {
    await client.initialize();
    expectToolSuccess(
      "hwpforge_to_json",
      await client.callTool("hwpforge_to_json", {
        file_path: request.sample_hwpx_path,
        output_path: originalJsonPath,
      }),
    );
    const originalDocument = readJson(originalJsonPath);
    const editedDocument = buildPatchedDocument(originalDocument, request);
    writeJson(editedJsonPath, editedDocument);
    expectToolSuccess(
      "hwpforge_from_json",
      await client.callTool("hwpforge_from_json", {
        structure: JSON.stringify(editedDocument),
        output_path: request.output_hwpx_path,
      }),
    );
    const inspectPayload = expectToolSuccess(
      "hwpforge_inspect",
      await client.callTool("hwpforge_inspect", { file_path: request.output_hwpx_path }),
    );
    const validatePayload = expectToolSuccess(
      "hwpforge_validate",
      await client.callTool("hwpforge_validate", { file_path: request.output_hwpx_path }),
    );
    if (!validatePayload.data.valid) {
      return buildFailureResponse(HWPX_VALIDATE_FAILED, "generated hwpx is invalid", validatePayload);
    }
    return buildSuccessResponse(request, inspectPayload);
  } catch (error) {
    return buildFailureResponse(HWPFORGE_SECTION_BUILD_FAILED, String(error.message || error), null);
  } finally {
    client.close();
  }
}

/**
 * main 진입점에서 요청/응답 파일을 연결한다.
 */
async function main() {
  const { requestPath, responsePath } = parseArgs(process.argv.slice(2));
  const request = readJson(requestPath);
  const response = await runHelper(request);
  writeJson(responsePath, response);
  if (!response.success) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
