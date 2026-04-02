import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  clearGuestDraftMock,
  createJobMock,
  guestDraftState,
  prepareLoginMock,
  readGuestDraftMock,
  refreshProfileMock,
  runPipelineMock,
  saveGuestDraftMock,
  saveRegionsMock,
} = vi.hoisted(() => {
  const guestDraftState = {
    current: null as
      | {
          image: {
            url: string;
            file: File;
            name: string;
            mimeType: string;
            width: number;
            height: number;
          };
          executionOptions: {
            doOcr: boolean;
            doImageStylize: boolean;
            doExplanation: boolean;
          };
          regions: Array<Record<string, unknown>>;
        }
      | null,
  };

  return {
    clearGuestDraftMock: vi.fn(async () => {
      guestDraftState.current = null;
    }),
    createJobMock: vi.fn(async () => "job-1"),
    guestDraftState,
    prepareLoginMock: vi.fn(),
    readGuestDraftMock: vi.fn(async () => guestDraftState.current),
    refreshProfileMock: vi.fn(async () => undefined),
    runPipelineMock: vi.fn(async () => ({
      job_id: "job-1",
      status: "completed" as const,
      charged_count: 1,
      completed_count: 1,
      failed_count: 0,
      exportable_count: 1,
    })),
    saveGuestDraftMock: vi.fn(async (draft) => {
      guestDraftState.current = {
        image: {
          url: "blob:guest-draft",
          file: draft.image.file,
          name: draft.image.name,
          mimeType: draft.image.mimeType,
          width: draft.image.width,
          height: draft.image.height,
        },
        executionOptions: draft.executionOptions,
        regions: draft.regions,
      };
    }),
    saveRegionsMock: vi.fn(async () => undefined),
  };
});

let mockAuthState = {
  isAuthenticated: true,
  prepareLogin: prepareLoginMock,
  refreshProfile: refreshProfileMock,
  user: {
    credits: 3,
    openAiConnected: true,
  },
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuthState,
}));

vi.mock("../context/JobContext", () => ({
  useJobs: () => ({
    createJob: createJobMock,
    runPipeline: runPipelineMock,
    saveRegions: saveRegionsMock,
  }),
}));

vi.mock("../lib/guestDraftStorage", () => ({
  clearGuestDraft: clearGuestDraftMock,
  readGuestDraft: readGuestDraftMock,
  saveGuestDraft: saveGuestDraftMock,
}));

vi.mock("./RegionEditor", () => ({
  RegionEditor: ({
    onRegionsChange,
    regions,
  }: {
    onRegionsChange?: (regions: Array<Record<string, unknown>>) => void;
    regions: Array<Record<string, unknown>>;
  }) => (
    <div>
      <p>RegionEditor</p>
      <p>현재 영역 {regions.length}개</p>
      <button
        type="button"
        onClick={() =>
          onRegionsChange?.([
            {
              id: "q1",
              polygon: [
                [0, 0],
                [10, 0],
                [10, 10],
                [0, 10],
              ],
              type: "mixed",
              order: 1,
            },
          ])
        }
      >
        영역 추가
      </button>
    </div>
  ),
}));

import { NewJobPage } from "./NewJobPage";

function PricingLocationProbe() {
  const location = useLocation();

  return <div>{`pricing page ${location.search}`}</div>;
}

