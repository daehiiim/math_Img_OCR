import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildPublicAppUrl, getPublicAppUrl } from "./publicAppUrl";

describe("publicAppUrl", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.stubGlobal("location", new URL("http://localhost:5173/login") as unknown as Location);
    delete (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__;
    delete (globalThis as { __MATH_OCR_SITE_URL__?: string }).__MATH_OCR_SITE_URL__;
  });

  it("SITE_URL 런타임 override를 우선 사용하고 마지막 슬래시를 제거한다", () => {
    (globalThis as { __MATH_OCR_SITE_URL__?: string }).__MATH_OCR_SITE_URL__ =
      "https://mathtohwp.vercel.app/";

    expect(getPublicAppUrl()).toBe("https://mathtohwp.vercel.app");
    expect(buildPublicAppUrl("/login")).toBe("https://mathtohwp.vercel.app/login");
  });

  it("SITE_URL 이 없으면 기존 APP_URL override를 계속 사용한다", () => {
    (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__ =
      "https://legacy-app-url.vercel.app/";

    expect(getPublicAppUrl()).toBe("https://legacy-app-url.vercel.app");
  });

  it("배포 origin에서는 설정값 없이도 현재 origin을 사용한다", () => {
    vi.stubGlobal("location", new URL("https://mathtohwp.vercel.app/pricing") as unknown as Location);

    expect(buildPublicAppUrl("/payment/starter")).toBe(
      "https://mathtohwp.vercel.app/payment/starter"
    );
  });

  it("localhost origin만 있으면 APP_URL 설정 누락 오류를 발생시킨다", () => {
    expect(() => buildPublicAppUrl("/login")).toThrow("APP_URL is not configured");
  });

  it("mock 모드에서는 localhost origin을 공개 앱 URL로 사용한다", () => {
    vi.stubEnv("VITE_LOCAL_UI_MOCK", "true");

    expect(buildPublicAppUrl("/payment/starter")).toBe("http://localhost:5173/payment/starter");
  });
});
