import type { BackendJob, BackendJobStatus, BackendJobSummary } from "../api/jobApi";
import { resolveRuntimePath } from "../api/jobApi";
import type { Job, JobHistoryItem, JobStatus, Region, RegionType } from "./jobStore";

export function normalizeJobStatus(status: BackendJobStatus | JobStatus): JobStatus {
  if (status === "created") return "created";
  if (status === "regions_pending") return "regions_pending";
  if (status === "queued") return "queued";
  if (status === "running") return "running";
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  return "exported";
}

function normalizeRegionType(value: string | undefined, fallback?: RegionType): RegionType {
  if (value === "text" || value === "diagram" || value === "mixed") {
    return value;
  }

  return fallback ?? "mixed";
}

function mapBackendRegion(region: BackendJob["regions"][number], fallback?: Region): Region {
  return {
    id: region.id,
    polygon: region.polygon ?? fallback?.polygon ?? [],
    type: normalizeRegionType(region.type, fallback?.type),
    order: region.order ?? fallback?.order ?? 1,
    selectionMode: region.selection_mode ?? fallback?.selectionMode ?? "manual",
    inputDevice: region.input_device ?? fallback?.inputDevice ?? undefined,
    warningLevel: region.warning_level ?? fallback?.warningLevel ?? "normal",
    autoDetectConfidence: region.auto_detect_confidence ?? fallback?.autoDetectConfidence ?? undefined,
    status: region.status,
    ocrText: region.ocr_text ?? undefined,
    explanation: region.explanation ?? undefined,
    mathml: region.mathml ?? undefined,
    problemMarkdown: region.problem_markdown ?? fallback?.problemMarkdown ?? undefined,
    explanationMarkdown: region.explanation_markdown ?? fallback?.explanationMarkdown ?? undefined,
    markdownVersion: region.markdown_version ?? fallback?.markdownVersion ?? undefined,
    verificationStatus: region.verification_status ?? fallback?.verificationStatus ?? undefined,
    verificationWarnings: region.verification_warnings ?? fallback?.verificationWarnings ?? undefined,
    cropUrl: resolveRuntimePath(region.crop_url),
    imageCropUrl: resolveRuntimePath(region.image_crop_url),
    styledImageUrl: resolveRuntimePath(region.styled_image_url),
    styledImageModel: region.styled_image_model ?? undefined,
    processingMs: region.processing_ms ?? undefined,
    success: region.success ?? undefined,
    errorReason: region.error_reason ?? undefined,
    wasCharged: region.was_charged ?? fallback?.wasCharged ?? false,
    ocrCharged: region.ocr_charged ?? fallback?.ocrCharged ?? false,
    imageCharged: region.image_charged ?? fallback?.imageCharged ?? false,
    explanationCharged: region.explanation_charged ?? fallback?.explanationCharged ?? false,
    chargedAt: region.charged_at ?? fallback?.chargedAt ?? undefined,
  };
}

/** 작업 카드에 필요한 파일명을 안전하게 정규화한다. */
function resolveJobFileName(
  jobId: string,
  fileName: string | null | undefined,
  imageUrl: string | null | undefined,
  fallback?: string
): string {
  return fileName ?? fallback ?? imageUrl?.split("/").pop() ?? `${jobId}.png`;
}

export function mapBackendJob(backend: BackendJob, local: Job | null): Job {
  const previousRegions = new Map(local?.regions.map((region) => [region.id, region]) ?? []);

  return {
    id: backend.job_id,
    fileName: resolveJobFileName(backend.job_id, backend.file_name, backend.image_url, local?.fileName),
    imageUrl: resolveRuntimePath(backend.image_url) ?? local?.imageUrl ?? "",
    imageWidth: backend.image_width ?? local?.imageWidth ?? 0,
    imageHeight: backend.image_height ?? local?.imageHeight ?? 0,
    status: normalizeJobStatus(backend.status),
    regions: backend.regions.map((region) => mapBackendRegion(region, previousRegions.get(region.id))),
    createdAt: backend.created_at ?? local?.createdAt ?? new Date().toISOString(),
    updatedAt: backend.updated_at ?? local?.updatedAt ?? backend.created_at ?? local?.createdAt ?? new Date().toISOString(),
    hwpxPath: resolveRuntimePath(backend.hwpx_export_path) ?? local?.hwpxPath,
    lastError: backend.last_error ?? local?.lastError,
  };
}

/** 백엔드 job summary를 워크스페이스 history 카드 모델로 변환한다. */
export function mapBackendJobSummary(summary: BackendJobSummary): JobHistoryItem {
  return {
    id: summary.job_id,
    fileName: resolveJobFileName(summary.job_id, summary.file_name, null),
    status: normalizeJobStatus(summary.status),
    createdAt: summary.created_at,
    updatedAt: summary.updated_at,
    regionCount: summary.region_count,
    hwpxReady: summary.hwpx_ready,
    lastError: summary.last_error ?? undefined,
  };
}
