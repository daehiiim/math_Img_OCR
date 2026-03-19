import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    prepareLogin: vi.fn(),
    user: {
      credits: 3,
      openAiConnected: true,
    },
  }),
}));

vi.mock("../context/JobContext", () => ({
  useJobs: () => ({
    createJob: vi.fn(async () => "job-1"),
  }),
}));

import { NewJobPage } from "./NewJobPage";

describe("NewJobPage", () => {
  it("데모 이미지 영역 없이 업로드 진입점만 노출한다", () => {
    render(
      <MemoryRouter>
        <NewJobPage />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "새 작업 생성" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "파일 선택" })).toBeInTheDocument();
    expect(screen.queryByText(/데모 이미지/)).not.toBeInTheDocument();
  });
});
