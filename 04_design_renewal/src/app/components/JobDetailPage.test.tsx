import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Job } from "../store/jobStore";

const runPipelineMock = vi.fn(async () => ({
  job_id: "job-1",
  status: "running" as const,
  accepted: true,
  operation: "run" as const,
}));
const autoDetectRegionsMock = vi.fn(async () => ({
  job_id: "job-1",
  status: "running" as const,
  accepted: true,
  operation: "auto_detect" as const,
}));
const exportHwpxMock = vi.fn(async () => undefined);
const hydrateJobMock = vi.fn(async () => null);
const refreshProfileMock = vi.fn(async () => undefined);
const saveRegionsMock = vi.fn(async () => undefined);
let mockAuthUser = {
  name: "김수학",
  email: "math@example.com",
  avatarInitials: "김",
  credits: 2,
  openAiConnected: true,
  openAiMaskedKey: "sk-us••••7890",
  usedCredits: 3,
  chargedJobIds: [],
};
let mockJob: Job = {
  id: "job-1",
  fileName: "sample.png",
  imageUrl: "https://signed.example/source.png",
  imageWidth: 800,
  imageHeight: 600,
  status: "queued",
  createdAt: "2026-03-19T00:00:00.000Z",
  updatedAt: "2026-03-19T00:00:00.000Z",
  regions: [],
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: mockAuthUser,
    consumeCredit: vi.fn(),
    refreshProfile: refreshProfileMock,
  }),
}));

vi.mock("../context/JobContext", () => ({
  useJobs: () => ({
    autoDetectRegions: autoDetectRegionsMock,
    getJob: () => mockJob,
    saveRegions: saveRegionsMock,
    runPipeline: runPipelineMock,
    hydrateJob: hydrateJobMock,
    exportHwpx: exportHwpxMock,
  }),
}));

vi.mock("./RegionEditor", () => ({
  RegionEditor: ({
    regions,
    onRegionsChange,
  }: {
    regions: Job["regions"];
    onRegionsChange?: (regions: Job["regions"]) => void;
  }) => (
    <div>
      <div>RegionEditor</div>
      <button
        type="button"
        onClick={() =>
          onRegionsChange?.([
            ...regions,
            {
              id: `q${regions.length + 1}`,
              polygon: [
                [0, 0],
                [10, 0],
                [10, 10],
                [0, 10],
              ],
              type: "mixed",
              order: regions.length + 1,
              status: "pending",
            },
          ])
        }
      >
        영역 편집
      </button>
    </div>
  ),
}));

vi.mock("./ResultsViewer", () => ({
  ResultsViewer: () => <div>ResultsViewer</div>,
}));

import { JobDetailPage } from "./JobDetailPage";

