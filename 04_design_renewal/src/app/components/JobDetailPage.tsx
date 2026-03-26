import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { toast } from "sonner";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FileDown,
  FileText,
  Layers,
  Loader2,
  Play,
  Sparkles,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { useJobs } from "../context/JobContext";
import { calculateRequiredCredits } from "../lib/executionCredits";
import { type ProgressJobStatus, getJobStepIndex } from "../lib/jobPresentation";
import type { JobExecutionOptions, JobStatus, Region } from "../store/jobStore";
import { copyToClipboard } from "../utils/clipboard";
import { ResultsViewer } from "./ResultsViewer";
import { RegionEditor } from "./RegionEditor";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Checkbox } from "./ui/checkbox";
import { Label } from "./ui/label";
import { Progress } from "./ui/progress";

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

function isResultVisible(status: JobStatus): boolean {
  return status === "running" || status === "completed" || status === "failed" || status === "exported";
}

/** 문제 또는 해설 텍스트가 있으면 내보내기 가능 영역으로 본다. */
function isExportableRegion(region: Region): boolean {
  return Boolean(
    region.problemMarkdown?.trim() ||
      region.explanationMarkdown?.trim() ||
      region.ocrText?.trim() ||
      region.explanation?.trim()
  );
}

/** 검증 경고 메시지 개수를 계산한다. */
function getVerificationWarningCount(regions: Region[]): number {
  return regions.reduce((total, region) => total + (region.verificationWarnings?.length ?? 0), 0);
}

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
  const requiredCredits = calculateRequiredCredits(
    executionOptions,
    Boolean(user?.openAiConnected),
    activeRegions
  );
  const hasSelectedAction =
    executionOptions.doOcr || executionOptions.doImageStylize || executionOptions.doExplanation;
  const exportableRegionCount = (job?.regions ?? []).filter(isExportableRegion).length;
  const verificationWarningCount = getVerificationWarningCount(job?.regions ?? []);
  const canExportHwpx =
    exportableRegionCount > 0 &&
    (job?.status === "completed" || job?.status === "failed" || job?.status === "exported");

  useEffect(() => {
    if (!jobId || job || isHydratingJob || hasHydrationError) {
      return;
    }

    let cancelled = false;

    const restoreJob = async () => {
      setIsHydratingJob(true);

      try {
        await hydrateJob(jobId);
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "작업 정보를 불러오지 못했습니다.";
          setActionError(message);
          setHasHydrationError(true);
        }
      } finally {
        if (!cancelled) {
          setIsHydratingJob(false);
        }
      }
    };

    void restoreJob();

    return () => {
      cancelled = true;
    };
  }, [hasHydrationError, hydrateJob, isHydratingJob, job, jobId]);

  useEffect(() => {
    if (!job) {
      return;
    }

    setDraftRegions(job.regions);
  }, [job]);

  useEffect(() => {
    if (!job) {
      return;
    }

    if (job.status === "running") {
      const total = job.regions.length;
      const completed = job.regions.filter((region) => region.status === "completed").length;
      setProgress(total > 0 ? (completed / total) * 100 : 0);
      return;
    }

    if (job.status === "completed" || job.status === "exported") {
      setProgress(100);
      return;
    }

    setProgress(0);
  }, [job]);

  /** 실행 옵션 체크 상태를 변경한다. */
  const updateExecutionOption = useCallback((key: keyof JobExecutionOptions, checked: boolean) => {
    setExecutionOptions((prev) => ({
      ...prev,
      [key]: checked,
    }));
  }, []);

  const handleSaveRegions = useCallback(
    async (regions: Region[]) => {
      if (!jobId) {
        return;
      }

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
    },
    [jobId, saveRegions]
  );

  const handleRun = useCallback(async () => {
    if (!jobId) {
      return;
    }

    if (!hasSelectedAction) {
      toast.error("실행할 작업을 하나 이상 선택하세요.");
      return;
    }

    if ((user?.credits ?? 0) < requiredCredits) {
      toast.error("선택한 작업을 실행하기 위한 크레딧이 부족합니다.", {
        description: "선택한 작업 기준으로 잔액을 먼저 확인합니다.",
      });
      return;
    }

    setIsRunning(true);
    setActionError(null);

    try {
      const result = await runPipeline(jobId, executionOptions);
      await refreshProfile();

      if (result.status === "failed") {
        toast.error("일부 영역 처리에 실패했습니다.", {
          description: `성공 ${result.completed_count}개, 실패 ${result.failed_count}개, 차감 ${result.charged_count}크레딧`,
        });
      } else {
        toast.success("선택한 파이프라인 실행이 완료되었습니다.", {
          description: `이번 실행 차감: ${result.charged_count}크레딧`,
        });
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
    if (!jobId) {
      return;
    }

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
    if (!job?.hwpxPath) {
      return;
    }

    copyToClipboard(job.hwpxPath);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!job) {
    if (isHydratingJob) {
      return (
        <div className="p-6 lg:p-8 max-w-5xl mx-auto">
          <div className="text-center py-20">
            <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto mb-4" />
            <h2>작업 정보를 불러오는 중...</h2>
            <p className="text-muted-foreground text-[14px] mt-2">ID: {jobId}</p>
          </div>
        </div>
      );
    }

    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto">
        <div className="text-center py-20">
          <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h2>작업을 찾을 수 없습니다</h2>
          <p className="text-muted-foreground text-[14px] mt-2">ID: {jobId}</p>
          {actionError ? <p className="text-[14px] text-destructive mt-2">{actionError}</p> : null}
          <Button variant="outline" onClick={() => navigate("/workspace")} className="mt-4 gap-2">
            <ArrowLeft className="w-4 h-4" />
            대시보드로 돌아가기
          </Button>
        </div>
      </div>
    );
  }

  const currentStep = Math.max(getJobStepIndex(job.status, statusSteps), 0);
  const runButtonDisabled = isRunning || !hasSelectedAction || (user?.credits ?? 0) < requiredCredits;
  const selectionDisabled = job.status === "running";

  return (
    <div className="liquid-workspace-page mx-auto max-w-5xl p-6 lg:p-8">
      <div className="flex items-center gap-3 mb-6">
        <Button
          variant="ghost"
          size="icon"
          type="button"
          aria-label="대시보드로 돌아가기"
          onClick={() => navigate("/workspace")}
        >
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="truncate">{job.fileName}</h1>
            <Badge variant="outline" className="shrink-0 text-[10px] font-mono">
              {job.id.slice(0, 20)}...
            </Badge>
          </div>
          <p className="text-[13px] text-muted-foreground">
            {new Date(job.createdAt).toLocaleString("ko-KR")} · {job.imageWidth}×{job.imageHeight}px · {job.regions.length}개 영역
          </p>
        </div>
      </div>

      <Card className="mb-6">
        <CardContent className="py-4">
          <div className="flex items-center gap-0">
            {statusSteps.map((step, index) => {
              const isActive = index === currentStep;
              const isDone = index < currentStep;

              return (
                <div key={step.key} className="flex items-center flex-1">
                  <div className="flex items-center gap-2 flex-1">
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-[11px] transition-colors ${
                        isDone
                          ? "bg-emerald-500 text-white"
                          : isActive
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4" />
                      ) : isActive && (job.status === "running" || isRunning) ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        index + 1
                      )}
                    </div>
                    <span
                      className={`text-[12px] hidden sm:inline ${
                        isActive ? "text-foreground" : "text-muted-foreground"
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {index < statusSteps.length - 1 ? (
                    <div
                      className={`h-px flex-1 mx-2 ${
                        index < currentStep ? "bg-emerald-500" : "bg-border"
                      }`}
                    />
                  ) : null}
                </div>
              );
            })}
          </div>
          {job.status === "running" ? (
            <div className="mt-3">
              <Progress value={progress} className="h-1.5" />
              <p className="text-[11px] text-muted-foreground mt-1">
                {job.regions.filter((region) => region.status === "completed").length} / {job.regions.length} 영역 처리 완료
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="w-4 h-4" />
                영역 지정
              </CardTitle>
              <CardDescription>
                이미지 위에 드래그하여 OCR 처리할 영역을 지정하세요.
                저장된 여러 영역은 순서대로 하나의 HWPX 문서로 합쳐집니다.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RegionEditor
                imageUrl={job.imageUrl}
                imageWidth={job.imageWidth}
                imageHeight={job.imageHeight}
                regions={draftRegions ?? job.regions}
                onSaveRegions={handleSaveRegions}
                onRegionsChange={setDraftRegions}
                disabled={job.status === "running" || job.status === "completed" || job.status === "exported"}
              />
            </CardContent>
          </Card>

          {isResultVisible(job.status) ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  처리 결과
                </CardTitle>
                <CardDescription>
                  각 영역별 OCR 텍스트, 문제 영역 크롭, 이미지 추출 원본, 이미지 생성 결과를 확인할 수 있습니다.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResultsViewer regions={job.regions} />
              </CardContent>
            </Card>
          ) : null}
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-[14px] flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                파이프라인 실행
              </CardTitle>
              <CardDescription>
                원하는 작업만 선택해서 실행할 수 있습니다.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                {[
                  {
                    id: "do-ocr",
                    key: "doOcr" as const,
                    label: "문제 타이핑",
                    description: "OCR과 수식 추출을 실행합니다.",
                  },
                  {
                    id: "do-image-stylize",
                    key: "doImageStylize" as const,
                    label: "이미지 생성",
                    description: "문제 영역에서 이미지 추출 원본과 생성 결과를 만듭니다.",
                  },
                  {
                    id: "do-explanation",
                    key: "doExplanation" as const,
                    label: "해설 작성",
                    description: "영역별 풀이 해설을 생성합니다.",
                  },
                ].map((option) => (
                  <div key={option.id} className="liquid-inline-note rounded-[20px] p-3">
                    <div className="flex items-start gap-3">
                      <Checkbox
                        id={option.id}
                        checked={executionOptions[option.key]}
                        disabled={selectionDisabled}
                        onCheckedChange={(checked) => updateExecutionOption(option.key, checked === true)}
                        aria-label={option.label}
                      />
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <Label htmlFor={option.id}>{option.label}</Label>
                        </div>
                        <p className="text-[12px] text-muted-foreground">{option.description}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

                <div className="liquid-inline-note rounded-[22px] p-3 text-[12px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-muted-foreground">이번 실행 최대 차감 예정</span>
                    <span className="font-semibold text-foreground">{requiredCredits} 크레딧</span>
                  </div>
                  <p className="mt-1 text-muted-foreground">
                    선택한 문제 수 기준으로 잔액을 먼저 확인하고, 실행 후 실제 성공한 작업만 차감합니다.
                  </p>
                  {verificationWarningCount > 0 ? (
                    <p className="mt-1 text-amber-700">검증 경고 {verificationWarningCount}개가 있어 결과를 다시 확인하세요.</p>
                  ) : null}
                  {draftRegions !== null && draftRegions !== job.regions ? (
                    <p className="mt-1 text-amber-700">
                      현재 편집 중인 draft 기준 예상 차감입니다.
                    </p>
                  ) : null}
                </div>

              {(job.status === "created" || job.status === "regions_pending") ? (
                <div className="text-center py-2">
                  <Clock className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-[13px] text-muted-foreground">먼저 영역을 지정하고 저장하세요.</p>
                </div>
              ) : null}

              {job.status === "queued" ? (
                <Button onClick={() => void handleRun()} className="w-full gap-2" disabled={runButtonDisabled}>
                  <Play className="w-4 h-4" />
                  파이프라인 실행
                </Button>
              ) : null}

              {job.status === "running" ? (
                <div className="text-center py-4">
                  <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-2" />
                  <p className="text-[13px]">처리 중...</p>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    {job.regions.filter((region) => region.status === "completed").length}/{job.regions.length} 영역 완료
                  </p>
                </div>
              ) : null}

              {job.status === "failed" ? (
                <div className="space-y-3 py-2">
                  <div className="text-center">
                    <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
                    <p className="text-[13px] text-destructive">일부 영역 처리 중 오류가 발생했습니다.</p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      {exportableRegionCount > 0
                        ? `결과가 남은 ${exportableRegionCount}개 영역은 HWPX로 내보낼 수 있습니다.`
                        : job.lastError || "오류 내용을 확인하세요."}
                    </p>
                  </div>
                  <Button onClick={() => void handleRun()} className="w-full gap-2" variant="outline" disabled={runButtonDisabled}>
                    <Play className="w-4 h-4" />
                    재시도
                  </Button>
                </div>
              ) : null}

              {(job.status === "completed" || job.status === "exported") ? (
                <div className="text-center py-4">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                  <p className="text-[13px] text-emerald-600">파이프라인 완료</p>
                  <p className="text-[11px] text-muted-foreground mt-1">선택한 작업이 성공적으로 처리되었습니다.</p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-[14px] flex items-center gap-2">
                <FileDown className="w-4 h-4" />
                {isExporting ? "내보내는 중..." : "HWPX 내보내기"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!canExportHwpx ? (
                <div className="text-center py-4">
                  <p className="text-[13px] text-muted-foreground">
                    {job.status === "failed"
                      ? "문제 또는 해설 텍스트가 있는 영역이 있어야 내보낼 수 있습니다."
                      : "문제 또는 해설이 생성된 뒤 내보내기가 가능합니다."}
                  </p>
                </div>
              ) : job.status === "exported" ? (
                <div className="space-y-3">
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span className="text-[13px] text-emerald-700">내보내기 완료</span>
                    </div>
                    <div className="bg-white rounded border p-2 flex items-center gap-2">
                      <code className="text-[11px] flex-1 truncate text-muted-foreground">{job.hwpxPath}</code>
                      <Button
                        variant="ghost"
                        size="icon"
                        type="button"
                        aria-label={copied ? "내보낸 경로 복사 완료" : "내보낸 경로 복사"}
                        onClick={copyPath}
                        className="shrink-0 h-6 w-6"
                      >
                        {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      </Button>
                    </div>
                  </div>
                  <Button
                    onClick={() => void handleExport()}
                    className="w-full gap-2"
                    variant="outline"
                    disabled={isExporting}
                  >
                    <Download className="w-4 h-4" />
                    {isExporting ? "내보내는 중..." : "HWPX 다시 내보내기"}
                  </Button>
                </div>
              ) : (
                <Button onClick={() => void handleExport()} className="w-full gap-2" variant="outline" disabled={isExporting}>
                  <Download className="w-4 h-4" />
                  {isExporting ? "내보내는 중..." : "HWPX 내보내기"}
                </Button>
              )}
            </CardContent>
          </Card>

          {actionError ? (
            <Card>
              <CardContent className="py-3">
                <p className="text-[12px] text-destructive">{actionError}</p>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle className="text-[14px]">API 참조</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[
                  { method: "POST", path: "/jobs", done: true },
                  { method: "PUT", path: "/jobs/{id}/regions", done: currentStep >= 1 },
                  { method: "POST", path: "/jobs/{id}/run", done: currentStep >= 2 },
                  { method: "GET", path: "/jobs/{id}", done: currentStep >= 2 },
                  { method: "POST", path: "/jobs/{id}/export/hwpx", done: currentStep >= 4 },
                ].map((api) => (
                  <div
                    key={api.path}
                    className={`flex items-center gap-2 px-2 py-1.5 rounded text-[11px] ${
                      api.done ? "bg-emerald-50" : "bg-muted/30"
                    }`}
                  >
                    <Badge variant={api.done ? "default" : "outline"} className="text-[9px] px-1.5 py-0 shrink-0">
                      {api.method}
                    </Badge>
                    <span className="font-mono truncate flex-1">{api.path}</span>
                    {api.done ? <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" /> : null}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
