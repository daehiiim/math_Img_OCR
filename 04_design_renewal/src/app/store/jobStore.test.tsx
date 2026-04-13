import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  autoDetectRegionsApiMock,
  createJobApiMock,
  downloadHwpxApiMock,
  exportHwpxApiMock,
  getJobApiMock,
  runPipelineApiMock,
  saveRegionsApiMock,
} = vi.hoisted(() => ({
  autoDetectRegionsApiMock: vi.fn(),
  createJobApiMock: vi.fn(),
  downloadHwpxApiMock: vi.fn(),
  exportHwpxApiMock: vi.fn(),
  getJobApiMock: vi.fn(),
  runPipelineApiMock: vi.fn(),
  saveRegionsApiMock: vi.fn(),
}));

vi.mock("../api/jobApi", () => ({
  autoDetectRegionsApi: autoDetectRegionsApiMock,
  createJobApi: createJobApiMock,
  downloadHwpxApi: downloadHwpxApiMock,
  exportHwpxApi: exportHwpxApiMock,
  getJobApi: getJobApiMock,
  runPipelineApi: runPipelineApiMock,
  saveRegionsApi: saveRegionsApiMock,
  resolveRuntimePath: (value: string | undefined) => value,
}));

import { useJobStore } from "./jobStore";

describe("useJobStore", () => {
  beforeEach(() => {
    createJobApiMock.mockReset();
    autoDetectRegionsApiMock.mockReset();
    downloadHwpxApiMock.mockReset();
    exportHwpxApiMock.mockReset();
    getJobApiMock.mockReset();
    runPipelineApiMock.mockReset();
    saveRegionsApiMock.mockReset();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:mock"),
      revokeObjectURL: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  it("영역 재저장 시 기존 과금 플래그를 즉시 초기화한다", async () => {
    createJobApiMock.mockResolvedValue({
      job_id: "job-1",
      status: "queued",
      file_name: "sample.png",
      image_url: "/sample.png",
      image_width: 400,
      image_height: 300,
      regions: [
        {
          id: "q1",
          status: "completed",
          polygon: [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
          ],
          type: "mixed",
          order: 1,
          was_charged: true,
          ocr_charged: true,
          image_charged: true,
          explanation_charged: true,
          charged_at: "2026-03-19T00:00:00Z",
          ocr_text: "기존 OCR",
          explanation: "기존 해설",
          styled_image_url: "/styled.png",
        },
      ],
    });

    let resolveSave: (() => void) | null = null;
    saveRegionsApiMock.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveSave = resolve;
        })
    );

    const { result } = renderHook(() => useJobStore());
    let jobId = "";

    await act(async () => {
      jobId = await result.current.createJob(
        "sample.png",
        "data:image/png;base64,ZmFrZQ==",
        400,
        300,
        new File(["fake"], "sample.png", { type: "image/png" })
      );
    });

    expect(result.current.getJob(jobId)?.regions[0]?.imageCharged).toBe(true);

    let pendingSave: Promise<void> | null = null;
    act(() => {
      pendingSave = result.current.saveRegions(jobId, [
        {
          id: "q1",
          polygon: [
            [0, 0],
            [20, 0],
            [20, 20],
            [0, 20],
          ],
          type: "mixed",
          order: 1,
        },
      ]);
    });

    const region = result.current.getJob(jobId)?.regions[0];
    expect(region?.wasCharged).toBe(false);
    expect(region?.ocrCharged).toBe(false);
    expect(region?.imageCharged).toBe(false);
    expect(region?.explanationCharged).toBe(false);
    expect(region?.chargedAt).toBeUndefined();
    expect(region?.ocrText).toBeUndefined();
    expect(region?.explanation).toBeUndefined();
    expect(region?.styledImageUrl).toBeUndefined();

    resolveSave?.();

    await act(async () => {
      await pendingSave;
    });
  });

  it("자동 문항 찾기 후 최신 job 상태로 hydrate한다", async () => {
    createJobApiMock.mockResolvedValue({
      job_id: "job-detect",
      status: "regions_pending",
      file_name: "sample.png",
      image_url: "/sample.png",
      image_width: 400,
      image_height: 300,
      regions: [],
    });
    autoDetectRegionsApiMock.mockResolvedValue({
      job_id: "job-detect",
      regions: [],
      detected_count: 2,
      review_required: false,
      detector_model: "gpt-test",
      detection_version: "openai_five_choice_v1",
      charged_count: 1,
    });
    getJobApiMock.mockResolvedValue({
      job_id: "job-detect",
      status: "queued",
      file_name: "sample.png",
      image_url: "/sample.png",
      image_width: 400,
      image_height: 300,
      regions: [
        {
          id: "q1",
          status: "pending",
          polygon: [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
          ],
          type: "mixed",
          order: 1,
          selection_mode: "auto_detected",
          auto_detect_confidence: 0.91,
        },
      ],
    });

    const { result } = renderHook(() => useJobStore());
    let jobId = "";

    await act(async () => {
      jobId = await result.current.createJob(
        "sample.png",
        "data:image/png;base64,ZmFrZQ==",
        400,
        300,
        new File(["fake"], "sample.png", { type: "image/png" })
      );
    });

    await act(async () => {
      await result.current.autoDetectRegions(jobId);
    });

    expect(autoDetectRegionsApiMock).toHaveBeenCalledWith("job-detect");
    expect(result.current.getJob(jobId)?.status).toBe("queued");
    expect(result.current.getJob(jobId)?.regions[0]?.selectionMode).toBe("auto_detected");
    expect(result.current.getJob(jobId)?.regions[0]?.autoDetectConfidence).toBe(0.91);
  });

  it("HWPX 다운로드가 끝나기 전에는 job 상태를 exported로 바꾸지 않는다", async () => {
    createJobApiMock.mockResolvedValue({
      job_id: "job-export-pending",
      status: "completed",
      file_name: "sample.png",
      image_url: "/sample.png",
      image_width: 400,
      image_height: 300,
      regions: [],
    });
    exportHwpxApiMock.mockResolvedValue({ download_url: "/jobs/job-export-pending/export/hwpx/download" });

    let resolveDownload: ((value: { blob: Blob; filename: string }) => void) | null = null;
    downloadHwpxApiMock.mockImplementation(
      () =>
        new Promise<{ blob: Blob; filename: string }>((resolve) => {
          resolveDownload = resolve;
        })
    );

    const { result } = renderHook(() => useJobStore());
    let jobId = "";

    await act(async () => {
      jobId = await result.current.createJob(
        "sample.png",
        "data:image/png;base64,ZmFrZQ==",
        400,
        300,
        new File(["fake"], "sample.png", { type: "image/png" })
      );
    });

    let pendingExport: Promise<void> | null = null;
    await act(async () => {
      pendingExport = result.current.exportHwpx(jobId);
      await Promise.resolve();
    });

    expect(result.current.getJob(jobId)?.status).toBe("completed");
    expect(result.current.getJob(jobId)?.hwpxPath).toBeUndefined();

    resolveDownload?.({ blob: new Blob(["hwpx"]), filename: "생성결과.hwpx" });

    await act(async () => {
      await pendingExport;
    });

    expect(result.current.getJob(jobId)?.status).toBe("exported");
    expect(result.current.getJob(jobId)?.hwpxPath).toBe("/jobs/job-export-pending/export/hwpx/download");
    expect(result.current.getJob(jobId)?.lastError).toBeUndefined();
  });

  it("HWPX 다운로드가 실패하면 이전 상태를 유지하고 에러를 기록한다", async () => {
    createJobApiMock.mockResolvedValue({
      job_id: "job-export-failed",
      status: "completed",
      file_name: "sample.png",
      image_url: "/sample.png",
      image_width: 400,
      image_height: 300,
      regions: [],
    });
    exportHwpxApiMock.mockResolvedValue({ download_url: "/jobs/job-export-failed/export/hwpx/download" });
    downloadHwpxApiMock.mockRejectedValue(new Error("다운로드 실패"));

    const { result } = renderHook(() => useJobStore());
    let jobId = "";

    await act(async () => {
      jobId = await result.current.createJob(
        "sample.png",
        "data:image/png;base64,ZmFrZQ==",
        400,
        300,
        new File(["fake"], "sample.png", { type: "image/png" })
      );
    });

    let failure: Error | null = null;
    await act(async () => {
      try {
        await result.current.exportHwpx(jobId);
      } catch (error) {
        failure = error as Error;
      }
    });

    expect(failure?.message).toBe("다운로드 실패");
    expect(result.current.getJob(jobId)?.status).toBe("completed");
    expect(result.current.getJob(jobId)?.hwpxPath).toBeUndefined();
    expect(result.current.getJob(jobId)?.lastError).toBe("다운로드 실패");
  });
});
