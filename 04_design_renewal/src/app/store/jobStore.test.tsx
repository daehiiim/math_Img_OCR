import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  createJobApiMock,
  downloadHwpxApiMock,
  exportHwpxApiMock,
  getJobApiMock,
  runPipelineApiMock,
  saveRegionsApiMock,
} = vi.hoisted(() => ({
  createJobApiMock: vi.fn(),
  downloadHwpxApiMock: vi.fn(),
  exportHwpxApiMock: vi.fn(),
  getJobApiMock: vi.fn(),
  runPipelineApiMock: vi.fn(),
  saveRegionsApiMock: vi.fn(),
}));

vi.mock("../api/jobApi", () => ({
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
    downloadHwpxApiMock.mockReset();
    exportHwpxApiMock.mockReset();
    getJobApiMock.mockReset();
    runPipelineApiMock.mockReset();
    saveRegionsApiMock.mockReset();
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
});
