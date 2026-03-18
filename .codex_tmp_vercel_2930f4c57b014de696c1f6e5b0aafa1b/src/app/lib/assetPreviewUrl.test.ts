import { describe, expect, it } from "vitest";

import { buildAssetPreviewUrl } from "./assetPreviewUrl";

describe("buildAssetPreviewUrl", () => {
  it("signed URL의 기존 쿼리를 유지하면서 version 파라미터를 추가한다", () => {
    expect(buildAssetPreviewUrl("https://signed.example/q1.svg?token=abc", 3)).toBe(
      "https://signed.example/q1.svg?token=abc&v=3"
    );
  });

  it("일반 경로에는 version 파라미터를 새로 추가한다", () => {
    expect(buildAssetPreviewUrl("/runtime/q1.svg", 3)).toBe("/runtime/q1.svg?v=3");
  });

  it("기존 version 파라미터가 있으면 중복 없이 교체한다", () => {
    expect(buildAssetPreviewUrl("https://signed.example/q1.svg?token=abc&v=1", 3)).toBe(
      "https://signed.example/q1.svg?token=abc&v=3"
    );
  });

  it("version이 없으면 원본 URL을 그대로 유지한다", () => {
    expect(buildAssetPreviewUrl("https://signed.example/q1.svg?token=abc")).toBe(
      "https://signed.example/q1.svg?token=abc"
    );
  });
});
