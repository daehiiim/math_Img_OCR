const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const ROOT = "D:\\03_PROJECT\\05_mathOCR";
const WORK_DIR = path.join(ROOT, ".tmp", "hwpforge-poc", "from-json-equation");
const SAMPLE_PATH = path.join(ROOT, "templates", "generated-canonical-sample.hwpx");
const OUTPUT_PATH = path.join(WORK_DIR, "hwpforge-generated-equation-example.hwpx");
const REPORT_PATH = path.join(WORK_DIR, "generation-report.json");
const ORIGINAL_JSON_PATH = path.join(WORK_DIR, "document.original.json");
const EDITED_JSON_PATH = path.join(WORK_DIR, "document.edited.json");
const GENERATED_JSON_PATH = path.join(WORK_DIR, "document.generated.json");
const STDERR_LOG_PATH = path.join(WORK_DIR, "hwpforge-stderr.log");
const MCP_LOCAL_BIN = path.join(
  WORK_DIR,
  "node_modules",
  "@hwpforge",
  "mcp",
  "bin",
  "hwpforge-mcp.js",
);
const REQUEST_TIMEOUT_MS = 120000;

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function buildRuntime() {
  if (!fs.existsSync(MCP_LOCAL_BIN)) {
    throw new Error(`로컬 MCP 실행 파일이 없습니다: ${MCP_LOCAL_BIN}`);
  }

  return {
    command: process.execPath,
    args: [MCP_LOCAL_BIN],
  };
}

class McpClient {
  constructor(command, args, cwd, stderrPath) {
    this.command = command;
    this.args = args;
    this.cwd = cwd;
    this.stderrPath = stderrPath;
    this.buffer = "";
    this.nextId = 1;
    this.pending = new Map();
  }

  start() {
    this.proc = spawn(this.command, this.args, {
      cwd: this.cwd,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    this.proc.stdout.on("data", (chunk) => this.consumeStdout(chunk));
    this.proc.stderr.on("data", (chunk) => fs.appendFileSync(this.stderrPath, chunk));
    this.proc.on("error", (error) => this.rejectAll(error));
    this.proc.on("exit", (code, signal) => {
      this.rejectAll(new Error(`MCP 서버 종료 code=${code} signal=${signal}`));
    });
  }

  rejectAll(error) {
    this.pending.forEach(({ reject, timer }) => {
      clearTimeout(timer);
      reject(error);
    });
    this.pending.clear();
  }

  consumeStdout(chunk) {
    this.buffer += chunk.toString("utf8");
    const lines = this.buffer.split(/\r?\n/);
    this.buffer = lines.pop() || "";
    lines
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .forEach((line) => this.handleMessage(JSON.parse(line)));
  }

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

  writeMessage(payload) {
    this.proc.stdin.write(`${JSON.stringify(payload)}\n`, "utf8");
  }

  request(method, params) {
    return new Promise((resolve, reject) => {
      const id = this.nextId;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`요청 타임아웃: ${method}`));
      }, REQUEST_TIMEOUT_MS);

      this.pending.set(id, { resolve, reject, timer });
      this.nextId += 1;
      this.writeMessage({ jsonrpc: "2.0", id, method, params });
    });
  }

  notify(method, params) {
    this.writeMessage({ jsonrpc: "2.0", method, params });
  }

  async initialize() {
    const result = await this.request("initialize", {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "hwpforge-equation-check", version: "0.1.0" },
    });
    this.notify("notifications/initialized");
    return result;
  }

  async callTool(name, args) {
    return this.request("tools/call", { name, arguments: args });
  }

  close() {
    if (!this.proc) return;
    this.proc.stdin.end();
    this.proc.kill();
  }
}

function parseToolPayload(result) {
  const textItem = (result.content || []).find((item) => typeof item.text === "string");
  if (!textItem) throw new Error("tool 응답에서 text payload를 찾지 못했습니다.");
  return JSON.parse(textItem.text);
}

function expectToolSuccess(toolName, payload) {
  if (payload && payload.code && payload.message) {
    throw new Error(`${toolName} 실패: ${payload.code} ${payload.message}`);
  }
  return payload;
}

function toolCallResult(name, payload) {
  return {
    name,
    payload,
  };
}

function sectionParagraphs(exportedDocument) {
  return exportedDocument.document.sections[0].paragraphs;
}

function collectEquationScripts(exportedDocument) {
  const scripts = [];

  function visitRuns(runs) {
    runs.forEach((run) => {
      const content = run.content || {};
      if (content.Control && content.Control.Equation) {
        scripts.push(content.Control.Equation.script);
      }
      if (content.Table) {
        content.Table.rows.forEach((row) => {
          row.cells.forEach((cell) => {
            (cell.paragraphs || []).forEach((paragraph) => visitRuns(paragraph.runs || []));
          });
        });
      }
      if (content.Control && content.Control.TextBox) {
        (content.Control.TextBox.paragraphs || []).forEach((paragraph) => visitRuns(paragraph.runs || []));
      }
    });
  }

  exportedDocument.document.sections.forEach((section) => {
    (section.paragraphs || []).forEach((paragraph) => visitRuns(paragraph.runs || []));
  });

  return scripts;
}

