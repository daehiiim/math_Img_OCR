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
});
