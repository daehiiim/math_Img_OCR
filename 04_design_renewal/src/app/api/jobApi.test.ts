import { beforeEach, describe, expect, it, vi } from "vitest";

const { getSessionMock } = vi.hoisted(() => ({
  getSessionMock: vi.fn(async () => ({
    data: {
      session: {
        access_token: "token-123",
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

import { getJobApi } from "./jobApi";

describe("jobApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getSessionMock.mockClear();
  });

  it("attaches the Supabase session token to backend requests", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          job_id: "job-1",
          status: "completed",
          file_name: "sample.png",
          image_url: "https://signed.example/source.png",
          image_width: 10,
          image_height: 10,
          regions: [],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await getJobApi("job-1");

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = requestInit.headers as Headers;

    expect(getSessionMock).toHaveBeenCalledTimes(1);
    expect(headers.get("Authorization")).toBe("Bearer token-123");
  });

  it("blocks non-local deployments when the API base URL is missing", async () => {
    (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__ = "";
    (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__ = false;

    await expect(getJobApi("job-1")).rejects.toThrow(
      "API base URL is not configured. Set VITE_API_BASE_URL for deployed environments."
    );

    delete (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__;
    delete (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__;
  });
});
