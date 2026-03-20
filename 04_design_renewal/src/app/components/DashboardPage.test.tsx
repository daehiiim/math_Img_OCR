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

    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.queryByText("∞")).not.toBeInTheDocument();
    expect(
      screen.getByText("OCR·해설은 연결한 OpenAI API key를 사용하고, 이미지 생성은 크레딧을 사용합니다.")
    ).toBeInTheDocument();
    expect(screen.getByText("OpenAI 연결됨")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이미지 충전" })).toBeInTheDocument();
  });
});
