import { render, screen, within } from "@testing-library/react";
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

  it("OCR 결과 탭에서 math 마크업을 숨기고 수식을 강조 텍스트로 보여준다", () => {
    const region = makeRegion({
      ocrText: "정답은 <math>x+1</math> 입니다",
    });

    render(
      <ResultsViewer
        regions={[region]}
        onSaveEditedSvg={vi.fn(async () => undefined)}
        onLoadRegionSvg={vi.fn(async () => "<svg />")}
      />
    );

    const panel = screen.getByRole("tabpanel", { name: /ocr 결과/i });

    expect(within(panel).getByText(/정답은/)).toBeInTheDocument();
    expect(within(panel).getByText("x+1")).toBeInTheDocument();
    expect(within(panel).queryByText(/<math>/i)).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button")).not.toBeInTheDocument();
  });

  it("해설 탭에서도 math 마크업을 숨기고 복사 버튼을 노출하지 않는다", async () => {
    const user = userEvent.setup();
    const region = makeRegion({
      explanation: "해설은 <math>AB</math> 입니다",
    });

    render(
      <ResultsViewer
        regions={[region]}
        onSaveEditedSvg={vi.fn(async () => undefined)}
        onLoadRegionSvg={vi.fn(async () => "<svg />")}
      />
    );

    await user.click(screen.getByRole("tab", { name: /해설/i }));

    const panel = screen.getByRole("tabpanel", { name: /해설/i });

    expect(within(panel).getByText(/해설은/)).toBeInTheDocument();
    expect(within(panel).getByText("AB")).toBeInTheDocument();
    expect(within(panel).queryByText(/<math>/i)).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button")).not.toBeInTheDocument();
  });
});
