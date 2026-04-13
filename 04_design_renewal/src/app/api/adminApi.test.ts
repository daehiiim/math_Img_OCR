import { beforeEach, describe, expect, it, vi } from "vitest";

const { getSessionMock } = vi.hoisted(() => ({
  getSessionMock: vi.fn(async () => ({
    data: {
      session: {
        access_token: "token-456",
      },
    },
  })),
}));

vi.mock("../lib/supabase", () => ({
  browserSupabase: {
    auth: {
      getSession: getSessionMock,
    },
  },
}));

import { createAdminSessionApi, getAdminDashboardApi } from "./adminApi";

describe("adminApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    getSessionMock.mockClear();
    delete (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__;
    delete (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__;
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("관리자 세션 발급 요청에 Supabase access token을 붙인다", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          session_token: "admin-token-123",
          expires_at: "2026-04-13T01:00:00+00:00",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await createAdminSessionApi("admin-secret");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://localhost:8000/admin/session");
    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = requestInit.headers as Headers;

    expect(getSessionMock).toHaveBeenCalledTimes(1);
    expect(headers.get("Authorization")).toBe("Bearer token-456");
  });

  it("관리자 대시보드 요청에 관리자 세션 헤더를 붙인다", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          generated_at: "2026-04-13T00:30:00+00:00",
          failed_jobs_today: 2,
          missing_openai_request_regions_today: 1,
          recent_user_runs: [],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await getAdminDashboardApi("admin-token-123");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://localhost:8000/admin/dashboard");
    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = requestInit.headers as Headers;

    expect(headers.get("Authorization")).toBe("Bearer token-456");
    expect(headers.get("X-Admin-Session")).toBe("admin-token-123");
  });
});
