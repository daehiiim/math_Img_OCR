import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Region } from "../store/jobStore";
import { ResultsViewer } from "./ResultsViewer";

function makeRegion(overrides: Partial<Region> = {}): Region {
  return {
    id: "q1",
    polygon: [
      [0, 0],
      [10, 0],
      [10, 10],
      [0, 10],
    ],
    type: "diagram",
    order: 1,
    status: "completed",
    ocrText: "OCR text",
    ...overrides,
  };
}

async function openSvgTab(): Promise<void> {
  const user = userEvent.setup();
  await user.click(screen.getByRole("tab", { name: /svg 벡터/i }));
}

describe("ResultsViewer", () => {
  it("완료된 영역에는 OCR 결과, SVG 벡터, 해설 탭만 노출한다", () => {
    const region = makeRegion({
      explanation: "해설 텍스트",
      mathml: "<math>x+1</math>",
    });

    render(
      <ResultsViewer
        regions={[region]}
        onSaveEditedSvg={vi.fn(async () => undefined)}
        onLoadRegionSvg={vi.fn(async () => "<svg />")}
      />
    );

    expect(screen.getByRole("tab", { name: /ocr 결과/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /svg 벡터/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /해설/i })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /mathml/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /raw/i })).not.toBeInTheDocument();
  });

  it("원본 signed SVG 미리보기 URL을 그대로 유지한다", async () => {
    const region = makeRegion({
      svgUrl: "https://signed.example/q1.svg?token=abc",
    });

    render(
      <ResultsViewer
        regions={[region]}
        onSaveEditedSvg={vi.fn(async () => undefined)}
        onLoadRegionSvg={vi.fn(async () => "<svg />")}
      />
    );

    await openSvgTab();

    expect(screen.getByAltText("q1 svg")).toHaveAttribute(
      "src",
      "https://signed.example/q1.svg?token=abc"
    );
  });

  it("수정본 signed SVG 미리보기 URL에는 version 파라미터를 안전하게 붙인다", async () => {
    const region = makeRegion({
      svgUrl: "https://signed.example/q1.svg?token=orig",
      editedSvgUrl: "https://signed.example/q1.edited.svg?token=edit",
      editedSvgVersion: 3,
    });

    render(
      <ResultsViewer
        regions={[region]}
        onSaveEditedSvg={vi.fn(async () => undefined)}
        onLoadRegionSvg={vi.fn(async () => "<svg />")}
      />
    );

    await openSvgTab();

    expect(screen.getByAltText("q1 svg")).toHaveAttribute(
      "src",
      "https://signed.example/q1.edited.svg?token=edit&v=3"
    );
  });
});
