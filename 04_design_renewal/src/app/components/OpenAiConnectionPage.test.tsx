import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const connectOpenAiMock = vi.fn(async () => undefined);
const disconnectOpenAiMock = vi.fn(async () => undefined);

let mockAuthState = {
  user: null,
  connectOpenAi: connectOpenAiMock,
  disconnectOpenAi: disconnectOpenAiMock,
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuthState,
}));

import { OpenAiConnectionPage } from "./OpenAiConnectionPage";

describe("OpenAiConnectionPage", () => {
  beforeEach(() => {
    connectOpenAiMock.mockClear();
    disconnectOpenAiMock.mockClear();
    mockAuthState = {
      user: null,
      connectOpenAi: connectOpenAiMock,
      disconnectOpenAi: disconnectOpenAiMock,
    };
  });

  it("무료 무제한 대신 실제 과금 정책을 안내한다", () => {
    render(
      <MemoryRouter initialEntries={["/connect-openai"]}>
        <Routes>
          <Route path="/connect-openai" element={<OpenAiConnectionPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      screen.getByText("OpenAI API key를 연결하면 OCR과 해설은 사용자 소유 키로 처리할 수 있습니다. 이미지 생성은 별도 크레딧이 필요합니다.")
    ).toBeInTheDocument();
    expect(screen.getByText("OCR과 해설은 사용자 OpenAI key로 처리")).toBeInTheDocument();
    expect(screen.getByText("이미지 생성은 크레딧이 필요")).toBeInTheDocument();
    expect(screen.queryByText(/무료 처리 모드/)).not.toBeInTheDocument();
    expect(screen.queryByText(/크레딧 없이 사용자 소유 키로 처리/)).not.toBeInTheDocument();
  });
});
