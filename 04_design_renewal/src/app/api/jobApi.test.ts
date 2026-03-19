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

import { getJobApi, runPipelineApi } from "./jobApi";

describe("jobApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
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

  it("ignores absolute env API bases on hosted deployments and keeps same-origin job paths", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://mathocr-146126176673.us-central1.run.app");
    vi.stubGlobal(
      "location",
      new URL("https://mathtohwpx-git-codex-google-oauth-app-url-daehiiim.vercel.app/workspace") as unknown as Location
    );
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          job_id: "job-4",
          status: "completed",
          file_name: "sample.png",
          image_url: "/runtime/jobs/job-4/input/sample.png",
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

    await getJobApi("job-4");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/jobs/job-4");
  });

  it("sends selected execution options when running a job", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          job_id: "job-5",
          status: "completed",
          executed_actions: ["ocr", "image_stylize"],
          charged_count: 2,
          completed_count: 2,
          failed_count: 0,
          exportable_count: 2,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runPipelineApi("job-5", {
      doOcr: true,
      doImageStylize: true,
      doExplanation: false,
    });

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;

    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://localhost:8000/jobs/job-5/run");
    expect(requestInit.method).toBe("POST");
    expect(requestInit.body).toBe(
      JSON.stringify({
        do_ocr: true,
        do_image_stylize: true,
        do_explanation: false,
      })
    );
    expect(result.charged_count).toBe(2);
    expect(result.completed_count).toBe(2);
  });
});
