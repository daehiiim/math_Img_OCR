import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RegionEditor } from "./RegionEditor";

describe("RegionEditor", () => {
  it("초기 렌더에서는 부모 영역 변경 콜백을 호출하지 않는다", () => {
    const onRegionsChange = vi.fn();

    render(
      <RegionEditor
        imageUrl="https://signed.example/source.png"
        imageWidth={400}
        imageHeight={300}
        regions={[]}
        onSaveRegions={vi.fn(async () => undefined)}
        onRegionsChange={onRegionsChange}
      />
    );

    expect(onRegionsChange).not.toHaveBeenCalled();
  });

  it("영역 타입 선택 없이 저장 payload를 항상 mixed로 보낸다", async () => {
    const user = userEvent.setup();
    const onSaveRegions = vi.fn(async () => undefined);

    render(
      <RegionEditor
        imageUrl="https://signed.example/source.png"
        imageWidth={400}
        imageHeight={300}
        regions={[]}
        onSaveRegions={onSaveRegions}
      />
    );

    expect(screen.getByRole("button", { name: /영역 그리기/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^텍스트$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^도형$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^혼합$/i })).not.toBeInTheDocument();

    const canvas = screen.getByAltText("uploaded").parentElement as HTMLDivElement;
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      width: 400,
      height: 300,
      top: 0,
      left: 0,
      right: 400,
      bottom: 300,
      toJSON: () => ({}),
    });

    fireEvent.mouseDown(canvas, { clientX: 20, clientY: 20 });
    fireEvent.mouseMove(canvas, { clientX: 160, clientY: 120 });
    fireEvent.mouseUp(canvas);

    await user.click(screen.getByRole("button", { name: /영역 저장 \(1개\)/i }));

    expect(onSaveRegions).toHaveBeenCalledWith([
      expect.objectContaining({
        id: "q1",
        type: "mixed",
        order: 1,
      }),
    ]);
  });
});
