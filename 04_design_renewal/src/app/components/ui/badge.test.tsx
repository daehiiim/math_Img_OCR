import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "./badge";

describe("Badge", () => {
  it("glass variant에 대한 계약을 유지한다", () => {
    render(<Badge variant="glass">상태</Badge>);

    const badge = screen.getByText("상태");

    expect(badge).toHaveAttribute("data-slot", "badge");
    expect(badge).toHaveAttribute("data-variant", "glass");
    expect(badge.className).toContain("backdrop-blur");
  });
});
