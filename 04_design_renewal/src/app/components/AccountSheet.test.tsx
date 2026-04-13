import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const logoutMock = vi.fn(async () => undefined);
const connectOpenAiMock = vi.fn(async () => undefined);
const disconnectOpenAiMock = vi.fn(async () => undefined);
const enterAdminModeMock = vi.fn(async () => ({
  sessionToken: "admin-token-123",
  expiresAt: "2099-04-13T01:00:00+00:00",
}));
const navigateMock = vi.fn();

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
    enterAdminMode: enterAdminModeMock,
  }),
}));

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

import { AccountSheet } from "./AccountSheet";

describe("AccountSheet", () => {
  beforeEach(() => {
    logoutMock.mockClear();
    connectOpenAiMock.mockClear();
    disconnectOpenAiMock.mockClear();
    enterAdminModeMock.mockClear();
    navigateMock.mockClear();
  });

  it("계정 작업 아래 관리자 모드 입력과 진입 버튼을 렌더링한다", async () => {
    const user = userEvent.setup();
    const onOpenChangeMock = vi.fn();

    render(
      <MemoryRouter>
        <AccountSheet open onOpenChange={onOpenChangeMock} />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "관리자 모드" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("관리자 비밀번호"), "admin-secret");
    await user.click(screen.getByRole("button", { name: "관리자 보드 열기" }));

    await waitFor(() => {
      expect(enterAdminModeMock).toHaveBeenCalledWith("admin-secret");
    });
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
    expect(navigateMock).toHaveBeenCalledWith("/workspace/admin");
  });

  it("비밀번호 불일치 에러를 인라인으로 노출한다", async () => {
    const user = userEvent.setup();
    enterAdminModeMock.mockRejectedValueOnce(new Error("관리자 비밀번호가 올바르지 않습니다."));

    render(
      <MemoryRouter>
        <AccountSheet open onOpenChange={vi.fn()} />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText("관리자 비밀번호"), "wrong-secret");
    await user.click(screen.getByRole("button", { name: "관리자 보드 열기" }));

    await waitFor(() => {
      expect(screen.getByText("관리자 비밀번호가 올바르지 않습니다.")).toBeInTheDocument();
    });
  });
});
