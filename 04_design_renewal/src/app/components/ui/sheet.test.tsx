import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "./sheet";

describe("Sheet", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("열린 시트를 렌더링해도 ref 관련 콘솔 에러를 남기지 않는다", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <Sheet open onOpenChange={() => undefined}>
        <SheetContent aria-describedby={undefined}>
          <SheetHeader>
            <SheetTitle>모바일 메뉴</SheetTitle>
          </SheetHeader>
        </SheetContent>
      </Sheet>
    );

    expect(screen.getByRole("dialog", { name: "모바일 메뉴" })).toBeInTheDocument();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it("트리거와 닫기 버튼을 거쳐도 ref 관련 콘솔 에러를 남기지 않는다", async () => {
    const user = userEvent.setup();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <Sheet>
        <SheetTrigger>열기</SheetTrigger>
        <SheetContent aria-describedby={undefined}>
          <SheetHeader>
            <SheetTitle>모바일 메뉴</SheetTitle>
          </SheetHeader>
          <SheetClose>닫기</SheetClose>
        </SheetContent>
      </Sheet>
    );

    await user.click(screen.getByRole("button", { name: "열기" }));
    expect(screen.getByRole("dialog", { name: "모바일 메뉴" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "닫기" }));
    expect(screen.queryByRole("dialog", { name: "모바일 메뉴" })).not.toBeInTheDocument();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });
});
