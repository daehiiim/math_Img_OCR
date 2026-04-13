import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getAdminDashboardApiMock } = vi.hoisted(() => ({
  getAdminDashboardApiMock: vi.fn(),
}));

const { exitAdminModeMock, navigateMock, toastMock, adminStateRef } = vi.hoisted(() => ({
  exitAdminModeMock: vi.fn(),
  navigateMock: vi.fn(),
  toastMock: vi.fn(),
  adminStateRef: {
    current: {
      adminSession: {
        sessionToken: "admin-token-123",
        expiresAt: "2099-04-13T01:00:00+00:00",
      },
      isAdminAuthenticated: true,
    },
  },
}));

vi.mock("../api/adminApi", () => ({
  getAdminDashboardApi: getAdminDashboardApiMock,
}));

vi.mock("../context/AdminContext", () => ({
  useAdmin: () => ({
    ...adminStateRef.current,
    exitAdminMode: exitAdminModeMock,
  }),
}));

vi.mock("sonner", () => ({
  toast: toastMock,
}));

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

import { AdminDashboardPage } from "./AdminDashboardPage";

describe("AdminDashboardPage", () => {
  beforeEach(() => {
    getAdminDashboardApiMock.mockReset();
    exitAdminModeMock.mockReset();
    navigateMock.mockReset();
    toastMock.mockReset();
    adminStateRef.current = {
      adminSession: {
        sessionToken: "admin-token-123",
        expiresAt: "2099-04-13T01:00:00+00:00",
      },
      isAdminAuthenticated: true,
    };
  });

  it("관리자 KPI와 최근 실행 목록을 렌더링한다", async () => {
    const user = userEvent.setup();
    getAdminDashboardApiMock.mockResolvedValue({
      generated_at: "2026-04-13T00:30:00+00:00",
      failed_jobs_today: 4,
      missing_openai_request_regions_today: 2,
      recent_user_runs: [
        {
          user_label: "홍길동",
          user_id_suffix: "9999",
          job_id: "job-123",
          file_name: "sheet.png",
          job_status: "completed",
          region_count: 3,
          ran_at: "2026-04-13T00:25:00+00:00",
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/admin"]}>
        <Routes>
          <Route path="/workspace/admin" element={<AdminDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(getAdminDashboardApiMock).toHaveBeenCalledWith("admin-token-123");
    });

    expect(screen.getByRole("heading", { name: "관리자 대시보드" })).toBeInTheDocument();
    expect(screen.getByText("오늘 실패 작업 수")).toBeInTheDocument();
    expect(screen.getByText("OpenAI 호출 누락 건")).toBeInTheDocument();
    expect(screen.getByText("사용자별 최근 실행")).toBeInTheDocument();
    expect(screen.getByText("홍길동")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "수동 새로고침" }));

    await waitFor(() => {
      expect(getAdminDashboardApiMock).toHaveBeenCalledTimes(2);
    });
  });

  it("세션이 없으면 워크스페이스로 되돌리고 재인증 토스트를 띄운다", async () => {
    adminStateRef.current = {
      adminSession: null,
      isAdminAuthenticated: false,
    };

    render(
      <MemoryRouter initialEntries={["/workspace/admin"]}>
        <Routes>
          <Route path="/workspace/admin" element={<AdminDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/workspace", { replace: true });
    });
    expect(toastMock).toHaveBeenCalled();
  });
});
