import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Check, Copy, Download, FileDown, FileText, Play } from "lucide-react";
import { useNavigate, useParams } from "react-router";

import { useAuth } from "../context/AuthContext";
import { useJobs } from "../context/JobContext";
import { calculateRequiredCredits } from "../lib/executionCredits";
import { getJobStepIndex, type ProgressJobStatus } from "../lib/jobPresentation";
import type { JobExecutionOptions, JobStatus, Region } from "../store/jobStore";
import { copyToClipboard } from "../utils/clipboard";
import { RegionEditor } from "./RegionEditor";
import { ResultsViewer } from "./ResultsViewer";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { ExecutionOptionsPanel } from "./shared/ExecutionOptionsPanel";
import { PipelineProgressHeader } from "./shared/PipelineProgressHeader";
import { RegionWorkspaceShell } from "./shared/RegionWorkspaceShell";
import { StatusPanel } from "./shared/StatusPanel";

const statusSteps: Array<{ key: ProgressJobStatus; label: string }> = [
  { key: "regions_pending", label: "영역 대기" },
  { key: "queued", label: "영역 저장" },
  { key: "running", label: "처리 중" },
  { key: "completed", label: "완료" },
  { key: "exported", label: "내보내기" },
];

const defaultExecutionOptions: JobExecutionOptions = {
  doOcr: true,
  doImageStylize: true,
  doExplanation: true,
};

/** 문제 또는 해설 텍스트가 있으면 내보내기 가능 영역으로 본다. */
function isExportableRegion(region: Region): boolean {
  return Boolean(region.problemMarkdown?.trim() || region.explanationMarkdown?.trim() || region.ocrText?.trim() || region.explanation?.trim());
}

/** 처리 중 또는 처리 완료 이후에만 결과 영역을 노출한다. */
function isResultVisible(status: JobStatus): boolean {
  return status === "running" || status === "completed" || status === "failed" || status === "exported";
}

/** 검증 경고 메시지 개수를 계산한다. */
function getVerificationWarningCount(regions: Region[]): number {
  return regions.reduce((total, region) => total + (region.verificationWarnings?.length ?? 0), 0);
}

/** 작업 상세의 상태별 실행 안내 문구를 렌더링한다. */
function JobExecutionFooter({
  status,
  exportableRegionCount,
  lastError,
}: {
  status: JobStatus;
  exportableRegionCount: number;
  lastError?: string;
}) {
  if (status === "created" || status === "regions_pending") {
    return <p className="text-center text-sm text-muted-foreground">먼저 영역을 지정하고 저장하세요.</p>;
  }

  if (status === "running") {
    return <p className="text-center text-sm text-muted-foreground">처리 중인 동안에는 실행 옵션을 잠시 잠급니다.</p>;
  }

  if (status === "failed") {
    return <p className="text-center text-sm text-muted-foreground">{exportableRegionCount > 0 ? `결과가 남은 ${exportableRegionCount}개 영역은 HWPX로 내보낼 수 있습니다.` : lastError || "오류 내용을 확인하세요."}</p>;
  }

  if (status === "completed" || status === "exported") {
    return <p className="text-center text-sm text-emerald-600">선택한 작업이 성공적으로 처리되었습니다.</p>;
  }

  return null;
}

