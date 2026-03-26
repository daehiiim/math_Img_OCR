import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const logoutMock = vi.fn(async () => undefined);

let mockAuthState = {
  user: {
    name: "김수학",
    email: "math@example.com",
    avatarInitials: "김",
    credits: 4,
    openAiConnected: true,
  },
  isAuthenticated: true,
  logout: logoutMock,
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuthState,
}));

import { AuthLayout } from "./AuthLayout";

describe("AuthLayout", () => {
  beforeEach(() => {
    logoutMock.mockClear();
    mockAuthState = {
      user: {
        name: "김수학",
        email: "math@example.com",
        avatarInitials: "김",
        credits: 4,
        openAiConnected: true,
      },
      isAuthenticated: true,
      logout: logoutMock,
    };
  });

  it("인증 헤더에 남은 이미지와 OpenAI 연결 상태를 함께 표시한다", () => {
    render(
      <MemoryRouter initialEntries={["/workspace"]}>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/workspace" element={<div>workspace</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("4개 이미지 남음")).toBeInTheDocument();
    expect(screen.getByText("OpenAI 연결됨")).toBeInTheDocument();
  });

  it("홈과 분리된 비홈 리퀴드 셸 스코프를 적용한다", () => {
    render(
      <MemoryRouter initialEntries={["/workspace"]}>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/workspace" element={<div>workspace</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("workspace").closest(".liquid-shell")).toHaveClass(
      "liquid-shell",
      "liquid-shell--auth"
    );
  });
});
