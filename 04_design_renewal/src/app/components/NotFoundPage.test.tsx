import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const navigateMock = vi.fn();

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");

  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

import { NotFoundPage } from "./NotFoundPage";

describe("NotFoundPage", () => {
  beforeEach(() => {
    navigateMock.mockClear();
  });

  it("회복 표면과 홈 복귀 CTA를 노출한다", () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>
    );

    expect(screen.getByRole("region", { name: "회복 표면" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "홈으로 돌아가기" })).toBeInTheDocument();
    expect(screen.getByText("페이지를 찾을 수 없습니다")).toBeInTheDocument();
  });
});
