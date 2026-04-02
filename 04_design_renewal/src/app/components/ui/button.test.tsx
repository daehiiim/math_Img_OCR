import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("glass variant와 pill size에 대한 계약을 유지한다", () => {
    render(
      <Button variant="glass" size="pill">
        실행
      </Button>
    );

    const button = screen.getByRole("button", { name: "실행" });

    expect(button).toHaveAttribute("data-slot", "button");
    expect(button).toHaveAttribute("data-variant", "glass");
    expect(button).toHaveAttribute("data-size", "pill");
    expect(button.className).toContain("rounded-full");
    expect(button.className).toContain("backdrop-blur");
  });

  it("asChild를 사용해도 glass 계약이 자식 요소에 유지된다", () => {
    render(
      <Button asChild variant="glass" size="pill">
        <a href="/workspace">작업실 이동</a>
      </Button>
    );

    const link = screen.getByRole("link", { name: "작업실 이동" });

    expect(link).toHaveAttribute("data-slot", "button");
    expect(link).toHaveAttribute("data-variant", "glass");
    expect(link).toHaveAttribute("data-size", "pill");
  });
});