describe("NewJobPage", () => {
  beforeEach(() => {
    clearGuestDraftMock.mockClear();
    createJobMock.mockClear();
    guestDraftState.current = null;
    prepareLoginMock.mockClear();
    readGuestDraftMock.mockClear();
    refreshProfileMock.mockClear();
    runPipelineMock.mockClear();
    saveGuestDraftMock.mockClear();
    saveRegionsMock.mockClear();
    mockAuthState = {
      isAuthenticated: true,
      prepareLogin: prepareLoginMock,
      refreshProfile: refreshProfileMock,
      user: {
        credits: 3,
        openAiConnected: true,
      },
    };

    class MockFileReader {
      onload: ((event: { target: { result: string } }) => void) | null = null;

      readAsDataURL(file: File) {
        this.onload?.({
          target: {
            result: `data:${file.type};base64,ZmFrZQ==`,
          },
        });
      }
    }

    class MockImage {
      onload: (() => void) | null = null;
      width = 320;
      height = 240;

      set src(_value: string) {
        this.onload?.();
      }
    }

    vi.stubGlobal("FileReader", MockFileReader as unknown as typeof FileReader);
    vi.stubGlobal("Image", MockImage as unknown as typeof Image);
  });

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

  it("비로그인 사용자도 파일을 선택해 draft 미리보기를 만들 수 있다", async () => {
    mockAuthState = {
      isAuthenticated: false,
      prepareLogin: prepareLoginMock,
      refreshProfile: refreshProfileMock,
      user: null,
    };

    render(
      <MemoryRouter>
        <NewJobPage />
      </MemoryRouter>
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake"], "sample.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText("sample.png")).toBeInTheDocument();
    expect(screen.getByText("320 × 240px")).toBeInTheDocument();
    expect(prepareLoginMock).not.toHaveBeenCalled();
  });

  it("업로드 후에는 별도 미리보기 카드 없이 영역 지정 화면에서 파일을 교체할 수 있다", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <NewJobPage />
      </MemoryRouter>
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: {
        files: [new File(["fake"], "sample.png", { type: "image/png" })],
      },
    });

    expect(await screen.findByText("sample.png")).toBeInTheDocument();
    expect(screen.queryByText("업로드 미리보기")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "다른 파일 선택" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "다른 파일 선택" }));

    expect(screen.getByRole("button", { name: "파일 선택" })).toBeInTheDocument();
    expect(screen.queryByText("sample.png")).not.toBeInTheDocument();
  });

  it("비로그인 상태에서 파이프라인 실행을 누르면 draft를 저장하고 로그인으로 이동한다", async () => {
    const user = userEvent.setup();
    mockAuthState = {
      isAuthenticated: false,
      prepareLogin: prepareLoginMock,
      refreshProfile: refreshProfileMock,
      user: null,
    };

    render(
      <MemoryRouter initialEntries={["/new"]}>
        <Routes>
          <Route path="/new" element={<NewJobPage />} />
          <Route path="/login" element={<div>login page</div>} />
        </Routes>
      </MemoryRouter>
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: {
        files: [new File(["fake"], "sample.png", { type: "image/png" })],
      },
    });

    await screen.findByText("sample.png");
    await user.click(screen.getByRole("button", { name: "영역 추가" }));
    await user.click(screen.getByRole("button", { name: /파이프라인 실행/i }));

    expect(prepareLoginMock).toHaveBeenCalledWith("/new?resumeDraft=1");
    expect(await screen.findByText("login page")).toBeInTheDocument();
    expect(saveGuestDraftMock).toHaveBeenCalledWith(
      expect.objectContaining({
        image: expect.objectContaining({
          name: "sample.png",
        }),
      })
    );
  });

  it("로그인 후 복원된 draft로 createJob, saveRegions, runPipeline을 순서대로 호출한다", async () => {
    const user = userEvent.setup();
    guestDraftState.current = {
      image: {
        url: "blob:restored-draft",
        file: new File(["restored"], "restored.png", { type: "image/png" }),
        name: "restored.png",
        mimeType: "image/png",
        width: 400,
        height: 300,
      },
      executionOptions: {
        doOcr: true,
        doImageStylize: false,
        doExplanation: true,
      },
      regions: [
        {
          id: "q1",
          polygon: [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
          ],
          type: "mixed",
          order: 1,
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/new?resumeDraft=1"]}>
        <Routes>
          <Route path="/new" element={<NewJobPage />} />
          <Route path="/workspace/job/:jobId" element={<div>job detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("restored.png")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /파이프라인 실행/i }));

    await waitFor(() => expect(createJobMock).toHaveBeenCalledTimes(1));
    expect(saveRegionsMock).toHaveBeenCalledWith(
      "job-1",
      expect.arrayContaining([expect.objectContaining({ id: "q1" })])
    );
    expect(runPipelineMock).toHaveBeenCalledWith("job-1", {
      doOcr: true,
      doImageStylize: false,
      doExplanation: true,
    });
    expect(await screen.findByText("job detail")).toBeInTheDocument();
  });

  it("영역이 없어도 자동 전체 인식 안내를 보여주고 saveRegions 없이 실행한다", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/new"]}>
        <Routes>
          <Route path="/new" element={<NewJobPage />} />
          <Route path="/workspace/job/:jobId" element={<div>job detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: {
        files: [new File(["fake"], "sample.png", { type: "image/png" })],
      },
    });

    await screen.findByText("sample.png");
    expect(screen.getByText(/영역을 지정하지 않으면 이미지 전체를 자동 인식/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /파이프라인 실행/i }));

    await waitFor(() => expect(createJobMock).toHaveBeenCalledTimes(1));
    expect(saveRegionsMock).not.toHaveBeenCalled();
    expect(runPipelineMock).toHaveBeenCalledWith("job-1", {
      doOcr: true,
      doImageStylize: true,
      doExplanation: true,
    });
    expect(await screen.findByText("job detail")).toBeInTheDocument();
  });

  it("로그인 사용자의 크레딧이 부족하면 draft를 저장하고 결제 경로로 이동한다", async () => {
    const user = userEvent.setup();
    mockAuthState = {
      isAuthenticated: true,
      prepareLogin: prepareLoginMock,
      refreshProfile: refreshProfileMock,
      user: {
        credits: 0,
        openAiConnected: true,
      },
    };

    render(
      <MemoryRouter initialEntries={["/new"]}>
        <Routes>
          <Route path="/new" element={<NewJobPage />} />
          <Route path="/pricing" element={<PricingLocationProbe />} />
        </Routes>
      </MemoryRouter>
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: {
        files: [new File(["fake"], "sample.png", { type: "image/png" })],
      },
    });

    await screen.findByText("sample.png");
    await user.click(screen.getByRole("button", { name: "영역 추가" }));
    await user.click(screen.getByRole("button", { name: /파이프라인 실행/i }));

    expect(
      await screen.findByText("pricing page ?returnTo=%2Fnew%3FresumeDraft%3D1")
    ).toBeInTheDocument();
    expect(saveGuestDraftMock).toHaveBeenCalledWith(
      expect.objectContaining({
        image: expect.objectContaining({
          name: "sample.png",
        }),
      })
    );
  });
});
