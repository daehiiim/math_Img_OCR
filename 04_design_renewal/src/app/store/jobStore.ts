import { useCallback, useRef, useState } from "react";

import {
  autoDetectRegionsApi,
  createJobApi,
  deleteJobApi,
  downloadHwpxApi,
  exportHwpxApi,
  getJobApi,
  getJobHistoryApi,
  saveRegionsApi,
  runPipelineApi,
  resolveRuntimePath,
  type JobTaskAcceptedResult,
  type RunPipelineOptions,
} from "../api/jobApi";
import { mapBackendJob, mapBackendJobSummary } from "./jobMappers";

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
  updatedAt: string;
  hwpxPath?: string;
  lastError?: string;
}

export interface JobHistoryItem {
  id: string;
  fileName: string;
  status: JobStatus;
  createdAt: string;
  updatedAt: string;
  regionCount: number;
  hwpxReady: boolean;
  lastError?: string;
}

export interface JobExecutionOptions extends RunPipelineOptions {}

/** 브라우저 다운로드를 트리거한다. */
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

/** 최신 수정 시각 기준으로 history 목록을 내림차순 정렬한다. */
function sortJobHistory(items: JobHistoryItem[]): JobHistoryItem[] {
  return [...items].sort((left, right) => {
    const rightTime = Date.parse(right.updatedAt || right.createdAt);
    const leftTime = Date.parse(left.updatedAt || left.createdAt);
    return rightTime - leftTime;
  });
}

/** detail cache에 job snapshot을 덮어쓴다. */
function upsertJobRecord(items: Job[], nextJob: Job): Job[] {
  return [nextJob, ...items.filter((job) => job.id !== nextJob.id)];
}

/** history cache에 summary snapshot을 덮어쓴다. */
function upsertHistoryRecord(items: JobHistoryItem[], nextItem: JobHistoryItem): JobHistoryItem[] {
  return sortJobHistory([nextItem, ...items.filter((item) => item.id !== nextItem.id)]);
}

/** detail cache와 함께 쓰는 history summary를 만든다. */
function summarizeJob(job: Job): JobHistoryItem {
  return {
    id: job.id,
    fileName: job.fileName,
    status: job.status,
    createdAt: job.createdAt,
    updatedAt: job.updatedAt,
    regionCount: job.regions.length,
    hwpxReady: Boolean(job.hwpxPath),
    lastError: job.lastError,
  };
}

/** job 하나를 수정해 detail cache에 반영한다. */
function patchJobRecord(items: Job[], jobId: string, patch: (job: Job) => Job): Job[] {
  return items.map((job) => (job.id === jobId ? patch(job) : job));
}

/** history 카드 한 장만 국소 업데이트한다. */
function patchHistoryRecord(
  items: JobHistoryItem[],
  jobId: string,
  patch: (item: JobHistoryItem) => JobHistoryItem
): JobHistoryItem[] {
  return sortJobHistory(items.map((item) => (item.id === jobId ? patch(item) : item)));
}

/** 서버 동기화 전 임시 updatedAt을 현재 시각으로 갱신한다. */
function markUpdatedNow<T extends { updatedAt: string }>(item: T): T {
  return {
    ...item,
    updatedAt: new Date().toISOString(),
  };
}

/** 재저장 직후 영역 상태를 안전한 초깃값으로 재구성한다. */
function resetDraftRegion(region: Region): Region {
  return {
    ...region,
    type: "mixed",
    selectionMode: region.selectionMode ?? "manual",
    inputDevice: region.inputDevice,
    warningLevel: region.warningLevel ?? "normal",
    autoDetectConfidence: region.selectionMode === "auto_detected" ? region.autoDetectConfidence : undefined,
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
  };
}

/** 생성 직후 local preview와 서버 응답을 합쳐 첫 job snapshot을 만든다. */
function buildCreatedJob(
  jobId: string,
  fileName: string,
  imageUrl: string,
  width: number,
  height: number
): Pick<Job, "id" | "fileName" | "imageUrl" | "imageWidth" | "imageHeight" | "status" | "regions" | "createdAt" | "updatedAt"> {
  const now = new Date().toISOString();
  return {
    id: jobId,
    fileName,
    imageUrl,
    imageWidth: width,
    imageHeight: height,
    status: "regions_pending",
    regions: [],
    createdAt: now,
    updatedAt: now,
  };
}

