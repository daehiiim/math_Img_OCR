import type { BackendJob, BackendJobStatus } from "../api/jobApi";
import { resolveRuntimePath } from "../api/jobApi";
import type { Job, JobStatus, Region, RegionType } from "./jobStore";

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
    status: region.status,
    ocrText: region.ocr_text ?? undefined,
    explanation: region.explanation ?? undefined,
    mathml: region.mathml ?? undefined,
    cropUrl: resolveRuntimePath(region.crop_url),
    imageCropUrl: resolveRuntimePath(region.image_crop_url),
    styledImageUrl: resolveRuntimePath(region.styled_image_url),
    styledImageModel: region.styled_image_model ?? undefined,
    processingMs: region.processing_ms ?? undefined,
    success: region.success ?? undefined,
    errorReason: region.error_reason ?? undefined,
    wasCharged: region.was_charged ?? fallback?.wasCharged ?? false,
    chargedAt: region.charged_at ?? fallback?.chargedAt ?? undefined,
  };
}

export function mapBackendJob(backend: BackendJob, local: Job | null): Job {
  const previousRegions = new Map(local?.regions.map((region) => [region.id, region]) ?? []);
  const fileName =
    backend.file_name ??
    local?.fileName ??
    backend.image_url?.split("/").pop() ??
    `${backend.job_id}.png`;

  return {
    id: backend.job_id,
    fileName,
    imageUrl: resolveRuntimePath(backend.image_url) ?? local?.imageUrl ?? "",
    imageWidth: backend.image_width ?? local?.imageWidth ?? 0,
    imageHeight: backend.image_height ?? local?.imageHeight ?? 0,
    status: normalizeJobStatus(backend.status),
    regions: backend.regions.map((region) => mapBackendRegion(region, previousRegions.get(region.id))),
    createdAt: local?.createdAt ?? new Date().toISOString(),
    hwpxPath: resolveRuntimePath(backend.hwpx_export_path) ?? local?.hwpxPath,
    lastError: backend.last_error ?? local?.lastError,
  };
}
