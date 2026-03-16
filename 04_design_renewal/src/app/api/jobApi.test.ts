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
    vi.unstubAllEnvs();
    getSessionMock.mockClear();
    delete (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__;
    delete (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__;
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
    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://localhost:8000/jobs/job-1");
    expect(headers.get("Authorization")).toBe("Bearer token-123");
  });

  it("uses same-origin job paths for production-style deployments without an API base URL", async () => {
    (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__ = "";
    (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__ = false;
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          job_id: "job-1",
          status: "completed",
          file_name: "sample.png",
          image_url: "/runtime/jobs/job-1/input/sample.png",
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

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/jobs/job-1");
  });

  it("prefers the configured API base URL when provided", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://env-api.example.com/");
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          job_id: "job-2",
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

    await getJobApi("job-2");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("https://env-api.example.com/jobs/job-2");
  });

  it("treats the same-origin API token as a relative production path", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "same-origin");
    (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__ = false;
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          job_id: "job-3",
          status: "completed",
          file_name: "sample.png",
          image_url: "/runtime/jobs/job-3/input/sample.png",
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

    await getJobApi("job-3");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/jobs/job-3");
  });
});
