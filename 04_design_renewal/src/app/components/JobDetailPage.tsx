import { useParams, useNavigate } from "react-router";
import { useJobs } from "../context/JobContext";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { RegionEditor } from "./RegionEditor";
import { ResultsViewer } from "./ResultsViewer";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { useState, useCallback, useEffect } from "react";
import {
  ArrowLeft,
  Play,
  Download,
  CheckCircle2,
  Loader2,
  Clock,
  Layers,
  FileDown,
  AlertCircle,
  Sparkles,
  FileText,
  Copy,
  Check,
} from "lucide-react";
import type { JobStatus, Region } from "../store/jobStore";
import { copyToClipboard } from "../utils/clipboard";

const statusSteps: { key: JobStatus; label: string }[] = [
  { key: "regions_pending", label: "영역 대기" },
  { key: "regions_saved", label: "영역 저장" },
  { key: "running", label: "처리 중" },
  { key: "completed", label: "완료" },
  { key: "exported", label: "내보내기" },
];

function getStepIndex(status: JobStatus) {
  return statusSteps.findIndex((s) => s.key === status);
}

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { getJob, saveRegions, runPipeline, exportHwpx } = useJobs();
  const { consumeCredit, user } = useAuth();
  const navigate = useNavigate();
  const [isRunning, setIsRunning] = useState(false);
  const [copied, setCopied] = useState(false);

  const job = getJob(jobId || "");

  // Calculate progress for running state
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!job) return;
    if (job.status === "running") {
      const total = job.regions.length;
      const completed = job.regions.filter((r) => r.status === "completed").length;
      setProgress(total > 0 ? (completed / total) * 100 : 0);
    } else if (job.status === "completed" || job.status === "exported") {
      setProgress(100);
    } else {
      setProgress(0);
    }
  }, [job]);

  const handleSaveRegions = useCallback(
    (regions: Region[]) => {
      if (jobId) saveRegions(jobId, regions);
    },
    [jobId, saveRegions]
  );

  const handleRun = useCallback(async () => {
    if (!jobId) return;

    const canProcess = Boolean(user?.openAiConnected || (user?.credits ?? 0) > 0);
    if (!canProcess) {
      toast.error("OpenAI 연결 또는 이미지 구매가 필요합니다", {
        description: "먼저 OpenAI API key를 연결하거나 이미지를 충전해주세요.",
      });
      navigate("/connect-openai");
      return;
    }

    setIsRunning(true);
    await runPipeline(jobId);
    consumeCredit(jobId);
    toast.success("OCR이 완료되었습니다", {
      description: user?.openAiConnected
        ? "사용자 OpenAI API key로 처리되었습니다."
        : "성공한 작업 1건에 대해 이미지 1개가 차감되었습니다.",
    });
    setIsRunning(false);
  }, [consumeCredit, jobId, navigate, runPipeline, user?.credits, user?.openAiConnected]);

  const handleExport = useCallback(() => {
    if (jobId) exportHwpx(jobId);
  }, [jobId, exportHwpx]);

  const copyPath = () => {
    if (job?.hwpxPath) {
      copyToClipboard(job.hwpxPath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!job) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto">
        <div className="text-center py-20">
          <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h2>작업을 찾을 수 없습니다</h2>
          <p className="text-muted-foreground text-[14px] mt-2">
            ID: {jobId}
          </p>
          <Button
            variant="outline"
            onClick={() => navigate("/workspace")}
            className="mt-4 gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            대시보드로 돌아가기
          </Button>
        </div>
      </div>
    );
  }

  const currentStep = getStepIndex(job.status);

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Button
          variant="ghost"
          size="icon"
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

      {/* Progress Steps */}
      <Card className="mb-6">
        <CardContent className="py-4">
          <div className="flex items-center gap-0">
            {statusSteps.map((step, i) => {
              const isActive = i === currentStep;
              const isDone = i < currentStep;
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
                      ) : isActive && job.status === "running" ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        i + 1
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
                  {i < statusSteps.length - 1 && (
                    <div
                      className={`h-px flex-1 mx-2 ${
                        i < currentStep ? "bg-emerald-500" : "bg-border"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
          {job.status === "running" && (
            <div className="mt-3">
              <Progress value={progress} className="h-1.5" />
              <p className="text-[11px] text-muted-foreground mt-1">
                {job.regions.filter((r) => r.status === "completed").length} / {job.regions.length} 영역 처리 완료
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Image + Region Editor */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step 1-2: Region Editor */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="w-4 h-4" />
                영역 지정
              </CardTitle>
              <CardDescription>
                이미지 위에 드래그하여 OCR 처리할 영역을 지정하세요.
                각 영역은 텍스트/도형/혼합 타입을 선택할 수 있습니다.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RegionEditor
                imageUrl={job.imageUrl}
                imageWidth={job.imageWidth}
                imageHeight={job.imageHeight}
                regions={job.regions}
                onSaveRegions={handleSaveRegions}
                disabled={
                  job.status === "running" ||
                  job.status === "completed" ||
                  job.status === "exported"
                }
              />
            </CardContent>
          </Card>

          {/* Step 4: Results */}
          {(job.status === "running" ||
            job.status === "completed" ||
            job.status === "exported") && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  처리 결과
                </CardTitle>
                <CardDescription>
                  각 영역별 OCR 텍스트, 벡터 SVG, 원본 데이터를 확인할 수 있습니다.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResultsViewer regions={job.regions} />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Actions Panel */}
        <div className="space-y-4">
          {/* Run Pipeline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-[14px] flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                파이프라인 실행
              </CardTitle>
            </CardHeader>
            <CardContent>
              {job.status === "regions_pending" && (
                <div className="text-center py-4">
                  <Clock className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-[13px] text-muted-foreground">
                    먼저 영역을 지정하고 저장하세요.
                  </p>
                </div>
              )}
              {job.status === "regions_saved" && (
                <Button
                  onClick={handleRun}
                  className="w-full gap-2"
                  disabled={isRunning}
                >
                  <Play className="w-4 h-4" />
                  파이프라인 실행
                </Button>
              )}
              {job.status === "running" && (
                <div className="text-center py-4">
                  <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-2" />
                  <p className="text-[13px]">처리 중...</p>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    {job.regions.filter((r) => r.status === "completed").length}/{job.regions.length} 영역 완료
                  </p>
                </div>
              )}
              {(job.status === "completed" || job.status === "exported") && (
                <div className="text-center py-4">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                  <p className="text-[13px] text-emerald-600">파이프라인 완료</p>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    모든 영역이 성공적으로 처리되었습니다.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Export */}
          <Card>
            <CardHeader>
              <CardTitle className="text-[14px] flex items-center gap-2">
                <FileDown className="w-4 h-4" />
                HWPX 내보내기
              </CardTitle>
            </CardHeader>
            <CardContent>
              {job.status !== "completed" && job.status !== "exported" ? (
                <div className="text-center py-4">
                  <p className="text-[13px] text-muted-foreground">
                    파이프라인 완료 후 내보내기가 가능합니다.
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
                      <code className="text-[11px] flex-1 truncate text-muted-foreground">
                        {job.hwpxPath}
                      </code>
                      <Button variant="ghost" size="icon" onClick={copyPath} className="shrink-0 h-6 w-6">
                        {copied ? (
                          <Check className="w-3 h-3 text-emerald-500" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </Button>
                    </div>
                  </div>
                  
                </div>
              ) : (
                <Button onClick={handleExport} className="w-full gap-2" variant="outline">
                  <Download className="w-4 h-4" />
                  HWPX 내보내기
                </Button>
              )}
            </CardContent>
          </Card>

          {/* API Reference */}
          <Card>
            <CardHeader>
              <CardTitle className="text-[14px]">API 참조</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[
                  { method: "POST", path: "/jobs", desc: "Job 생성", done: true },
                  {
                    method: "PUT",
                    path: `/jobs/{id}/regions`,
                    desc: "영역 저장",
                    done: currentStep >= 1,
                  },
                  {
                    method: "POST",
                    path: `/jobs/{id}/run`,
                    desc: "실행",
                    done: currentStep >= 3,
                  },
                  {
                    method: "GET",
                    path: `/jobs/{id}`,
                    desc: "조회",
                    done: currentStep >= 3,
                  },
                  {
                    method: "POST",
                    path: `/.../export/hwpx`,
                    desc: "내보내기",
                    done: currentStep >= 4,
                  },
                ].map((api) => (
                  <div
                    key={api.path}
                    className={`flex items-center gap-2 px-2 py-1.5 rounded text-[11px] ${
                      api.done ? "bg-emerald-50" : "bg-muted/30"
                    }`}
                  >
                    <Badge
                      variant={api.done ? "default" : "outline"}
                      className="text-[9px] px-1.5 py-0 shrink-0"
                    >
                      {api.method}
                    </Badge>
                    <span className="font-mono truncate flex-1">{api.path}</span>
                    {api.done && (
                      <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* JSON Schema sample */}
          
        </div>
      </div>
    </div>
  );
}
