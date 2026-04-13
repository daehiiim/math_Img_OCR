import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const logoutMock = vi.fn(async () => undefined);
const connectOpenAiMock = vi.fn(async () => undefined);
const disconnectOpenAiMock = vi.fn(async () => undefined);

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: {
      name: "김수학",
      email: "math@example.com",
      avatarInitials: "김",
      credits: 12,
      openAiConnected: true,
      openAiMaskedKey: "sk-us••••7890",
      usedCredits: 3,
      chargedJobIds: [],
    },
    isAuthenticated: true,
    isLoading: false,
    prepareLogin: vi.fn(),
    logout: logoutMock,
    connectOpenAi: connectOpenAiMock,
    disconnectOpenAi: disconnectOpenAiMock,
  }),
}));

vi.mock("../context/AdminContext", () => ({
  useAdmin: () => ({
    enterAdminMode: vi.fn(async () => ({
      sessionToken: "admin-token",
      expiresAt: "2099-04-13T01:00:00+00:00",
    })),
  }),
}));

import { Layout } from "./Layout";

describe("Layout", () => {
  beforeEach(() => {
    logoutMock.mockClear();
    connectOpenAiMock.mockClear();
    disconnectOpenAiMock.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("opens and closes the account sheet from the sidebar", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/workspace"]}>
        <Routes>
          <Route path="/workspace" element={<Layout />}>
            <Route index element={<div>workspace</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: "내 계정" }));

    expect(screen.getByRole("heading", { name: "계정 요약" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "연결 상태" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "계정 작업" })).toBeInTheDocument();
    expect(screen.getByText("김수학")).toBeInTheDocument();
    expect(screen.getByText("math@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "로그아웃" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "연결 해제" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /close/i }));

    await waitFor(() => {
      expect(screen.queryByText("math@example.com")).not.toBeInTheDocument();
    });
  });

  it("모바일 메뉴에서 탐색과 계정 시트를 연다", async () => {
    const user = userEvent.setup();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <MemoryRouter initialEntries={["/workspace"]}>
        <Routes>
          <Route path="/workspace" element={<Layout />}>
            <Route index element={<div>workspace</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: "워크스페이스 메뉴 열기" }));

    expect(screen.getByRole("dialog", { name: "워크스페이스 메뉴" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "대시보드" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "새 작업" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "내 계정" }));

    expect(screen.getByRole("heading", { name: "계정 요약" })).toBeInTheDocument();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it("워크스페이스에 비홈 리퀴드 셸 스코프를 적용한다", () => {
    render(
      <MemoryRouter initialEntries={["/workspace"]}>
        <Routes>
          <Route path="/workspace" element={<Layout />}>
            <Route index element={<div>workspace</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("workspace").closest(".liquid-shell")).toHaveClass(
      "liquid-shell",
      "liquid-shell--workspace"
    );
    expect(screen.getByRole("button", { name: "워크스페이스 메뉴 열기" })).toBeInTheDocument();
    expect(screen.getByText("workspace").closest(".liquid-page-shell")).toBeInTheDocument();
  });
});
