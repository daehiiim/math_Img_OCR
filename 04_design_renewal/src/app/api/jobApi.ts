import { browserSupabase } from "../lib/supabase";
import { buildApiUrl, getApiBaseUrl } from "./apiBase";

export type BackendRegionStatus = "pending" | "running" | "completed" | "failed";
export type BackendJobStatus =
  | "created"
  | "regions_pending"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "exported";

export interface BackendRegion {
  id: string;
  status: BackendRegionStatus;
  type?: "text" | "diagram" | "mixed";
  order?: number;
  selection_mode?: "manual" | "auto_full";
  input_device?: "mouse" | "touch" | "pen" | "system" | null;
  warning_level?: "normal" | "high_risk";
  polygon?: number[][];
  ocr_text?: string | null;
  explanation?: string | null;
  mathml?: string | null;
  problem_markdown?: string | null;
  explanation_markdown?: string | null;
  markdown_version?: string | null;
  verification_status?: "verified" | "warning" | "unverified" | null;
  verification_warnings?: string[] | null;
  svg_url?: string | null;
  crop_url?: string | null;
  image_crop_url?: string | null;
  styled_image_url?: string | null;
  styled_image_model?: string | null;
  processing_ms?: number | null;
  success?: boolean | null;
  error_reason?: string | null;
  was_charged?: boolean | null;
  ocr_charged?: boolean | null;
  image_charged?: boolean | null;
  explanation_charged?: boolean | null;
  charged_at?: string | null;
}

export interface BackendJob {
  job_id: string;
  status: BackendJobStatus;
  file_name?: string | null;
  image_url?: string | null;
  image_width?: number | null;
  image_height?: number | null;
  last_error?: string | null;
  hwpx_export_path?: string | null;
  regions: BackendRegion[];
}

export interface RegionPayload {
  id: string;
  polygon: number[][];
  type: "text" | "diagram" | "mixed";
  order: number;
  selection_mode?: "manual" | "auto_full";
  input_device?: "mouse" | "touch" | "pen" | "system";
  warning_level?: "normal" | "high_risk";
}

export interface RunPipelineOptions {
  doOcr: boolean;
  doImageStylize: boolean;
  doExplanation: boolean;
}

export interface RunPipelineResult {
  job_id: string;
  status: "completed" | "failed";
  executed_actions?: Array<"ocr" | "image_stylize" | "explanation">;
  charged_count: number;
  completed_count: number;
  failed_count: number;
  exportable_count: number;
}

async function buildRequestHeaders(initHeaders?: HeadersInit): Promise<Headers> {
  const headers = new Headers(initHeaders);
  const session = browserSupabase ? await browserSupabase.auth.getSession() : null;
  const accessToken = session?.data.session?.access_token;

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = buildApiUrl(path);
  let response: Response;
  const headers = await buildRequestHeaders(init?.headers);

  try {
    response = await fetch(url, {
      ...init,
      headers,
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new Error(`API 연결 실패 (${url}): ${reason}`);
  }

  if (!response.ok) {
    const text = await response.text();
    let message = text || `HTTP ${response.status}`;

    try {
      const parsed = JSON.parse(text) as { detail?: string };
      if (typeof parsed.detail === "string") {
        message = `[${response.status}] ${parsed.detail}`;
      }
    } catch {
      // JSON이 아닌 에러 응답은 그대로 둔다.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function resolveRuntimePath(pathValue: string | null | undefined): string | undefined {
  if (!pathValue) {
    return undefined;
  }

  if (/^https?:\/\//.test(pathValue) || pathValue.startsWith("data:")) {
    return pathValue;
  }

  const normalized = pathValue.split("\\").join("/");
  const base = getApiBaseUrl();
  return `${base}${normalized.startsWith("/") ? normalized : `/${normalized}`}`;
}

export async function createJobApi(image: File): Promise<BackendJob> {
  const form = new FormData();
  form.append("image", image);
  return requestJson<BackendJob>("/jobs", { method: "POST", body: form });
}

export async function saveRegionsApi(jobId: string, regions: RegionPayload[]): Promise<void> {
  await requestJson<{ message: string; count: number }>(`/jobs/${jobId}/regions`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ regions }),
  });
}

export async function runPipelineApi(
  jobId: string,
  options: RunPipelineOptions
): Promise<RunPipelineResult> {
  return requestJson<RunPipelineResult>(`/jobs/${jobId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      do_ocr: options.doOcr,
      do_image_stylize: options.doImageStylize,
      do_explanation: options.doExplanation,
    }),
  });
}

export async function getJobApi(jobId: string): Promise<BackendJob> {
  return requestJson<BackendJob>(`/jobs/${jobId}`, { method: "GET" });
}

export async function exportHwpxApi(jobId: string): Promise<{ download_url: string }> {
  return requestJson<{ download_url: string }>(`/jobs/${jobId}/export/hwpx`, {
    method: "POST",
  });
}

export async function downloadHwpxApi(jobId: string): Promise<{ blob: Blob; filename: string }> {
  const url = buildApiUrl(`/jobs/${jobId}/export/hwpx/download`);
  const headers = await buildRequestHeaders();
  const response = await fetch(url, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  const defaultFilename = "생성결과.hwpx";
  const contentDisposition = response.headers.get("content-disposition") || "";
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(contentDisposition);
  const rawName = match?.[1] || match?.[2];
  const filename = rawName ? safeDecodeFilename(rawName, defaultFilename) : defaultFilename;
  return {
    blob: await response.blob(),
    filename,
  };
}

/** 다운로드 파일명을 안전하게 해석한다. */
function safeDecodeFilename(rawName: string, fallback: string): string {
  try {
    return decodeURIComponent(rawName).trim() || fallback;
  } catch {
    return rawName.trim() || fallback;
  }
}
