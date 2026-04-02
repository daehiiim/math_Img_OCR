import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const indexHtmlPath = resolve(currentDirectory, "index.html");
const indexHtmlContent = readFileSync(indexHtmlPath, "utf8");

describe("index.html", () => {
  it("브라우저 탭 아이콘과 애플 터치 아이콘을 함께 연결한다", () => {
    expect(indexHtmlContent).toContain('rel="icon"');
    expect(indexHtmlContent).toContain('href="/logo.png"');
    expect(indexHtmlContent).toContain('rel="apple-touch-icon"');
  });
});
