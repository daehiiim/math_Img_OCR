import { describe, expect, it } from "vitest";

import type { BackendJob } from "../api/jobApi";
import { mapBackendJob, normalizeJobStatus } from "./jobMappers";

describe("normalizeJobStatus", () => {
  it("queued 상태를 유지한다", () => {
    expect(normalizeJobStatus("queued")).toBe("queued");
  });

  it("failed 상태를 유지한다", () => {
    expect(normalizeJobStatus("failed")).toBe("failed");
  });
});

describe("mapBackendJob", () => {
  it("백엔드 작업을 프런트 작업으로 변환한다", () => {
    const backend: BackendJob = {
      job_id: "job_123",
      status: "completed",
      file_name: "sample.png",
      image_url: "/runtime/jobs/job_123/input/sample.png",
      image_width: 800,
      image_height: 600,
      regions: [
        {
          id: "q1",
          status: "completed",
          type: "diagram",
          order: 2,
          polygon: [
            [10, 20],
            [110, 20],
            [110, 80],
            [10, 80],
          ],
          ocr_text: "OCR text",
          problem_markdown: "OCR $x$",
          explanation_markdown: "설명 $y$",
          markdown_version: "mathocr_markdown_bridge_v1",
          image_crop_url: "/runtime/jobs/job_123/outputs/q1.image_crop.png",
          styled_image_url: "/runtime/jobs/job_123/outputs/q1.styled.png",
          styled_image_model: "gemini-3-pro-image-preview",
        },
      ],
    };

    const job = mapBackendJob(backend, null);

    expect(job.id).toBe("job_123");
    expect(job.fileName).toBe("sample.png");
    expect(job.imageWidth).toBe(800);
    expect(job.imageHeight).toBe(600);
    expect(job.status).toBe("completed");
    expect(job.regions[0]).toMatchObject({
      id: "q1",
      type: "diagram",
      order: 2,
      ocrText: "OCR text",
      problemMarkdown: "OCR $x$",
      explanationMarkdown: "설명 $y$",
      markdownVersion: "mathocr_markdown_bridge_v1",
      imageCropUrl: "http://localhost:8000/runtime/jobs/job_123/outputs/q1.image_crop.png",
      styledImageUrl: "http://localhost:8000/runtime/jobs/job_123/outputs/q1.styled.png",
      styledImageModel: "gemini-3-pro-image-preview",
    });
  });

  it("기존 로컬 영역 정보가 있으면 polygon과 크기를 보존한다", () => {
    const backend: BackendJob = {
      job_id: "job_123",
      status: "running",
      file_name: null,
      image_url: null,
      image_width: null,
      image_height: null,
      regions: [
        {
          id: "q1",
          status: "running",
          type: "mixed",
        },
      ],
    };

    const job = mapBackendJob(backend, {
      id: "job_123",
      fileName: "local.png",
      imageUrl: "data:image/png;base64,abc",
      imageWidth: 320,
      imageHeight: 240,
      status: "queued",
      regions: [
        {
          id: "q1",
          polygon: [
            [1, 2],
            [3, 4],
            [5, 6],
            [7, 8],
          ],
          type: "text",
          order: 7,
        },
      ],
      createdAt: "2026-03-15T00:00:00.000Z",
    });

    expect(job.fileName).toBe("local.png");
    expect(job.imageWidth).toBe(320);
    expect(job.imageHeight).toBe(240);
    expect(job.regions[0].polygon).toEqual([
      [1, 2],
      [3, 4],
      [5, 6],
      [7, 8],
    ]);
    expect(job.regions[0].order).toBe(7);
  });
});
