import { browserSupabase } from "../lib/supabase";
import { getApiBaseUrl } from "./apiBase";

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
  polygon?: number[][];
  ocr_text?: string | null;
  explanation?: string | null;
  mathml?: string | null;
  svg_url?: string | null;
  crop_url?: string | null;
  processing_ms?: number | null;
  success?: boolean | null;
  error_reason?: string | null;
  edited_svg_url?: string | null;
  edited_svg_version?: number | null;
}

export interface BackendJob {
  job_id: string;
  status: BackendJobStatus;
  file_name?: string | null;
  image_url?: string | null;
  image_width?: number | null;
  image_height?: number | null;
  regions: BackendRegion[];
}

export interface RegionPayload {
  id: string;
  polygon: number[][];
  type: "text" | "diagram" | "mixed";
  order: number;
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
  const base = getApiBaseUrl();
  let response: Response;
  const headers = await buildRequestHeaders(init?.headers);

  try {
    response = await fetch(`${base}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new Error(`API 연결 실패 (${base}${path}): ${reason}`);
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

export async function runPipelineApi(jobId: string): Promise<{ job_id: string; status: string }> {
  return requestJson<{ job_id: string; status: string }>(`/jobs/${jobId}/run`, {
    method: "POST",
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

export async function saveEditedSvgApi(jobId: string, regionId: string, svg: string) {
  return requestJson<{ region_id: string; edited_svg_url: string; edited_svg_version: number }>(
    `/jobs/${jobId}/regions/${regionId}/svg/edited`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ svg }),
    }
  );
}

export async function getRegionSvgApi(jobId: string, regionId: string) {
  return requestJson<{ region_id: string; svg: string; source: string }>(
    `/jobs/${jobId}/regions/${regionId}/svg`,
    { method: "GET" }
  );
}

export async function downloadHwpxApi(jobId: string): Promise<{ blob: Blob; filename: string }> {
  const base = getApiBaseUrl();
  const headers = await buildRequestHeaders();
  const response = await fetch(`${base}/jobs/${jobId}/export/hwpx/download`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  const contentDisposition = response.headers.get("content-disposition") || "";
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(contentDisposition);
  const rawName = match?.[1] || match?.[2] || `${jobId}.hwpx`;
  return {
    blob: await response.blob(),
    filename: decodeURIComponent(rawName).trim() || `${jobId}.hwpx`,
  };
}
