import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileDown,
  Layers,
  Loader2,
} from "lucide-react";

import type { JobStatus } from "../store/jobStore";

export type JobBadgeVariant = "default" | "secondary" | "outline" | "destructive";
export type ProgressJobStatus = "regions_pending" | "queued" | "running" | "completed" | "exported";

interface StatusConfig {
  label: string;
  variant: JobBadgeVariant;
  icon: React.ComponentType<{ className?: string }>;
}

const STATUS_CONFIG: Record<JobStatus, StatusConfig> = {
  created: { label: "작업 생성", variant: "outline", icon: Clock },
  regions_pending: { label: "영역 대기", variant: "outline", icon: Clock },
  queued: { label: "영역 저장됨", variant: "secondary", icon: Layers },
  running: { label: "처리 중", variant: "default", icon: Loader2 },
  completed: { label: "완료", variant: "secondary", icon: CheckCircle2 },
  failed: { label: "실패", variant: "destructive", icon: AlertCircle },
  exported: { label: "내보내기 완료", variant: "default", icon: FileDown },
};

// 대시보드와 상세 화면에서 공통으로 사용하는 상태 표시 정보를 반환한다.
export function getStatusConfig(status: JobStatus): StatusConfig {
  return STATUS_CONFIG[status];
}

// 진행 단계 UI에 맞게 내부 상태를 정규화한다.
export function getJobProgressStatus(status: JobStatus): ProgressJobStatus {
  if (status === "created") {
    return "regions_pending";
  }

  if (status === "failed") {
    return "running";
  }

  return status;
}

// 상태를 진행 단계 배열 인덱스로 변환한다.
export function getJobStepIndex(
  status: JobStatus,
  steps: Array<{ key: ProgressJobStatus }>
): number {
  return steps.findIndex((step) => step.key === getJobProgressStatus(status));
}
