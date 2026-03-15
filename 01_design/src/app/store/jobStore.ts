import { useCallback, useState } from "react";
import {
  createJobApi,
  exportHwpxApi,
  getJobApi,
  resolveRuntimePath,
  runPipelineApi,
  saveRegionsApi,
  saveEditedSvgApi,
  getRegionSvgApi,
  downloadHwpxApi,
  type BackendJob,
  type BackendJobStatus,
} from "../api/jobApi";

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

function normalizeJobStatus(status: BackendJobStatus | JobStatus): JobStatus {
  if (status === "created") return "created";
  if (status === "regions_pending") return "regions_pending";
  if (status === "queued") return "queued";
  if (status === "running") return "running";
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  return status;
}

function normalizeRegionType(value: string | undefined): RegionType {
  if (value === "text" || value === "diagram" || value === "mixed") {
    return value;
  }
  return "mixed";
}

function mapBackendRegion(region: BackendJob["regions"][number], fallback?: Region): Region {
  return {
    id: region.id,
    polygon: region.polygon ?? fallback?.polygon ?? [],
    type: normalizeRegionType(region.type),
    order: region.order ?? fallback?.order ?? 1,
    status: region.status,
    ocrText: region.ocr_text ?? undefined,
    explanation: region.explanation ?? undefined,
    mathml: region.mathml ?? undefined,
    svgUrl: resolveRuntimePath(region.svg_url),
    cropUrl: resolveRuntimePath(region.crop_url),
    processingMs: region.processing_ms ?? undefined,
    success: region.success ?? undefined,
    errorReason: region.error_reason ?? (region.status === "failed" ? "영역 처리 실패" : undefined),
    editedSvgUrl: resolveRuntimePath(region.edited_svg_url),
    editedSvgVersion: region.edited_svg_version ?? undefined,
  };
}

function mergeBackendJob(local: Job, backend: BackendJob): Job {
  const prevById = new Map(local.regions.map((r) => [r.id, r]));
  return {
    ...local,
    status: normalizeJobStatus(backend.status),
    imageUrl: resolveRuntimePath(backend.image_url) || local.imageUrl,
    regions: backend.regions.map((r) => mapBackendRegion(r, prevById.get(r.id))),
  };
}

export function useJobStore() {
  const [jobs, setJobs] = useState<Job[]>([]);

  const createJob = useCallback(
    async (fileName: string, imageUrl: string, width: number, height: number, imageFile: File) => {
      const backend = await createJobApi(imageFile);
      const job: Job = {
        id: backend.job_id,
        fileName,
        imageUrl,
        imageWidth: width,
        imageHeight: height,
        status: normalizeJobStatus(backend.status),
        regions: [],
        createdAt: new Date().toISOString(),
      };

      setJobs((prev) => [job, ...prev]);
      return job.id;
    },
    []
  );

  const saveRegions = useCallback(async (jobId: string, regions: Region[]) => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === jobId
          ? {
              ...j,
              // IMPORTANT: keep regions_pending until backend save succeeds
              status: "regions_pending",
              lastError: undefined,
              regions: regions.map((r) => ({
                ...r,
                status: "pending",
                ocrText: undefined,
                explanation: undefined,
                mathml: undefined,
                svgUrl: undefined,
                cropUrl: undefined,
                processingMs: undefined,
                success: undefined,
                errorReason: undefined,
              })),
            }
          : j
      )
    );

    try {
      await saveRegionsApi(
        jobId,
        regions.map((r) => ({
          id: r.id,
          polygon: r.polygon,
          type: r.type,
          order: r.order,
        }))
      );

      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? {
                ...j,
                status: "queued",
                lastError: undefined,
              }
            : j
        )
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "영역 저장에 실패했습니다.";
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? {
                ...j,
                status: "regions_pending",
                lastError: message,
              }
            : j
        )
      );
      throw error;
    }
  }, []);

  const runPipeline = useCallback(async (jobId: string): Promise<void> => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === jobId
          ? {
              ...j,
              status: "running",
              lastError: undefined,
              regions: j.regions.map((r) => ({ ...r, status: "running" })),
            }
          : j
      )
    );

    try {
      await runPipelineApi(jobId);

      for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt += 1) {
        const backend = await getJobApi(jobId);
        setJobs((prev) =>
          prev.map((j) => {
            if (j.id !== jobId) return j;
            return mergeBackendJob(j, backend);
          })
        );

        if (backend.status === "completed") return;
        if (backend.status === "failed") {
          throw new Error("파이프라인 처리에 실패했습니다.");
        }

        await sleep(POLL_INTERVAL_MS);
      }

      throw new Error("처리 상태 조회 시간이 초과되었습니다.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "알 수 없는 오류가 발생했습니다.";
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, status: "failed", lastError: message } : j))
      );
      throw error;
    }
  }, []);


  const saveEditedSvg = useCallback(async (jobId: string, regionId: string, svg: string) => {
    await saveEditedSvgApi(jobId, regionId, svg);
    const backend = await getJobApi(jobId);
    setJobs((prev) =>
      prev.map((j) => {
        if (j.id !== jobId) return j;
        return mergeBackendJob(j, backend);
      })
    );
  }, []);


  const hydrateJob = useCallback(async (jobId: string): Promise<Job> => {
    const backend = await getJobApi(jobId);

    let hydrated: Job | null = null;
    setJobs((prev) => {
      const existing = prev.find((j) => j.id === jobId) || null;
      const fallbackFileName = backend.image_url ? backend.image_url.split("/").pop() || `${jobId}.png` : `${jobId}.png`;

      if (existing) {
        hydrated = mergeBackendJob(existing, backend);
        return prev.map((j) => (j.id === jobId ? (hydrated as Job) : j));
      }

      const created: Job = {
        id: backend.job_id,
        fileName: fallbackFileName,
        imageUrl: resolveRuntimePath(backend.image_url) || "",
        imageWidth: 0,
        imageHeight: 0,
        status: normalizeJobStatus(backend.status),
        regions: backend.regions.map((r) => mapBackendRegion(r)),
        createdAt: new Date().toISOString(),
      };
      hydrated = created;
      return [created, ...prev];
    });

    return hydrated as Job;
  }, []);


  const loadRegionSvg = useCallback(async (jobId: string, regionId: string): Promise<string> => {
    const data = await getRegionSvgApi(jobId, regionId);
    return data.svg;
  }, []);

  const exportHwpx = useCallback(async (jobId: string) => {
    const result = await exportHwpxApi(jobId);
    const resolvedDownloadUrl = resolveRuntimePath(result.download_url) ?? result.download_url;

    setJobs((prev) =>
      prev.map((j) =>
        j.id === jobId
          ? {
              ...j,
              status: "exported",
              hwpxPath: resolvedDownloadUrl,
              lastError: undefined,
            }
          : j
      )
    );

    const downloaded = await downloadHwpxApi(jobId);
    const filename = downloaded.filename.toLowerCase().endsWith(".hwpx") ? downloaded.filename : `${jobId}.hwpx`;
    triggerDownloadBlob(downloaded.blob, filename);
  }, []);

  const deleteJob = useCallback((jobId: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== jobId));
  }, []);

  const getJob = useCallback(
    (jobId: string) => {
      return jobs.find((j) => j.id === jobId) || null;
    },
    [jobs]
  );

  return { jobs, createJob, saveRegions, runPipeline, saveEditedSvg, loadRegionSvg, hydrateJob, exportHwpx, deleteJob, getJob };
}
