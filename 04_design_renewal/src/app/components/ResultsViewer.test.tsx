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
  await user.click(screen.getByRole("tab", { name: /이미지 미리보기/i }));
}

describe("ResultsViewer", () => {
  it("완료된 영역에는 OCR 결과, 이미지 미리보기, 해설 탭만 노출한다", () => {
    const region = makeRegion({
      explanation: "해설 텍스트",
      mathml: "<math>x+1</math>",
    });

    render(<ResultsViewer regions={[region]} />);

    expect(screen.getByRole("tab", { name: /ocr 결과/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /이미지 미리보기/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /해설/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /svg 도형 편집/i })).not.toBeInTheDocument();
  });

  it("생성된 이미지가 있으면 미리보기 탭에서 노출한다", async () => {
    const region = makeRegion({
      cropUrl: "https://signed.example/q1.crop.png?token=crop",
      imageCropUrl: "https://signed.example/q1.image_crop.png?token=orig",
      styledImageUrl: "https://signed.example/q1.styled.png?token=styled",
      styledImageModel: "gemini-3-pro-image-preview",
    });

    render(<ResultsViewer regions={[region]} />);

    await openSvgTab();

    expect(screen.getByAltText("q1 문제 영역 크롭")).toHaveAttribute(
      "src",
      "https://signed.example/q1.crop.png?token=crop"
    );
    expect(screen.getByAltText("q1 이미지 추출 원본")).toHaveAttribute(
      "src",
      "https://signed.example/q1.image_crop.png?token=orig"
    );
    expect(screen.getByAltText("q1 이미지 생성 결과")).toHaveAttribute(
      "src",
      "https://signed.example/q1.styled.png?token=styled"
    );
    expect(screen.queryByText("gemini-3-pro-image-preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Nano Banana 결과")).not.toBeInTheDocument();
  });

  it("문제 영역 크롭, 이미지 추출 원본, 이미지 생성 결과를 함께 보여준다", async () => {
    const region = makeRegion({
      cropUrl: "https://signed.example/q1.crop.png?token=crop",
      imageCropUrl: "https://signed.example/q1.image_crop.png?token=orig",
      styledImageUrl: "https://signed.example/q1.styled.png?token=styled",
    });

    render(<ResultsViewer regions={[region]} />);

    await openSvgTab();

    expect(screen.getByAltText("q1 문제 영역 크롭")).toHaveAttribute(
      "src",
      "https://signed.example/q1.crop.png?token=crop"
    );
    expect(screen.getByAltText("q1 이미지 추출 원본")).toHaveAttribute(
      "src",
      "https://signed.example/q1.image_crop.png?token=orig"
    );
    expect(screen.getByAltText("q1 이미지 생성 결과")).toHaveAttribute(
      "src",
      "https://signed.example/q1.styled.png?token=styled"
    );
  });

  it("OCR 결과 탭에서 math 마크업을 숨기고 수식을 강조 텍스트로 보여준다", () => {
    const region = makeRegion({
      ocrText: "정답은 <math>x+1</math> 입니다",
    });

    render(<ResultsViewer regions={[region]} />);

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

    render(<ResultsViewer regions={[region]} />);

    await user.click(screen.getByRole("tab", { name: /해설/i }));

    const panel = screen.getByRole("tabpanel", { name: /해설/i });

    expect(within(panel).getByText(/해설은/)).toBeInTheDocument();
    expect(within(panel).getByText("AB")).toBeInTheDocument();
    expect(within(panel).queryByText(/<math>/i)).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button")).not.toBeInTheDocument();
  });

  it("실패 상태여도 텍스트가 남아 있으면 결과 탭을 유지한다", () => {
    const region = makeRegion({
      status: "failed",
      ocrText: "남은 문제",
      explanation: "남은 해설",
      errorReason: "image failed",
    });

    render(<ResultsViewer regions={[region]} />);

    expect(screen.getByText(/영역 처리 경고: image failed/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /ocr 결과/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /해설/i })).toBeInTheDocument();
  });
});
