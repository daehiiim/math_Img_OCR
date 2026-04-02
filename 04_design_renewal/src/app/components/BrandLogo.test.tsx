import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BrandLogo } from "./BrandLogo";

describe("BrandLogo", () => {
  it("공통 브랜드 로고 이미지를 렌더링한다", () => {
    render(<BrandLogo className="h-10 w-10 rounded-2xl" />);

    expect(screen.getByAltText("MathHWP 로고")).toHaveAttribute("src", "/logo.png");
  });
});
