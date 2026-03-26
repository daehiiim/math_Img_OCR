import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/** 배포 원본 HTML을 읽어 Google 태그 위치와 스니펫 내용을 검증한다. */
function readIndexHtml(): string {
  return readFileSync(resolve(process.cwd(), "index.html"), "utf8");
}

describe("Google Analytics placement", () => {
  it("Google 태그는 배포 HTML head 바로 다음에 가이드 그대로 포함되어야 한다", () => {
    const indexHtml = readIndexHtml();

    expect(indexHtml).toMatch(
      /<head>\s*<!-- Google tag \(gtag\.js\) -->\s*<script async src="https:\/\/www\.googletagmanager\.com\/gtag\/js\?id=G-SM6ETGCFGP"><\/script>\s*<script>\s*window\.dataLayer = window\.dataLayer \|\| \[\];\s*function gtag\(\)\{dataLayer\.push\(arguments\);\}\s*gtag\('js', new Date\(\)\);\s*gtag\('config', 'G-SM6ETGCFGP'\);\s*<\/script>/s
    );
  });
});
