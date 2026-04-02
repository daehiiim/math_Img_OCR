import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** theme.css를 읽어 현재 비홈 테마 계약을 검증한다. */
function readThemeCss(): string {
  return readFileSync(resolve(process.cwd(), "src", "styles", "theme.css"), "utf8");
}

describe("liquid theme contract", () => {
  it("비홈 liquid-shell은 흰색과 아이스 블루 방향을 유지한다", () => {
    const themeCss = readThemeCss();

    expect(themeCss).toContain(".liquid-shell {");
    expect(themeCss).toContain(".liquid-shell--workspace {");
    expect(themeCss).toContain(".liquid-header-shell {");
    expect(themeCss).toContain(".liquid-sidebar-shell {");
    expect(themeCss).toContain(".liquid-frost-panel {");
    expect(themeCss).toContain(".liquid-inline-note {");
    expect(themeCss).toContain(".liquid-stat-orb {");
    expect(themeCss).toContain(".public-home-page {");
    expect(themeCss).toContain("#f7fbff");
    expect(themeCss).toContain("#eef4fb");
    expect(themeCss).toContain("#4da3ff");
    expect(themeCss).not.toContain("#355547");
    expect(themeCss).not.toContain("#2c4439");
    expect(themeCss).not.toContain("#436454");
  });
});
