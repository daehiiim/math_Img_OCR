import { describe, expect, it } from "vitest";

import { validateImageFile } from "./uploadPreview";

describe("validateImageFile", () => {
  it("지원하지 않는 파일 형식은 오류를 반환한다", () => {
    const file = new File(["hello"], "sample.gif", { type: "image/gif" });

    expect(validateImageFile(file)).toBe("지원되지 않는 파일 형식입니다.");
  });

  it("10MB를 초과하면 오류를 반환한다", () => {
    const file = new File(["a".repeat(10 * 1024 * 1024 + 1)], "large.png", {
      type: "image/png",
    });

    expect(validateImageFile(file)).toBe("파일 크기가 제한을 초과했습니다.");
  });

  it("허용된 이미지 파일은 통과한다", () => {
    const file = new File(["ok"], "sample.jpg", { type: "image/jpeg" });

    expect(validateImageFile(file)).toBeNull();
  });
});
