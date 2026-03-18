import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
  }),
}));

import { PublicHomePage } from "./PublicHomePage";

describe("PublicHomePage", () => {
  it("랜딩 페이지에 새 헤더와 카피를 노출한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.getByText("MATH OCR")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "가격" })).not.toBeInTheDocument();
    expect(screen.getByText("어떤 문제 사진이라도 한글 파일로")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "컴퓨터에서도, 휴대폰에서도 문제를 한글로." })).toBeInTheDocument();
    expect(screen.getByText("로그인 없이 시작하고, 문서 제작도 간단히.")).toBeInTheDocument();
    expect(screen.getByText("바로 결과를 만들어내는 워크스테이션")).toBeInTheDocument();
    expect(screen.getByText("사진을 찍으세요.")).toBeInTheDocument();
    expect(screen.getByText("검토하세요.")).toBeInTheDocument();
    expect(screen.getByText("변환하세요.")).toBeInTheDocument();
  });

  it("단계 설명의 줄바꿈 문자를 화면 줄바꿈으로 처리할 수 있는 클래스를 적용한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    const firstStepBody = screen
      .getByText(/시험지, 프린트물, 풀이를 업로드하세요\./)
      .closest("p");

    expect(firstStepBody).toHaveClass("whitespace-pre-line");
  });
});
