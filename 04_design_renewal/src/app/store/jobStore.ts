import { useCallback, useState } from "react";

import {
  createJobApi,
  downloadHwpxApi,
  exportHwpxApi,
  getJobApi,
  getRegionSvgApi,
  saveEditedSvgApi,
  saveRegionsApi,
  runPipelineApi,
  resolveRuntimePath,
} from "../api/jobApi";
import { mapBackendJob } from "./jobMappers";

export type RegionType = "text" | "diagram" | "mixed";
export type RegionStatus = "pending" | "running" | "completed" | "failed";

export interface Region {
  id: string;
  polygon: number[][];
  type: RegionType;
  order: number;
  status?: RegionStatus;
  ocrText?: string;
  explanation?: string;
  mathml?: string;
  svgUrl?: string;
  cropUrl?: string;
  processingMs?: number;
  success?: boolean;
  errorReason?: string;
  editedSvgUrl?: string;
  editedSvgVersion?: number;
  svgData?: string;
}

export type JobStatus =
  | "created"
  | "regions_pending"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "exported";

export interface Job {
  id: string;
  fileName: string;
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  status: JobStatus;
  regions: Region[];
  createdAt: string;
  hwpxPath?: string;
  lastError?: string;
}

const POLL_INTERVAL_MS = 1200;
const POLL_MAX_ATTEMPTS = 45;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function triggerDownloadBlob(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
}

export function useJobStore() {
  const [jobs, setJobs] = useState<Job[]>([]);

  const createJob = useCallback(
    async (fileName: string, imageUrl: string, width: number, height: number, imageFile: File) => {
      const backend = await createJobApi(imageFile);
      const job = mapBackendJob(backend, {
        id: backend.job_id,
        fileName,
        imageUrl,
        imageWidth: width,
        imageHeight: height,
        status: "regions_pending",
        regions: [],
        createdAt: new Date().toISOString(),
      });

      setJobs((prev) => [job, ...prev.filter((candidate) => candidate.id !== job.id)]);
      return job.id;
    },
    []
  );

  const saveRegions = useCallback(async (jobId: string, regions: Region[]) => {
    setJobs((prev) =>
      prev.map((job) =>
        job.id === jobId
          ? {
              ...job,
              status: "regions_pending",
              lastError: undefined,
              regions: regions.map((region) => ({
                ...region,
                status: "pending",
                ocrText: undefined,
                explanation: undefined,
                mathml: undefined,
                svgUrl: undefined,
                cropUrl: undefined,
                processingMs: undefined,
                success: undefined,
                errorReason: undefined,
                editedSvgUrl: undefined,
                editedSvgVersion: undefined,
                svgData: undefined,
              })),
            }
          : job
      )
    );

    try {
      await saveRegionsApi(
        jobId,
        regions.map((region) => ({
          id: region.id,
          polygon: region.polygon,
          type: region.type,
          order: region.order,
        }))
      );

      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: "queued",
                lastError: undefined,
              }
            : job
        )
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "영역 저장에 실패했습니다.";
      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: "regions_pending",
                lastError: message,
              }
            : job
        )
      );
      throw error;
    }
  }, []);

  const runPipeline = useCallback(async (jobId: string): Promise<void> => {
    setJobs((prev) =>
      prev.map((job) =>
        job.id === jobId
          ? {
              ...job,
              status: "running",
              lastError: undefined,
              regions: job.regions.map((region) => ({ ...region, status: "running" })),
            }
          : job
      )
    );

    try {
      await runPipelineApi(jobId);

      for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt += 1) {
        const backend = await getJobApi(jobId);
        let hydrated: Job | null = null;

        setJobs((prev) =>
          prev.map((job) => {
            if (job.id !== jobId) {
              return job;
            }

            hydrated = mapBackendJob(backend, job);
            return hydrated;
          })
        );

        if (backend.status === "completed") {
          return;
        }

        if (backend.status === "failed") {
          throw new Error("파이프라인 처리에 실패했습니다.");
        }

        await sleep(POLL_INTERVAL_MS);
      }

      throw new Error("처리 상태 조회 시간이 초과되었습니다.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "파이프라인 실행 중 오류가 발생했습니다.";
      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: "failed",
                lastError: message,
              }
            : job
        )
      );
      throw error;
    }
  }, []);

  const saveEditedSvg = useCallback(async (jobId: string, regionId: string, svg: string) => {
    await saveEditedSvgApi(jobId, regionId, svg);
    const backend = await getJobApi(jobId);
    setJobs((prev) => prev.map((job) => (job.id === jobId ? mapBackendJob(backend, job) : job)));
  }, []);

  const loadRegionSvg = useCallback(async (jobId: string, regionId: string): Promise<string> => {
    const data = await getRegionSvgApi(jobId, regionId);
    return data.svg;
  }, []);

  const hydrateJob = useCallback(async (jobId: string): Promise<Job> => {
    const backend = await getJobApi(jobId);
    let hydrated: Job | null = null;

    setJobs((prev) => {
      const existing = prev.find((job) => job.id === jobId) ?? null;
      hydrated = mapBackendJob(backend, existing);

      if (existing) {
        return prev.map((job) => (job.id === jobId ? hydrated! : job));
      }

      return [hydrated!, ...prev];
    });

    return hydrated!;
  }, []);

  const exportHwpx = useCallback(async (jobId: string) => {
    const result = await exportHwpxApi(jobId);
    const hwpxPath = resolveRuntimePath(result.download_url) ?? result.download_url;

    setJobs((prev) =>
      prev.map((job) =>
        job.id === jobId
          ? {
              ...job,
              status: "exported",
              hwpxPath,
              lastError: undefined,
            }
          : job
      )
    );

    const downloaded = await downloadHwpxApi(jobId);
    const filename = downloaded.filename.toLowerCase().endsWith(".hwpx")
      ? downloaded.filename
      : `${jobId}.hwpx`;
    triggerDownloadBlob(downloaded.blob, filename);
  }, []);

  const deleteJob = useCallback((jobId: string) => {
    setJobs((prev) => prev.filter((job) => job.id !== jobId));
  }, []);

  const getJob = useCallback(
    (jobId: string) => jobs.find((job) => job.id === jobId) || null,
    [jobs]
  );

  return {
    jobs,
    createJob,
    saveRegions,
    runPipeline,
    saveEditedSvg,
    loadRegionSvg,
    hydrateJob,
    exportHwpx,
    deleteJob,
    getJob,
  };
}
