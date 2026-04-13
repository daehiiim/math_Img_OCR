import { browserSupabase } from "../lib/supabase";
import { buildApiUrl } from "./apiBase";

export interface AdminSessionResponse {
  session_token: string;
  expires_at: string;
}

export interface RecentUserRunResponse {
  user_label: string;
  user_id_suffix: string;
  job_id: string;
  file_name: string;
  job_status: string;
  region_count: number;
  ran_at?: string | null;
}

export interface AdminDashboardResponse {
  generated_at: string;
  failed_jobs_today: number;
  missing_openai_request_regions_today: number;
  recent_user_runs: RecentUserRunResponse[];
}

/** Supabase 로그인 토큰과 관리자 세션 헤더를 함께 조립한다. */
async function buildRequestHeaders(initHeaders?: HeadersInit, adminSessionToken?: string): Promise<Headers> {
  const headers = new Headers(initHeaders);
  const session = browserSupabase ? await browserSupabase.auth.getSession() : null;
  const accessToken = session?.data.session?.access_token;

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  if (adminSessionToken) {
    headers.set("X-Admin-Session", adminSessionToken);
  }

  return headers;
}

/** 관리자 모드 백엔드 detail을 사용자 메시지로 정규화한다. */
function mapAdminDetailToMessage(detail: string) {
  return detail;
}

/** 관리자 모드 JSON API 요청을 공통 규칙으로 수행한다. */
async function requestJson<T>(path: string, init?: RequestInit, adminSessionToken?: string): Promise<T> {
  const url = buildApiUrl(path);
  const headers = await buildRequestHeaders(init?.headers, adminSessionToken);
  let response: Response;

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
        message = mapAdminDetailToMessage(parsed.detail);
      }
    } catch {
      // JSON이 아닌 에러 응답은 그대로 유지한다.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

/** 관리자 비밀번호를 검증해 짧은 관리자 세션을 발급받는다. */
export async function createAdminSessionApi(password: string) {
  return requestJson<AdminSessionResponse>(
    "/admin/session",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    }
  );
}

/** 관리자 세션 헤더로 운영 대시보드 집계를 조회한다. */
export async function getAdminDashboardApi(sessionToken: string) {
  return requestJson<AdminDashboardResponse>(
    "/admin/dashboard",
    { method: "GET" },
    sessionToken
  );
}
