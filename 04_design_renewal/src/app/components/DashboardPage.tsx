import { useNavigate } from "react-router";
import { useJobs } from "../context/JobContext";
import { useAuth } from "../context/AuthContext";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import {
  Upload,
  FileImage,
  Trash2,
  Eye,
  ArrowRight,
  Layers,
  Clock,
  CheckCircle2,
  Cpu,
  Box,
  Workflow,
  Coins,
  TrendingUp,
  Zap,
} from "lucide-react";
import { getStatusConfig } from "../lib/jobPresentation";

const pipelineSteps = [
  { step: "1", label: "이미지 업로드", desc: "POST /jobs", color: "bg-blue-500" },
  { step: "2", label: "영역 지정", desc: "PUT /jobs/{id}/regions", color: "bg-violet-500" },
  { step: "3", label: "파이프라인 실행", desc: "POST /jobs/{id}/run", color: "bg-amber-500" },
  { step: "4", label: "결과 조회", desc: "GET /jobs/{id}", color: "bg-emerald-500" },
  { step: "5", label: "HWPX 내보내기", desc: "POST /.../export/hwpx", color: "bg-rose-500" },
];

/** 워크스페이스 대시보드의 요약, 지표, 작업 목록을 생산성 우선 구조로 렌더링한다. */
export function DashboardPage() {
  const { jobs, deleteJob } = useJobs();
  const { user } = useAuth();
  const navigate = useNavigate();

  const completedJobs = jobs.filter(
    (job) => job.status === "completed" || job.status === "exported"
  ).length;
  const runningJobs = jobs.filter((job) => job.status === "running").length;
  const totalRegions = jobs.reduce((acc, job) => acc + job.regions.length, 0);

  return (
    <div className="liquid-workspace-page mx-auto max-w-7xl p-6 lg:p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1>작업 대시보드</h1>
        </div>
        <Button onClick={() => navigate("/new")} size="pill" className="gap-2">
          <Upload className="w-4 h-4" />
          새 작업
        </Button>
      </div>

      {user ? (
        <section className="mb-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[13px] font-semibold tracking-[0.18em] text-muted-foreground">상단 요약</h2>
            <span className="liquid-chip rounded-full px-3 py-1 text-[12px] text-muted-foreground">
              실시간 크레딧과 연결 상태
            </span>
          </div>
          <Card className="liquid-frost-panel--accent border-primary/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-primary" />
                남은 이미지
              </CardTitle>
              <CardDescription>
                {user.openAiConnected
                  ? "OCR·해설은 연결한 OpenAI API key를 사용하고, 이미지 생성은 크레딧을 사용합니다."
                  : "OCR·해설과 이미지 생성을 실행하려면 크레딧이 필요합니다."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(240px,280px)]">
                <div className="liquid-feature-row grid gap-3 rounded-[28px] p-4 sm:grid-cols-2">
                  <div className="flex items-center gap-4">
                    <div className="liquid-stat-orb flex h-12 w-12 shrink-0 items-center justify-center rounded-full">
                      <Coins className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <p className="mb-1 text-[12px] text-muted-foreground">남은 이미지</p>
                      <p className="text-[24px]">{user.credits.toLocaleString()}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="liquid-stat-orb flex h-12 w-12 shrink-0 items-center justify-center rounded-full">
                      <TrendingUp className="w-6 h-6 text-amber-600" />
                    </div>
                    <div>
                      <p className="mb-1 text-[12px] text-muted-foreground">사용한 이미지</p>
                      <p className="text-[24px]">{user.usedCredits.toLocaleString()}</p>
                    </div>
                  </div>
                </div>

                <div className="liquid-feature-row flex flex-col justify-between gap-4 rounded-[28px] p-4">
                  {user.openAiConnected ? (
                    <div className="flex items-center gap-2 text-sky-700">
                      <CheckCircle2 className="w-5 h-5" />
                      <span className="text-[14px]">OpenAI 연결됨</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Clock className="w-5 h-5" />
                      <span className="text-[14px]">OpenAI 미연결</span>
                    </div>
                  )}
                  <Button
                    onClick={() => navigate("/pricing")}
                    variant={user.credits <= 10 ? "default" : "glass"}
                    size="pill"
                    className="gap-2 self-start"
                  >
                    <Coins className="w-4 h-4" />
                    {user.credits <= 10 ? "이미지 충전" : "이미지 추가"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      ) : null}

      <section className="mb-8 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-[13px] font-semibold tracking-[0.18em] text-muted-foreground">핵심 지표</h2>
          <span className="text-[12px] text-muted-foreground">현재 작업 리듬을 한 줄로 요약합니다.</span>
        </div>
        <div className="liquid-feature-row grid gap-3 rounded-[32px] p-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="liquid-inline-note flex items-center justify-between rounded-[24px] px-4 py-4">
            <div>
              <p className="text-[12px] text-muted-foreground">전체 작업</p>
              <p className="mt-1 text-[28px]">{jobs.length}</p>
            </div>
            <div className="liquid-stat-orb flex h-10 w-10 items-center justify-center rounded-2xl">
              <Box className="w-5 h-5 text-primary" />
            </div>
          </div>
          <div className="liquid-inline-note flex items-center justify-between rounded-[24px] px-4 py-4">
            <div>
              <p className="text-[12px] text-muted-foreground">처리 중</p>
              <p className="mt-1 text-[28px]">{runningJobs}</p>
            </div>
            <div className="liquid-stat-orb flex h-10 w-10 items-center justify-center rounded-2xl">
              <Cpu className="w-5 h-5 text-amber-600" />
            </div>
          </div>
          <div className="liquid-inline-note flex items-center justify-between rounded-[24px] px-4 py-4">
            <div>
              <p className="text-[12px] text-muted-foreground">완료</p>
              <p className="mt-1 text-[28px]">{completedJobs}</p>
            </div>
            <div className="liquid-stat-orb flex h-10 w-10 items-center justify-center rounded-2xl">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            </div>
          </div>
          <div className="liquid-inline-note flex items-center justify-between rounded-[24px] px-4 py-4">
            <div>
              <p className="text-[12px] text-muted-foreground">총 영역</p>
              <p className="mt-1 text-[28px]">{totalRegions}</p>
            </div>
            <div className="liquid-stat-orb flex h-10 w-10 items-center justify-center rounded-2xl">
              <Layers className="w-5 h-5 text-blue-500" />
            </div>
          </div>
        </div>
      </section>

      <section className="mb-8 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-[13px] font-semibold tracking-[0.18em] text-muted-foreground">작업 흐름</h2>
          <span className="text-[12px] text-muted-foreground">업로드부터 내보내기까지 한 줄로 이어집니다.</span>
        </div>
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-center gap-0 overflow-x-auto pb-2">
              {pipelineSteps.map((item, index) => (
                <div key={item.step} className="flex shrink-0 items-center">
                  <div className="liquid-inline-note flex min-w-[180px] items-center gap-2 rounded-[22px] px-4 py-3">
                    <div
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] text-white ${item.color}`}
                    >
                      {item.step}
                    </div>
                    <div>
                      <p className="text-[13px]">{item.label}</p>
                      <p className="text-[11px] text-muted-foreground">{item.desc}</p>
                    </div>
                  </div>
                  {index < pipelineSteps.length - 1 ? (
                    <ArrowRight className="mx-1 h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : null}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-3">
        <div className="mb-4 flex items-center justify-between">
          <h2>작업 목록</h2>
          <p className="text-[13px] text-muted-foreground">{jobs.length}개 작업</p>
        </div>

        {jobs.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="liquid-stat-orb mb-4 flex h-16 w-16 items-center justify-center rounded-full">
                <FileImage className="w-7 h-7 text-muted-foreground" />
              </div>
              <h3 className="mb-1 text-[15px]">작업이 없습니다</h3>
              <p className="mb-4 text-[13px] text-muted-foreground">
                수학 문제 이미지를 업로드하여 첫 번째 작업을 시작하세요.
              </p>
              <Button onClick={() => navigate("/new")} variant="glass" size="pill" className="gap-2">
                <Upload className="w-4 h-4" />
                이미지 업로드
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => {
              const cfg = getStatusConfig(job.status);
              const StatusIcon = cfg.icon;

              return (
                <div
                  key={job.id}
                  className="liquid-feature-row rounded-[30px] p-2 transition-transform duration-200 hover:-translate-y-0.5"
                >
                  <div className="flex items-center gap-4 rounded-[24px] px-2 py-2">
                    <button
                      type="button"
                      aria-label={`${job.fileName} 작업 상세 보기`}
                      className="flex min-w-0 flex-1 items-center gap-4 rounded-[24px] text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/10"
                      onClick={() => navigate(`/workspace/job/${job.id}`)}
                    >
                      <div className="h-14 w-14 shrink-0 overflow-hidden rounded-[20px] bg-muted">
                        <img
                          src={job.imageUrl}
                          alt={job.fileName}
                          className="w-full h-full object-cover"
                        />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="mb-1 flex items-center gap-2">
                          <p className="truncate text-[14px]">{job.fileName}</p>
                          <Badge variant={cfg.variant} className="shrink-0 rounded-full">
                            <StatusIcon
                              className={`w-3 h-3 ${job.status === "running" ? "animate-spin" : ""}`}
                            />
                            {cfg.label}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-[12px] text-muted-foreground">
                          <span className="font-mono">{job.id.slice(0, 16)}...</span>
                          <span>{job.regions.length}개 영역</span>
                          <span>
                            {new Date(job.createdAt).toLocaleString("ko-KR", {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                      </div>
                    </button>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        type="button"
                        aria-label={`${job.fileName} 작업 보기`}
                        onClick={() => navigate(`/workspace/job/${job.id}`)}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        type="button"
                        aria-label={`${job.fileName} 작업 삭제`}
                        onClick={() => deleteJob(job.id)}
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
