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

import { createCheckoutSessionApi } from "./billingApi";

describe("billingApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getSessionMock.mockClear();
  });

  it("attaches the Supabase session token to billing requests", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          checkout_id: "chk_test_123",
          checkout_url: "https://sandbox-checkout.polar.sh/checkout/chk_test_123",
          plan_id: "starter",
          credits: 100,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await createCheckoutSessionApi({
      planId: "starter",
      successUrl: "https://example.com/success",
      cancelUrl: "https://example.com/cancel",
    });

    expect(fetchMock.mock.calls[0]?.[0]).toBe("http://localhost:8000/billing/checkout");

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = requestInit.headers as Headers;

    expect(getSessionMock).toHaveBeenCalledTimes(1);
    expect(headers.get("Authorization")).toBe("Bearer token-456");
  });

  it("includes the API URL when checkout network requests fail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    await expect(
      createCheckoutSessionApi({
        planId: "starter",
        successUrl: "https://example.com/success",
        cancelUrl: "https://example.com/cancel",
      })
    ).rejects.toThrow("API 연결 실패 (http://localhost:8000/billing/checkout): Failed to fetch");
  });

  it("blocks non-local deployments when the API base URL is missing", async () => {
    (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__ = "";
    (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__ = false;

    await expect(
      createCheckoutSessionApi({
        planId: "starter",
        successUrl: "https://example.com/success",
        cancelUrl: "https://example.com/cancel",
      })
    ).rejects.toThrow("API base URL is not configured. Set VITE_API_BASE_URL for deployed environments.");

    delete (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__;
    delete (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean }).__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__;
  });

  it("surfaces backend detail messages for failed checkout requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Polar gateway is not configured" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    await expect(
      createCheckoutSessionApi({
        planId: "starter",
        successUrl: "https://example.com/success",
        cancelUrl: "https://example.com/cancel",
      })
    ).rejects.toThrow("[400] Polar gateway is not configured");
  });
});