function buildEditedDocument(original) {
  const edited = JSON.parse(JSON.stringify(original));
  const paragraphs = sectionParagraphs(edited);

  paragraphs.splice(2, 1);

  paragraphs[0].runs[4].content.Text =
    "HwpForge JSON 생성 예시: △PQR에서 PQ 위의 점 S와 PR 위의 점 T에 대하여 ∠PQR = ∠STR일 때, 닮음 관계를 이용해 y의 값을 구하시오. [4점]";
  paragraphs[2].runs[5].content.Control.Equation.script = "2";
  paragraphs[2].runs[6].content.Control.Equation.script = "5 over 3";
  paragraphs[2].runs[7].content.Control.Equation.script = "11 over 4";
  paragraphs[2].runs[8].content.Control.Equation.script = "8 over 3";
  paragraphs[2].runs[9].content.Control.Equation.script = "7 over 2";

  paragraphs[4].runs[0].content.Text = "[해설] HwpForge 수식 생성 검증";
  paragraphs[6].runs[0].content.Text = "주어진 조건에서 S는 PQ 위, T는 PR 위에 있으므로";
  paragraphs[7].runs[0].content.Text = "이다. 또한";
  paragraphs[7].runs[1].content.Text = "이므로";
  paragraphs[7].runs[2].content.Control.Equation.script = "ANGLE QPR= ANGLE SRT";
  paragraphs[7].runs[3].content.Control.Equation.script = "ANGLE PQR= ANGLE STR";
  paragraphs[8].runs[0].content.Text = "삼각형";
  paragraphs[8].runs[1].content.Text = "와 삼각형";
  paragraphs[8].runs[2].content.Text = "는 서로 닮음이다.";
  paragraphs[8].runs[3].content.Control.Equation.script = "PQR";
  paragraphs[8].runs[4].content.Control.Equation.script = "SRT";

  return edited;
}

async function run() {
  ensureDir(WORK_DIR);
  fs.writeFileSync(STDERR_LOG_PATH, "", "utf8");

  const runtime = buildRuntime();
  const client = new McpClient(runtime.command, runtime.args, WORK_DIR, STDERR_LOG_PATH);
  client.start();

  const report = {
    sample_path: SAMPLE_PATH,
    output_path: OUTPUT_PATH,
    runtime,
  };

  try {
    report.initialize = await client.initialize();

    const toJsonResult = expectToolSuccess(
      "hwpforge_to_json",
      parseToolPayload(
        await client.callTool("hwpforge_to_json", {
          file_path: SAMPLE_PATH,
          output_path: ORIGINAL_JSON_PATH,
        }),
      ),
    );
    report.export_full = toolCallResult("hwpforge_to_json", toJsonResult);

    const original = readJson(ORIGINAL_JSON_PATH);
    report.original_equations = collectEquationScripts(original);

    const edited = buildEditedDocument(original);
    writeJson(EDITED_JSON_PATH, edited);
    report.expected_equations = collectEquationScripts(edited);

    const fromJsonResult = expectToolSuccess(
      "hwpforge_from_json",
      parseToolPayload(
        await client.callTool("hwpforge_from_json", {
          structure: JSON.stringify(edited),
          output_path: OUTPUT_PATH,
        }),
      ),
    );
    report.from_json = toolCallResult("hwpforge_from_json", fromJsonResult);

    const inspectResult = expectToolSuccess(
      "hwpforge_inspect",
      parseToolPayload(
        await client.callTool("hwpforge_inspect", {
          file_path: OUTPUT_PATH,
        }),
      ),
    );
    report.inspect_generated = toolCallResult("hwpforge_inspect", inspectResult);

    const generatedJsonResult = expectToolSuccess(
      "hwpforge_to_json",
      parseToolPayload(
        await client.callTool("hwpforge_to_json", {
          file_path: OUTPUT_PATH,
          output_path: GENERATED_JSON_PATH,
        }),
      ),
    );
    report.generated_export = toolCallResult("hwpforge_to_json", generatedJsonResult);

    const generated = readJson(GENERATED_JSON_PATH);
    report.actual_equations = collectEquationScripts(generated);
    report.success = JSON.stringify(report.expected_equations) === JSON.stringify(report.actual_equations);
    report.message = report.success
      ? "HwpForge from_json 생성 경로에서 equation script가 그대로 HWPX로 생성됨"
      : "생성된 equation script가 기대값과 일치하지 않음";

    writeJson(REPORT_PATH, report);
    client.close();
  } catch (error) {
    report.success = false;
    report.message = String(error.message || error);
    writeJson(REPORT_PATH, report);
    client.close();
    throw error;
  }
}

run().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
