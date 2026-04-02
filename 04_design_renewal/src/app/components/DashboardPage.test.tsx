import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const deleteJobMock = vi.fn();

let mockUser = {
  credits: 7,
  usedCredits: 11,
  openAiConnected: true,
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: mockUser,
  }),
}));

vi.mock("../context/JobContext", () => ({
  useJobs: () => ({
    jobs: [],
    deleteJob: deleteJobMock,
  }),
}));

import { DashboardPage } from "./DashboardPage";

describe("DashboardPage", () => {
  beforeEach(() => {
    deleteJobMock.mockClear();
    mockUser = {
      credits: 7,
      usedCredits: 11,
      openAiConnected: true,
    };
  });

  it("OpenAI 연결 계정에도 실제 남은 이미지와 충전 CTA를 표시한다", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "작업 대시보드" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "상단 요약" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "핵심 지표" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "작업 목록" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "작업 흐름" })).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.queryByText("∞")).not.toBeInTheDocument();
    expect(
      screen.getByText("OCR·해설은 연결한 OpenAI API key를 사용하고, 이미지 생성은 크레딧을 사용합니다.")
    ).toBeInTheDocument();
    expect(screen.getByText("OpenAI 연결됨")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이미지 충전" })).toBeInTheDocument();
  });

  it("작업실 대시보드에 생산성 우선 글라스 페이지 스코프를 적용한다", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByText("작업 대시보드").closest(".liquid-workspace-page")).toHaveClass("liquid-workspace-page");
    expect(screen.getByRole("button", { name: "새 작업" })).toBeInTheDocument();
  });
});
