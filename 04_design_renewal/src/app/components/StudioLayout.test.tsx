import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const logoutMock = vi.fn(async () => undefined);

let mockAuthState = {
  user: {
    credits: 9,
    openAiConnected: true,
  },
  isAuthenticated: true,
  logout: logoutMock,
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuthState,
}));

import { StudioLayout } from "./StudioLayout";

describe("StudioLayout", () => {
  beforeEach(() => {
    logoutMock.mockClear();
    mockAuthState = {
      user: {
        credits: 9,
        openAiConnected: true,
      },
      isAuthenticated: true,
      logout: logoutMock,
    };
  });

  it("작업실 헤더에 남은 이미지와 OpenAI 연결 상태를 함께 표시한다", () => {
    render(
      <MemoryRouter initialEntries={["/workspace"]}>
        <Routes>
          <Route element={<StudioLayout />}>
            <Route path="/workspace" element={<div>workspace</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("9개 이미지 남음")).toBeInTheDocument();
    expect(screen.getByText("OpenAI 연결됨")).toBeInTheDocument();
  });
});