/** job store는 detail cache와 workspace history cache를 함께 유지한다. */
export function useJobStore() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobHistory, setJobHistory] = useState<JobHistoryItem[]>([]);
  const jobsRef = useRef<Job[]>([]);
  const historyRef = useRef<JobHistoryItem[]>([]);

  /** detail cache를 동기 ref와 함께 갱신한다. */
  const writeJobs = useCallback((updater: (items: Job[]) => Job[]) => {
    const next = updater(jobsRef.current);
    jobsRef.current = next;
    setJobs(next);
  }, []);

  /** history cache를 동기 ref와 함께 갱신한다. */
  const writeHistory = useCallback((updater: (items: JobHistoryItem[]) => JobHistoryItem[]) => {
    const next = updater(historyRef.current);
    historyRef.current = next;
    setJobHistory(next);
  }, []);

  /** detail cache와 history cache를 같은 snapshot으로 맞춘다. */
  const commitJobSnapshot = useCallback(
    (job: Job) => {
      writeJobs((items) => upsertJobRecord(items, job));
      writeHistory((items) => upsertHistoryRecord(items, summarizeJob(job)));
    },
    [writeHistory, writeJobs]
  );

  /** 서버 history 요약을 그대로 workspace 목록에 반영한다. */
  const loadJobHistory = useCallback(async () => {
    const summaries = await getJobHistoryApi();
    writeHistory(() => sortJobHistory(summaries.map(mapBackendJobSummary)));
  }, [writeHistory]);

  const createJob = useCallback(
    async (fileName: string, imageUrl: string, width: number, height: number, imageFile: File) => {
      const backend = await createJobApi(imageFile);
      const localJob = buildCreatedJob(backend.job_id, fileName, imageUrl, width, height);
      const job = mapBackendJob(backend, localJob);
      commitJobSnapshot(job);
      return job.id;
    },
    [commitJobSnapshot]
  );

  const autoDetectRegions = useCallback(
    async (jobId: string): Promise<JobTaskAcceptedResult> => {
      const previousJob = jobsRef.current.find((job) => job.id === jobId) ?? null;
      writeJobs((items) => patchJobRecord(items, jobId, (job) => ({ ...job, lastError: undefined })));
      writeHistory((items) => patchHistoryRecord(items, jobId, (job) => ({ ...job, lastError: undefined })));

      try {
        writeJobs((items) =>
          patchJobRecord(items, jobId, (job) =>
            markUpdatedNow({ ...job, status: "running", lastError: undefined })
          )
        );
        writeHistory((items) =>
          patchHistoryRecord(items, jobId, (job) => markUpdatedNow({ ...job, status: "running", lastError: undefined }))
        );
        return await autoDetectRegionsApi(jobId);
      } catch (error) {
        const message = error instanceof Error ? error.message : "AI 자동 문항 찾기에 실패했습니다.";
        writeJobs((items) =>
          patchJobRecord(items, jobId, (job) => ({
            ...job,
            status: previousJob?.status ?? job.status,
            lastError: message,
          }))
        );
        writeHistory((items) =>
          patchHistoryRecord(items, jobId, (job) => ({
            ...job,
            status: previousJob?.status ?? job.status,
            lastError: message,
          }))
        );
        throw error;
      }
    },
    [writeHistory, writeJobs]
  );

  const saveRegions = useCallback(
    async (jobId: string, regions: Region[]) => {
      const nextStatus = regions.length > 0 ? "queued" : "regions_pending";
      const resetRegions = regions.map(resetDraftRegion);

      writeJobs((items) =>
        patchJobRecord(items, jobId, (job) =>
          markUpdatedNow({ ...job, status: "regions_pending", lastError: undefined, regions: resetRegions })
        )
      );
      writeHistory((items) =>
        patchHistoryRecord(items, jobId, (job) =>
          markUpdatedNow({ ...job, status: "regions_pending", regionCount: resetRegions.length, hwpxReady: false, lastError: undefined })
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
            auto_detect_confidence: region.selectionMode === "auto_detected" ? region.autoDetectConfidence : undefined,
          }))
        );

        writeJobs((items) => patchJobRecord(items, jobId, (job) => ({ ...job, status: nextStatus, lastError: undefined })));
        writeHistory((items) => patchHistoryRecord(items, jobId, (job) => ({ ...job, status: nextStatus, lastError: undefined })));
      } catch (error) {
        const message = error instanceof Error ? error.message : "영역 저장에 실패했습니다.";
        writeJobs((items) => patchJobRecord(items, jobId, (job) => ({ ...job, status: "regions_pending", lastError: message })));
        writeHistory((items) => patchHistoryRecord(items, jobId, (job) => ({ ...job, status: "regions_pending", lastError: message })));
        throw error;
      }
    },
    [writeHistory, writeJobs]
  );

  const runPipeline = useCallback(
    async (jobId: string, options: JobExecutionOptions): Promise<JobTaskAcceptedResult> => {
      const previousJob = jobsRef.current.find((job) => job.id === jobId) ?? null;
      writeJobs((items) =>
        patchJobRecord(items, jobId, (job) =>
          markUpdatedNow({
            ...job,
            status: "running",
            lastError: undefined,
            regions: job.regions.map((region) => ({ ...region, status: "running" })),
          })
        )
      );
      writeHistory((items) => patchHistoryRecord(items, jobId, (job) => markUpdatedNow({ ...job, status: "running", lastError: undefined })));

      try {
        return await runPipelineApi(jobId, options);
      } catch (error) {
        const message = error instanceof Error ? error.message : "파이프라인 실행 중 오류가 발생했습니다.";
        writeJobs((items) =>
          patchJobRecord(items, jobId, (job) => ({
            ...job,
            status: previousJob?.status ?? job.status,
            regions: previousJob?.regions ?? job.regions,
            lastError: message,
          }))
        );
        writeHistory((items) =>
          patchHistoryRecord(items, jobId, (job) => ({
            ...job,
            status: previousJob?.status ?? job.status,
            lastError: message,
          }))
        );
        throw error;
      }
    },
    [writeHistory, writeJobs]
  );

  const hydrateJob = useCallback(
    async (jobId: string): Promise<Job> => {
      const backend = await getJobApi(jobId);
      const existing = jobsRef.current.find((job) => job.id === jobId) ?? null;
      const hydrated = mapBackendJob(backend, existing);
      commitJobSnapshot(hydrated);
      return hydrated;
    },
    [commitJobSnapshot]
  );

  const exportHwpx = useCallback(
    async (jobId: string) => {
      try {
        const result = await exportHwpxApi(jobId);
        const hwpxPath = resolveRuntimePath(result.download_url) ?? result.download_url;
        const downloaded = await downloadHwpxApi(jobId);

        triggerDownloadBlob(downloaded.blob, downloaded.filename || "생성결과.hwpx");
        writeJobs((items) =>
          patchJobRecord(items, jobId, (job) =>
            markUpdatedNow({ ...job, status: "exported", hwpxPath, lastError: undefined })
          )
        );
        writeHistory((items) =>
          patchHistoryRecord(items, jobId, (job) =>
            markUpdatedNow({ ...job, status: "exported", hwpxReady: true, lastError: undefined })
          )
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "HWPX 내보내기에 실패했습니다.";
        writeJobs((items) => patchJobRecord(items, jobId, (job) => ({ ...job, lastError: message })));
        writeHistory((items) => patchHistoryRecord(items, jobId, (job) => ({ ...job, lastError: message })));
        throw error;
      }
    },
    [writeHistory, writeJobs]
  );

  const deleteJob = useCallback(
    async (jobId: string) => {
      await deleteJobApi(jobId);
      writeJobs((items) => items.filter((job) => job.id !== jobId));
      writeHistory((items) => items.filter((job) => job.id !== jobId));
    },
    [writeHistory, writeJobs]
  );

  /** detail cache에서 현재 job snapshot을 조회한다. */
  const getJob = useCallback((jobId: string) => jobsRef.current.find((job) => job.id === jobId) || null, []);

  return {
    jobs,
    jobHistory,
    createJob,
    loadJobHistory,
    autoDetectRegions,
    saveRegions,
    runPipeline,
    hydrateJob,
    exportHwpx,
    deleteJob,
    getJob,
  };
}
