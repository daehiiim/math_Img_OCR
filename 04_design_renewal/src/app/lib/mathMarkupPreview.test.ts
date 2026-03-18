import { describe, expect, it } from "vitest";

import { parseMathMarkupPreview } from "./mathMarkupPreview";

describe("parseMathMarkupPreview", () => {
  it("일반 텍스트와 수식 마크업을 줄 단위 세그먼트로 분리한다", () => {
    expect(parseMathMarkupPreview("정답은 <math>x+1</math> 입니다")).toEqual([
      [
        { kind: "text", value: "정답은 " },
        { kind: "formula", value: "x+1" },
        { kind: "text", value: " 입니다" },
      ],
    ]);
  });

  it("빈 수식 마크업은 화면에 노출하지 않는다", () => {
    expect(parseMathMarkupPreview("정답은 <math></math> 입니다")).toEqual([
      [{ kind: "text", value: "정답은  입니다" }],
    ]);
  });

  it("닫히지 않은 태그는 raw 마크업을 숨기고 일반 텍스트로 폴백한다", () => {
    expect(parseMathMarkupPreview("정답은 <math>x+1 입니다")).toEqual([
      [{ kind: "text", value: "정답은 x+1 입니다" }],
    ]);
  });

  it("여러 줄과 복수 수식을 순서대로 유지한다", () => {
    expect(parseMathMarkupPreview("첫 줄 <math>a</math>\n둘째 줄 <math>b</math> 끝")).toEqual([
      [
        { kind: "text", value: "첫 줄 " },
        { kind: "formula", value: "a" },
      ],
      [
        { kind: "text", value: "둘째 줄 " },
        { kind: "formula", value: "b" },
        { kind: "text", value: " 끝" },
      ],
    ]);
  });
});
