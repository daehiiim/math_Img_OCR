import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockNavigate = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
  }),
}));

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");

  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { PublicHomePage } from "./PublicHomePage";

describe("PublicHomePage", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it("새 세리프 랜딩 카피와 정보 밴드를 노출한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.getByText("MATH OCR")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "문제 사진이 곧, 한글 문서가 됩니다." })).toBeInTheDocument();
    expect(screen.getByText("로그인 없이 첫 작업을 시작하고,")).toBeInTheDocument();
    expect(screen.getByText("사진에서 HWPX까지 한 흐름으로 이어갑니다.")).toBeInTheDocument();
    expect(screen.getByText("사용 방식")).toBeInTheDocument();
    expect(screen.getByText("OCR·해설은 본인 OpenAI API key로 처리")).toBeInTheDocument();
    expect(screen.getByText("이미지 생성은 충전한 크레딧으로 진행")).toBeInTheDocument();
    expect(screen.getByText("사진을 올리면 정리됩니다.")).toBeInTheDocument();
    expect(screen.getByText("결과를 보고 다듬습니다.")).toBeInTheDocument();
    expect(screen.getByText("끝은 한글 문서입니다.")).toBeInTheDocument();
    expect(screen.queryByText(/어떤 문제 사진이라도 한글 파일로/)).not.toBeInTheDocument();
  });

  it("헤더와 주요 CTA를 노출한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.queryByRole("button", { name: "가격" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "새 작업 시작" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "가격 보기" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "로그인" })).toBeInTheDocument();
  });

  it("메인 카피와 섹션 타이틀은 산세리프 랜딩 타이포를 사용한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    const heroHeading = screen.getByRole("heading", { name: "문제 사진이 곧, 한글 문서가 됩니다." });
    const sectionHeading = screen.getByRole("heading", { name: "길게 설명하지 않아도 흐름은 분명합니다." });

    expect(heroHeading).toHaveClass("landing-heading");
    expect(heroHeading).not.toHaveClass("landing-serif");
    expect(sectionHeading).toHaveClass("landing-heading");
  });

  it("공개 홈 CTA가 기존 목적지로 이동한다", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: "로그인" }));
    await user.click(screen.getByRole("button", { name: "새 작업 시작" }));
    await user.click(screen.getByRole("button", { name: "가격 보기" }));

    expect(mockNavigate).toHaveBeenCalledWith("/login");
    expect(mockNavigate).toHaveBeenCalledWith("/new");
    expect(mockNavigate).toHaveBeenCalledWith("/pricing");
  });
});