describe("JobDetailPage", () => {
  beforeEach(() => {
    autoDetectRegionsMock.mockClear();
    runPipelineMock.mockClear();
    exportHwpxMock.mockClear();
    hydrateJobMock.mockReset();
    hydrateJobMock.mockResolvedValue(null);
    refreshProfileMock.mockReset();
    refreshProfileMock.mockResolvedValue(undefined);
    saveRegionsMock.mockReset();
    saveRegionsMock.mockResolvedValue(undefined);
    mockAuthUser = {
      name: "김수학",
      email: "math@example.com",
      avatarInitials: "김",
      credits: 2,
      openAiConnected: true,
      openAiMaskedKey: "sk-us••••7890",
      usedCredits: 3,
      chargedJobIds: [],
    };
    mockJob = {
      id: "job-1",
      fileName: "sample.png",
      imageUrl: "https://signed.example/source.png",
      imageWidth: 800,
      imageHeight: 600,
      status: "queued",
      createdAt: "2026-03-19T00:00:00.000Z",
      updatedAt: "2026-03-19T00:00:00.000Z",
      regions: [],
    };
  });

  it("체크박스 선택값을 runPipeline 호출에 전달한다", async () => {
    const user = userEvent.setup();
    mockJob = {
      ...mockJob,
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
          status: "pending",
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByRole("region", { name: "작업 상태 surface" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "액션 도크 surface" })).toBeInTheDocument();
    expect(screen.queryByText("API 참조")).not.toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: /해설 작성/i }));
    await user.click(screen.getByRole("button", { name: /^파이프라인 실행$/i }));

    expect(runPipelineMock).toHaveBeenCalledWith("job-1", {
      doOcr: true,
      doImageStylize: true,
      doExplanation: false,
    });
  });

  it("서비스 API 모드에서는 문항 수와 선택한 작업 수를 곱한 크레딧을 표시한다", async () => {
    const user = userEvent.setup();
    mockAuthUser = {
      ...mockAuthUser,
      credits: 10,
      openAiConnected: false,
      openAiMaskedKey: null,
    };
    mockJob = {
      ...mockJob,
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
          status: "completed",
          ocrText: "문제 1",
          explanation: "해설 1",
        },
        {
          id: "q2",
          polygon: [
            [20, 20],
            [30, 20],
            [30, 30],
            [20, 30],
          ],
          type: "mixed",
          order: 2,
          status: "completed",
          ocrText: "문제 2",
          explanation: "해설 2",
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("6 크레딧")).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: /해설 작성/i }));

    expect(screen.getByText("4 크레딧")).toBeInTheDocument();
  });

  it("OpenAI 연결 계정은 이미지 생성만 문항 수 기준으로 차감 예정에 포함한다", async () => {
    const user = userEvent.setup();
    mockAuthUser = {
      ...mockAuthUser,
      credits: 10,
      openAiConnected: true,
      openAiMaskedKey: "sk-us••••7890",
    };
    mockJob = {
      ...mockJob,
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
          status: "completed",
        },
        {
          id: "q2",
          polygon: [
            [20, 20],
            [30, 20],
            [30, 30],
            [20, 30],
          ],
          type: "mixed",
          order: 2,
          status: "completed",
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("2 크레딧")).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: /이미지 생성/i }));

    expect(screen.getByText("0 크레딧")).toBeInTheDocument();
  });

  it("처리 결과 설명은 문제 영역 크롭, 이미지 추출 원본, 이미지 생성 결과를 기준으로 안내한다", () => {
    mockJob = {
      ...mockJob,
      status: "completed",
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
          status: "completed",
          cropUrl: "https://signed.example/q1.crop.png",
          imageCropUrl: "https://signed.example/q1.image_crop.png",
          styledImageUrl: "https://signed.example/q1.styled.png",
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByRole("region", { name: "결과 보드 surface" })).toBeInTheDocument();
    expect(
      screen.queryAllByText((_, element) => {
        const text = element?.textContent || "";
        return (
          text.includes("문제 영역 크롭") &&
          text.includes("이미지 추출 원본") &&
          text.includes("이미지 생성 결과")
        );
      }).length
    ).toBeGreaterThan(0);
  });

  it("이미지 생성 옵션 설명은 Nano Banana 용어를 노출하지 않는다", () => {
    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/문제 영역에서 이미지 추출 원본과 생성 결과를 만듭니다\./i)).toBeInTheDocument();
    expect(screen.queryByText(/Nano Banana/i)).not.toBeInTheDocument();
  });

  it("실패 상태여도 내보낼 텍스트가 있으면 HWPX 내보내기 버튼을 보여준다", () => {
    mockJob = {
      ...mockJob,
      status: "failed",
      lastError: "image failed",
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
          status: "failed",
          ocrText: "문제 본문",
          explanation: "해설 본문",
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByRole("button", { name: /^HWPX 내보내기$/i })).toBeEnabled();
    expect(screen.getByText(/결과가 남은 1개 영역은 HWPX로 내보낼 수 있습니다\./i)).toBeInTheDocument();
  });

  it("검증 경고가 있으면 내보내기 안내 영역에 표시한다", () => {
    mockJob = {
      ...mockJob,
      status: "completed",
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
          status: "completed",
          ocrText: "문제 본문",
          explanation: "해설 본문",
          verificationStatus: "warning",
          verificationWarnings: ["정답 불일치"],
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/검증 경고 1개/i)).toBeInTheDocument();
  });

  it("편집 중인 영역 기준으로 예상 차감 크레딧을 다시 계산한다", async () => {
    const user = userEvent.setup();
    mockAuthUser = {
      ...mockAuthUser,
      credits: 10,
      openAiConnected: false,
      openAiMaskedKey: null,
    };
    mockJob = {
      ...mockJob,
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
          status: "pending",
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("3 크레딧")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "영역 편집" }));

    expect(screen.getByText("6 크레딧")).toBeInTheDocument();
  });

  it("영역이 없으면 AI 자동 문항 찾기 버튼을 노출한다", () => {
    mockJob = {
      ...mockJob,
      status: "regions_pending",
      regions: [],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/영역을 직접 그리지 않아도 AI가 문항·지문·수식·표·답안칸을 읽기 단위로 묶어서 찾아줍니다/i)).toBeInTheDocument();
    expect(screen.queryByText(/1토큰/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^AI가 문항 찾기$/i })).toBeInTheDocument();
  });

  it("영역이 없을 때는 자동 문항 찾기 호출을 우선한다", async () => {
    const user = userEvent.setup();
    mockJob = {
      ...mockJob,
      status: "regions_pending",
      regions: [],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await user.click(screen.getByRole("button", { name: /^AI가 문항 찾기$/i }));

    expect(autoDetectRegionsMock).toHaveBeenCalledWith("job-1");
    expect(runPipelineMock).not.toHaveBeenCalled();
  });

  it("고위험 자동 감지 결과가 있으면 실행 전 검토 안내를 유지한다", () => {
    mockJob = {
      ...mockJob,
      status: "queued",
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
          status: "pending",
          selectionMode: "auto_detected",
          warningLevel: "high_risk",
          autoDetectConfidence: 0.41,
        },
      ],
    };

    render(
      <MemoryRouter initialEntries={["/jobs/job-1"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/실행 전 박스를 확인하고 필요하면 수정하세요/i)).toBeInTheDocument();
    expect(screen.getByText(/경계 신뢰도가 낮거나 애매한 영역이 있습니다/i)).toBeInTheDocument();
  });

  it("running 상태에서는 polling으로 완료를 감시하고 프로필을 갱신한다", async () => {
    mockJob = {
      ...mockJob,
      status: "running",
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
          status: "running",
        },
      ],
    };
    hydrateJobMock.mockResolvedValueOnce({
      ...mockJob,
      status: "completed",
      updatedAt: "2026-03-19T00:05:00.000Z",
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
          status: "completed",
          ocrText: "문제 본문",
        },
      ],
    });

    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/jobs/job-1",
            state: { queuedOperation: "run" },
          } as never,
        ]}
      >
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(hydrateJobMock).toHaveBeenCalledWith("job-1");
    });
    await waitFor(() => {
      expect(refreshProfileMock).toHaveBeenCalledTimes(1);
    });
  });
});
