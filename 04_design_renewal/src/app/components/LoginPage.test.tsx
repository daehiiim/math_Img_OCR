import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useAuthMock } = vi.hoisted(() => ({
  useAuthMock: vi.fn(),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
  });

  it("mock 모드에서는 로컬 테스트 로그인 문구를 노출한다", () => {
    useAuthMock.mockReturnValue({
      authErrorMessage: null,
      clearPostLoginPath: vi.fn(),
      isAuthenticated: false,
      isLoading: false,
      isLocalUiMock: true,
      loginWithGoogle: vi.fn(async () => null),
      readPostLoginPath: vi.fn(() => "/workspace"),
      user: null,
    });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByRole("button", { name: "로컬 테스트로 로그인" })).toBeInTheDocument();
    expect(screen.getByText("Google 없이 로컬 프로필로 바로 진입합니다.")).toBeInTheDocument();
  });

  it("인증 설정이 없으면 한국어 안내를 보여주고 로그인 버튼을 비활성화한다", () => {
    useAuthMock.mockReturnValue({
      authErrorMessage: "로컬 UI mock 모드를 켜거나 Supabase 인증 환경값을 설정해주세요.",
      clearPostLoginPath: vi.fn(),
      isAuthenticated: false,
      isLoading: false,
      isLocalUiMock: false,
      loginWithGoogle: vi.fn(async () => null),
      readPostLoginPath: vi.fn(() => "/workspace"),
      user: null,
    });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      screen.getByText("로컬 UI mock 모드를 켜거나 Supabase 인증 환경값을 설정해주세요.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Google 계정으로 로그인" })).toBeDisabled();
  });

  it("mock 로그인 완료 후에는 원래 요청 경로로 바로 복귀한다", async () => {
    useAuthMock.mockReturnValue({
      authErrorMessage: null,
      clearPostLoginPath: vi.fn(),
      isAuthenticated: true,
      isLoading: false,
      isLocalUiMock: true,
      loginWithGoogle: vi.fn(async () => null),
      readPostLoginPath: vi.fn(() => "/workspace"),
      user: {
        openAiConnected: false,
        credits: 0,
      },
    });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/workspace" element={<div>workspace</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("workspace")).toBeInTheDocument();
  });
});
