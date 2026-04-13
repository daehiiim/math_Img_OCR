import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createAdminSessionApiMock } = vi.hoisted(() => ({
  createAdminSessionApiMock: vi.fn(),
}));

vi.mock("../api/adminApi", () => ({
  createAdminSessionApi: createAdminSessionApiMock,
}));

import { AdminProvider, useAdmin } from "./AdminContext";

function AdminHarness() {
  const { adminSession, enterAdminMode, exitAdminMode, isAdminAuthenticated } = useAdmin();

  return (
    <div>
      <button type="button" onClick={() => void enterAdminMode("admin-secret")}>
        관리자 진입
      </button>
      <button type="button" onClick={() => exitAdminMode()}>
        관리자 종료
      </button>
      <span data-testid="admin-state">{isAdminAuthenticated ? "authenticated" : "guest"}</span>
      <span data-testid="admin-token">{adminSession?.sessionToken ?? "none"}</span>
    </div>
  );
}

describe("AdminContext", () => {
  beforeEach(() => {
    createAdminSessionApiMock.mockReset();
    window.sessionStorage.clear();
  });

  it("sessionStorage에 저장된 관리자 세션을 초기 상태로 복원한다", async () => {
    window.sessionStorage.setItem(
      "math-ocr:admin-session",
      JSON.stringify({
        sessionToken: "stored-admin-token",
        expiresAt: "2099-04-13T01:00:00+00:00",
      })
    );

    render(
      <AdminProvider>
        <AdminHarness />
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("admin-state")).toHaveTextContent("authenticated");
    });
    expect(screen.getByTestId("admin-token")).toHaveTextContent("stored-admin-token");
  });

  it("enterAdminMode가 세션을 저장하고 인증 상태를 갱신한다", async () => {
    const user = userEvent.setup();
    createAdminSessionApiMock.mockResolvedValueOnce({
      session_token: "fresh-admin-token",
      expires_at: "2099-04-13T01:30:00+00:00",
    });

    render(
      <AdminProvider>
        <AdminHarness />
      </AdminProvider>
    );

    await user.click(screen.getByRole("button", { name: "관리자 진입" }));

    await waitFor(() => {
      expect(createAdminSessionApiMock).toHaveBeenCalledWith("admin-secret");
    });
    expect(screen.getByTestId("admin-state")).toHaveTextContent("authenticated");
    expect(screen.getByTestId("admin-token")).toHaveTextContent("fresh-admin-token");
    expect(window.sessionStorage.getItem("math-ocr:admin-session")).toContain("fresh-admin-token");
  });

  it("exitAdminMode가 세션과 인증 상태를 함께 비운다", async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem(
      "math-ocr:admin-session",
      JSON.stringify({
        sessionToken: "stored-admin-token",
        expiresAt: "2099-04-13T01:00:00+00:00",
      })
    );

    render(
      <AdminProvider>
        <AdminHarness />
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("admin-state")).toHaveTextContent("authenticated");
    });

    await user.click(screen.getByRole("button", { name: "관리자 종료" }));

    expect(screen.getByTestId("admin-state")).toHaveTextContent("guest");
    expect(window.sessionStorage.getItem("math-ocr:admin-session")).toBeNull();
  });
});
