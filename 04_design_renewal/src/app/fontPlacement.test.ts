import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** 프로젝트 루트 기준으로 지정한 파일을 UTF-8 문자열로 읽는다. */
function readProjectFile(...segments: string[]): string {
  return readFileSync(resolve(process.cwd(), ...segments), "utf8");
}

describe("Pretendard font placement", () => {
  it("self-host Pretendard 폰트 파일과 font-face 선언을 함께 유지한다", () => {
    const fontsCss = readProjectFile("src", "styles", "fonts.css");

    expect(existsSync(resolve(process.cwd(), "public", "fonts", "Pretendard-Regular.woff2"))).toBe(true);
    expect(existsSync(resolve(process.cwd(), "public", "fonts", "Pretendard-Medium.woff2"))).toBe(true);
    expect(existsSync(resolve(process.cwd(), "public", "fonts", "Pretendard-SemiBold.woff2"))).toBe(true);
    expect(existsSync(resolve(process.cwd(), "public", "fonts", "Pretendard-Bold.woff2"))).toBe(true);
    expect(fontsCss).toContain('font-family: "Pretendard"');
    expect(fontsCss).toContain('url("/fonts/Pretendard-Regular.woff2")');
    expect(fontsCss).toContain('url("/fonts/Pretendard-Bold.woff2")');
  });

  it("전역 font stack은 Pretendard를 최우선으로 사용한다", () => {
    const themeCss = readProjectFile("src", "styles", "theme.css");

    expect(themeCss).toContain('--font-ui-sans-stack: "Pretendard"');
    expect(themeCss).toContain('--font-landing-heading-stack: "Pretendard"');
    expect(themeCss).toContain("font-family: var(--font-ui-sans-stack);");
  });
});
