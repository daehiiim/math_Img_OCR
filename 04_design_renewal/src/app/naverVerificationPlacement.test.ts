import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** 배포 원본 HTML을 읽어 네이버 검증 메타 태그 위치를 확인한다. */
function readIndexHtml(): string {
  return readFileSync(resolve(process.cwd(), "index.html"), "utf8");
}

describe("Naver verification placement", () => {
  it("네이버 사이트 검증 메타 태그는 배포 HTML head 에 직접 포함되어야 한다", () => {
    const indexHtml = readIndexHtml();

    expect(indexHtml).toMatch(
      /<head>[\s\S]*<meta name="naver-site-verification" content="b688176edcf34fb4e2617c148556dc5c7a0bacb6"\s*\/>/
    );
  });
});
