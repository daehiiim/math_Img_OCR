import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** 배포 원본 HTML을 읽어 AdSense 검증 코드 위치를 확인한다. */
function readIndexHtml(): string {
  return readFileSync(resolve(process.cwd(), "index.html"), "utf8");
}

/** 앱 루트 소스를 읽어 런타임 주입 흔적이 남지 않았는지 확인한다. */
function readAppSource(): string {
  return readFileSync(resolve(process.cwd(), "src/app/App.tsx"), "utf8");
}

describe("AdSense placement", () => {
  it("AdSense 로더는 배포 HTML head 에 직접 포함되어야 한다", () => {
    const indexHtml = readIndexHtml();

    expect(indexHtml).toMatch(
      /<script\s+async\s+src="https:\/\/pagead2\.googlesyndication\.com\/pagead\/js\/adsbygoogle\.js\?client=ca-pub-4088422118336195"/
    );
    expect(indexHtml).toContain('crossorigin="anonymous"');
  });

  it("앱 라우트는 AdSense 로더를 런타임에 다시 주입하지 않는다", () => {
    const appSource = readAppSource();

    expect(appSource).not.toContain("AdSenseTracker");
  });
});