/** HWPX 내보내기 결과 섹션을 렌더링한다. */
function ExportCard({
  canExportHwpx,
  copied,
  exportableRegionCount,
  hwpxPath,
  isExporting,
  status,
  onCopy,
  onExport,
}: {
  canExportHwpx: boolean;
  copied: boolean;
  exportableRegionCount: number;
  hwpxPath?: string;
  isExporting: boolean;
  status: JobStatus;
  onCopy: () => void;
  onExport: () => void;
}) {
  return (
    <Card>
      <CardHeader><CardTitle className="text-sm">HWPX 내보내기</CardTitle></CardHeader>
      <CardContent>
        {!canExportHwpx ? <p className="text-sm text-muted-foreground">{status === "failed" ? "문제 또는 해설 텍스트가 있는 영역이 있어야 내보낼 수 있습니다." : "문제 또는 해설이 생성된 뒤 내보내기가 가능합니다."}</p> : status === "exported" ? <div className="space-y-3"><div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3"><div className="mb-2 flex items-center gap-2 text-emerald-700"><Badge variant="secondary">내보내기 완료</Badge><span className="text-xs">{`${exportableRegionCount}개 영역 반영`}</span></div><div className="flex items-center gap-2 rounded border bg-background p-2"><code className="flex-1 truncate text-xs text-muted-foreground">{hwpxPath}</code><Button type="button" variant="ghost" size="icon" className="size-6" onClick={onCopy}>{copied ? <Check className="size-3 text-emerald-500" /> : <Copy className="size-3" />}</Button></div></div><Button type="button" variant="outline" className="w-full" disabled={isExporting} onClick={onExport}><Download data-icon="inline-start" />{isExporting ? "내보내는 중..." : "HWPX 다시 내보내기"}</Button></div> : <Button type="button" variant="outline" className="w-full" disabled={isExporting} onClick={onExport}><Download data-icon="inline-start" />{isExporting ? "내보내는 중..." : "HWPX 내보내기"}</Button>}
      </CardContent>
    </Card>
  );
}

/** 작업 상세 화면을 shared pattern 기준으로 정리하되 기존 실행 계약은 그대로 유지한다. */
export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { refreshProfile, user } = useAuth();
  const { getJob, saveRegions, runPipeline, hydrateJob, exportHwpx } = useJobs();
  const [isRunning, setIsRunning] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [progress, setProgress] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isHydratingJob, setIsHydratingJob] = useState(false);
  const [hasHydrationError, setHasHydrationError] = useState(false);
  const [draftRegions, setDraftRegions] = useState<Region[] | null>(null);
  const [executionOptions, setExecutionOptions] = useState<JobExecutionOptions>(defaultExecutionOptions);
  const job = getJob(jobId || "");
  const activeRegions = draftRegions ?? job?.regions ?? [];
  const requiredCredits = calculateRequiredCredits(executionOptions, Boolean(user?.openAiConnected), activeRegions);
  const hasSelectedAction = executionOptions.doOcr || executionOptions.doImageStylize || executionOptions.doExplanation;
  const exportableRegionCount = (job?.regions ?? []).filter(isExportableRegion).length;
  const verificationWarningCount = getVerificationWarningCount(job?.regions ?? []);
  const canExportHwpx = exportableRegionCount > 0 && (job?.status === "completed" || job?.status === "failed" || job?.status === "exported");

  useEffect(() => {
    if (!jobId || job || isHydratingJob || hasHydrationError) return;
    let cancelled = false;

    const restoreJob = async () => {
      setIsHydratingJob(true);
      try {
        await hydrateJob(jobId);
      } catch (error) {
        if (!cancelled) {
          setActionError(error instanceof Error ? error.message : "작업 정보를 불러오지 못했습니다.");
          setHasHydrationError(true);
        }
      } finally {
        if (!cancelled) setIsHydratingJob(false);
      }
    };

    void restoreJob();
    return () => {
      cancelled = true;
    };
  }, [hasHydrationError, hydrateJob, isHydratingJob, job, jobId]);

  useEffect(() => {
    if (job) {
      setDraftRegions(job.regions);
    }
  }, [job]);

  useEffect(() => {
    if (!job) return;
    if (job.status === "running") {
      const completed = job.regions.filter((region) => region.status === "completed").length;
      setProgress(job.regions.length > 0 ? (completed / job.regions.length) * 100 : 0);
      return;
    }
    setProgress(job.status === "completed" || job.status === "exported" ? 100 : 0);
  }, [job]);

  /** 실행 옵션 체크 상태를 변경한다. */
  const updateExecutionOption = useCallback((key: keyof JobExecutionOptions, checked: boolean) => {
    setExecutionOptions((prev) => ({ ...prev, [key]: checked }));
  }, []);

  const handleSaveRegions = useCallback(async (regions: Region[]) => {
    if (!jobId) return;
    setActionError(null);

    try {
      await saveRegions(jobId, regions);
      setDraftRegions(regions);
      toast.success("영역이 저장되었습니다.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "영역 저장 중 오류가 발생했습니다.";
      setActionError(message);
      toast.error(message);
      throw error;
    }
  }, [jobId, saveRegions]);

  const handleRun = useCallback(async () => {
    if (!jobId) return;
    if (!hasSelectedAction) {
      toast.error("실행할 작업을 하나 이상 선택하세요.");
      return;
    }
    if ((user?.credits ?? 0) < requiredCredits) {
      toast.error("선택한 작업을 실행하기 위한 크레딧이 부족합니다.", { description: "선택한 작업 기준으로 잔액을 먼저 확인합니다." });
      return;
    }

    setIsRunning(true);
    setActionError(null);

    try {
      const result = await runPipeline(jobId, executionOptions);
      await refreshProfile();
      if (result.status === "failed") {
        toast.error("일부 영역 처리에 실패했습니다.", { description: `성공 ${result.completed_count}개, 실패 ${result.failed_count}개, 차감 ${result.charged_count}크레딧` });
      } else {
        toast.success("선택한 파이프라인 실행이 완료되었습니다.", { description: `이번 실행 차감: ${result.charged_count}크레딧` });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "파이프라인 실행 중 오류가 발생했습니다.";
      setActionError(message);
      toast.error(message);
    } finally {
      setIsRunning(false);
    }
  }, [executionOptions, hasSelectedAction, jobId, refreshProfile, requiredCredits, runPipeline, user?.credits]);

  const handleExport = useCallback(async () => {
    if (!jobId) return;
    setIsExporting(true);
    setActionError(null);

    try {
      await exportHwpx(jobId);
      toast.success("HWPX 파일이 준비되었습니다.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "내보내기 중 오류가 발생했습니다.";
      setActionError(message);
      toast.error(message);
    } finally {
      setIsExporting(false);
    }
  }, [exportHwpx, jobId]);

  /** 내보낸 경로를 클립보드로 복사한다. */
  const copyPath = () => {
    if (!job?.hwpxPath) return;
    copyToClipboard(job.hwpxPath);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!job) {
    if (isHydratingJob) {
      return <div className="mx-auto max-w-5xl p-6 lg:p-8"><StatusPanel title="작업 정보를 불러오는 중..." description={`ID: ${jobId}`} tone="default" /></div>;
    }

    return <div className="mx-auto max-w-5xl p-6 lg:p-8"><StatusPanel title="작업을 찾을 수 없습니다" description={actionError ? `ID: ${jobId} · ${actionError}` : `ID: ${jobId}`} tone="warning" primaryAction={{ label: "대시보드로 돌아가기", href: "/workspace", variant: "outline" }} /></div>;
  }

  const currentStep = Math.max(getJobStepIndex(job.status, statusSteps), 0);
  const runButtonDisabled = isRunning || !hasSelectedAction || (user?.credits ?? 0) < requiredCredits;
  const selectionDisabled = job.status === "running";
  const runActionLabel = job.status === "queued" ? "파이프라인 실행" : job.status === "failed" ? "재시도" : undefined;
  const progressLabel = `${job.regions.filter((region) => region.status === "completed").length} / ${job.regions.length} 영역 처리 완료`;
  const executionSummary = draftRegions !== null && draftRegions !== job.regions ? "현재 편집 중인 draft 영역 기준 예상 차감입니다." : "선택한 문제 수 기준으로 잔액을 먼저 확인하고, 실행 후 실제 성공한 작업만 차감합니다.";
  const actionWarning = verificationWarningCount > 0 ? `검증 경고 ${verificationWarningCount}개가 있어 결과를 다시 확인하세요.` : undefined;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6 lg:p-8">
      <PipelineProgressHeader title={job.fileName} subtitle={`${new Date(job.createdAt).toLocaleString("ko-KR")} · ${job.imageWidth}×${job.imageHeight}px · ${job.regions.length}개 영역`} backHref="/workspace" backLabel="대시보드로 돌아가기" badge={`${job.id.slice(0, 20)}...`} steps={statusSteps} currentStep={currentStep} running={job.status === "running"} progress={progress} progressLabel={job.status === "running" ? progressLabel : undefined} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="space-y-6">
          <RegionWorkspaceShell title="영역 지정" description="이미지 위에 드래그하여 OCR 처리할 영역을 지정하세요. 저장된 여러 영역은 순서대로 하나의 HWPX 문서로 합쳐집니다." fileName={job.fileName} imageMeta={`${job.imageWidth}×${job.imageHeight}px`} regionCount={activeRegions.length} error={actionError} resetLabel="영역 다시 불러오기">
            <RegionEditor imageUrl={job.imageUrl} imageWidth={job.imageWidth} imageHeight={job.imageHeight} regions={draftRegions ?? job.regions} onSaveRegions={handleSaveRegions} onRegionsChange={setDraftRegions} disabled={job.status === "running" || job.status === "completed" || job.status === "exported"} />
          </RegionWorkspaceShell>
          {isResultVisible(job.status) ? <Card><CardHeader><CardTitle className="flex items-center gap-2"><FileText className="w-4 h-4" />처리 결과</CardTitle><CardDescription>각 영역별 OCR 텍스트, 문제 영역 크롭, 이미지 추출 원본, 이미지 생성 결과를 확인할 수 있습니다.</CardDescription></CardHeader><CardContent><ResultsViewer regions={job.regions} /></CardContent></Card> : null}
        </div>
        <div className="space-y-4">
          <ExecutionOptionsPanel title="파이프라인 실행" description="원하는 작업만 선택해서 실행할 수 있습니다." options={[{ id: "do-ocr", key: "doOcr", label: "문제 타이핑", description: "OCR과 수식 추출을 실행합니다.", disabled: selectionDisabled }, { id: "do-image-stylize", key: "doImageStylize", label: "이미지 생성", description: "문제 영역에서 이미지 추출 원본과 생성 결과를 만듭니다.", disabled: selectionDisabled }, { id: "do-explanation", key: "doExplanation", label: "해설 작성", description: "영역별 풀이 해설을 생성합니다.", disabled: selectionDisabled }]} values={executionOptions} requiredCredits={requiredCredits} summary={executionSummary} warning={actionWarning} actionLabel={runActionLabel} actionDisabled={runButtonDisabled} actionIcon={<Play data-icon="inline-start" />} footer={<JobExecutionFooter status={job.status} exportableRegionCount={exportableRegionCount} lastError={job.lastError} />} onToggle={updateExecutionOption} onAction={() => void handleRun()} />
          <ExportCard canExportHwpx={canExportHwpx} copied={copied} exportableRegionCount={exportableRegionCount} hwpxPath={job.hwpxPath} isExporting={isExporting} status={job.status} onCopy={copyPath} onExport={() => void handleExport()} />
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><FileDown className="w-4 h-4" />API 참조</CardTitle></CardHeader>
            <CardContent className="space-y-2">{[{ method: "POST", path: "/jobs", done: true }, { method: "PUT", path: "/jobs/{id}/regions", done: currentStep >= 1 }, { method: "POST", path: "/jobs/{id}/run", done: currentStep >= 2 }, { method: "GET", path: "/jobs/{id}", done: currentStep >= 2 }, { method: "POST", path: "/jobs/{id}/export/hwpx", done: currentStep >= 4 }].map((api) => <div key={api.path} className={`flex items-center gap-2 rounded px-2 py-1.5 text-xs ${api.done ? "bg-emerald-50" : "bg-muted/30"}`}><Badge variant={api.done ? "default" : "outline"} className="px-1.5 py-0 text-[9px]">{api.method}</Badge><span className="flex-1 truncate font-mono">{api.path}</span>{api.done ? <Check className="size-3 text-emerald-500" /> : null}</div>)}</CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
