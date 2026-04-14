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

  it("포인터 드래그로 만든 영역을 항상 mixed payload로 저장한다", async () => {
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

    expect(screen.queryByRole("button", { name: /^텍스트$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^도형$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^혼합$/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/마우스·손가락·펜 드래그 지원/i)).not.toBeInTheDocument();

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

    fireEvent.pointerDown(canvas, { clientX: 20, clientY: 20, pointerId: 1, pointerType: "touch" });
    fireEvent.pointerMove(canvas, { clientX: 160, clientY: 120, pointerId: 1, pointerType: "touch" });
    fireEvent.pointerUp(canvas, { clientX: 160, clientY: 120, pointerId: 1, pointerType: "touch" });

    await user.click(screen.getByRole("button", { name: /영역 저장 \(1개\)/i }));

    expect(onSaveRegions).toHaveBeenCalledWith([
      expect.objectContaining({
        id: "q1",
        type: "mixed",
        order: 1,
        inputDevice: "touch",
        selectionMode: "manual",
      }),
    ]);
  });

  it("데스크톱 삭제 버튼 클릭은 기존 영역만 제거한다", async () => {
    const user = userEvent.setup();

    render(
      <RegionEditor
        imageUrl="https://signed.example/source.png"
        imageWidth={400}
        imageHeight={300}
        regions={[
          {
            id: "q1",
            polygon: [
              [40, 40],
              [160, 40],
              [160, 160],
              [40, 160],
            ],
            type: "mixed",
            order: 1,
            selectionMode: "manual",
            inputDevice: "mouse",
            warningLevel: "normal",
          },
        ]}
        onSaveRegions={vi.fn(async () => undefined)}
      />
    );

    await user.click(screen.getByRole("button", { name: /q1 영역 삭제/i }));

    expect(screen.queryByRole("button", { name: /q1 영역 삭제/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /q2 영역 삭제/i })).not.toBeInTheDocument();
  });

  it("삭제 버튼 pointerdown은 데스크톱 드래그 영역 생성을 시작하지 않는다", () => {
    render(
      <RegionEditor
        imageUrl="https://signed.example/source.png"
        imageWidth={400}
        imageHeight={300}
        regions={[
          {
            id: "q1",
            polygon: [
              [40, 40],
              [160, 40],
              [160, 160],
              [40, 160],
            ],
            type: "mixed",
            order: 1,
            selectionMode: "manual",
            inputDevice: "mouse",
            warningLevel: "normal",
          },
        ]}
        onSaveRegions={vi.fn(async () => undefined)}
      />
    );

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

    const deleteButton = screen.getByRole("button", { name: /q1 영역 삭제/i });

    fireEvent.pointerDown(deleteButton, { clientX: 150, clientY: 60, pointerId: 1, pointerType: "mouse", button: 0 });
    fireEvent.pointerMove(canvas, { clientX: 230, clientY: 150, pointerId: 1, pointerType: "mouse", buttons: 1 });
    fireEvent.pointerUp(canvas, { clientX: 230, clientY: 150, pointerId: 1, pointerType: "mouse", button: 0 });

    expect(screen.queryByRole("button", { name: /q2 영역 삭제/i })).not.toBeInTheDocument();
  });
});
