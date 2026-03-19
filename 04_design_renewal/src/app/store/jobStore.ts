import { useCallback, useState } from "react";

import {
  createJobApi,
  downloadHwpxApi,
  exportHwpxApi,
  getJobApi,
  saveRegionsApi,
  runPipelineApi,
  resolveRuntimePath,
  type RunPipelineOptions,
  type RunPipelineResult,
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
  cropUrl?: string;
  imageCropUrl?: string;
  styledImageUrl?: string;
  styledImageModel?: string;
  processingMs?: number;
  success?: boolean;
  errorReason?: string;
  wasCharged?: boolean;
  ocrCharged?: boolean;
  imageCharged?: boolean;
  explanationCharged?: boolean;
  chargedAt?: string;
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

export interface JobExecutionOptions extends RunPipelineOptions {}

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
                type: "mixed",
                status: "pending",
                ocrText: undefined,
                explanation: undefined,
                mathml: undefined,
                cropUrl: undefined,
                imageCropUrl: undefined,
                styledImageUrl: undefined,
                styledImageModel: undefined,
                processingMs: undefined,
                success: undefined,
                errorReason: undefined,
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
          type: "mixed",
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

  const runPipeline = useCallback(async (jobId: string, options: JobExecutionOptions): Promise<RunPipelineResult> => {
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
      const result = await runPipelineApi(jobId, options);
      const backend = await getJobApi(jobId);

      setJobs((prev) =>
        prev.map((job) => (job.id === jobId ? mapBackendJob(backend, job) : job))
      );
      return result;
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
    hydrateJob,
    exportHwpx,
    deleteJob,
    getJob,
  };
}
