import { useCallback, useState } from "react";

import {
  autoDetectRegionsApi,
  createJobApi,
  downloadHwpxApi,
  exportHwpxApi,
  getJobApi,
  saveRegionsApi,
  runPipelineApi,
  resolveRuntimePath,
  type AutoDetectRegionsResult,
  type RunPipelineOptions,
  type RunPipelineResult,
} from "../api/jobApi";
import { mapBackendJob } from "./jobMappers";

export type RegionType = "text" | "diagram" | "mixed";
export type RegionStatus = "pending" | "running" | "completed" | "failed";
export type SelectionMode = "manual" | "auto_full" | "auto_detected" | "none";
export type InputDevice = "mouse" | "touch" | "pen" | "system";
export type WarningLevel = "normal" | "high_risk";

export interface Region {
  id: string;
  polygon: number[][];
  type: RegionType;
  order: number;
  selectionMode?: Exclude<SelectionMode, "none">;
  inputDevice?: InputDevice;
  warningLevel?: WarningLevel;
  autoDetectConfidence?: number;
  status?: RegionStatus;
  ocrText?: string;
  explanation?: string;
  mathml?: string;
  problemMarkdown?: string;
  explanationMarkdown?: string;
  markdownVersion?: string;
  verificationStatus?: "verified" | "warning" | "unverified";
  verificationWarnings?: string[];
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

  const autoDetectRegions = useCallback(async (jobId: string): Promise<AutoDetectRegionsResult> => {
    setJobs((prev) =>
      prev.map((job) =>
        job.id === jobId
          ? {
              ...job,
              lastError: undefined,
            }
          : job
      )
    );

    try {
      const result = await autoDetectRegionsApi(jobId);
      const backend = await getJobApi(jobId);

      setJobs((prev) =>
        prev.map((job) => (job.id === jobId ? mapBackendJob(backend, job) : job))
      );
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : "AI 자동 문항 찾기에 실패했습니다.";
      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                lastError: message,
              }
            : job
        )
      );
      throw error;
    }
  }, []);

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
                selectionMode: region.selectionMode ?? "manual",
                inputDevice: region.inputDevice,
                warningLevel: region.warningLevel ?? "normal",
                autoDetectConfidence:
                  region.selectionMode === "auto_detected" ? region.autoDetectConfidence : undefined,
                status: "pending",
                wasCharged: false,
                ocrCharged: false,
                imageCharged: false,
                explanationCharged: false,
                chargedAt: undefined,
                ocrText: undefined,
                explanation: undefined,
                mathml: undefined,
                problemMarkdown: undefined,
                explanationMarkdown: undefined,
                markdownVersion: undefined,
                verificationStatus: undefined,
                verificationWarnings: undefined,
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
          selection_mode: region.selectionMode ?? "manual",
          input_device: region.inputDevice,
          warning_level: region.warningLevel ?? "normal",
          auto_detect_confidence:
            region.selectionMode === "auto_detected" ? region.autoDetectConfidence : undefined,
        }))
      );

      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: regions.length > 0 ? "queued" : "regions_pending",
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
    try {
      const result = await exportHwpxApi(jobId);
      const hwpxPath = resolveRuntimePath(result.download_url) ?? result.download_url;
      const downloaded = await downloadHwpxApi(jobId);

      triggerDownloadBlob(downloaded.blob, downloaded.filename || "생성결과.hwpx");
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
    } catch (error) {
      const message = error instanceof Error ? error.message : "HWPX 내보내기에 실패했습니다.";
      setJobs((prev) =>
        prev.map((job) =>
          job.id === jobId
            ? {
                ...job,
                lastError: message,
              }
            : job
        )
      );
      throw error;
    }
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
    autoDetectRegions,
    saveRegions,
    runPipeline,
    hydrateJob,
    exportHwpx,
    deleteJob,
    getJob,
  };
}
