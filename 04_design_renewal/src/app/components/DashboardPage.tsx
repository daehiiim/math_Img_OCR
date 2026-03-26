import { Box, CheckCircle2, Cpu, Layers, Upload } from "lucide-react";
import { useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { useJobs } from "../context/JobContext";
import { getStatusConfig } from "../lib/jobPresentation";
import { StatusPanel } from "./shared/StatusPanel";
import { JobListItemCard } from "./shared/JobListItemCard";
import { PageIntro } from "./shared/PageIntro";
import { UserCreditPill } from "./shared/UserCreditPill";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";

/** 대시보드 상단 통계 카드 하나를 렌더링한다. */
function DashboardStatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: typeof Box;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between pt-6">
        <div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl">{value}</p></div>
        <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon /></div>
      </CardContent>
    </Card>
  );
}

/** 작업 대시보드 화면을 shared presentation component 기준으로 렌더링한다. */
export function DashboardPage() {
  const { jobs, deleteJob } = useJobs();
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 lg:p-8">
      <PageIntro title="작업 대시보드" description="잔여 크레딧, 작업 진행 현황, 최근 작업을 한 화면에서 관리합니다." actions={<Button onClick={() => navigate("/new")}><Upload data-icon="inline-start" />새 작업</Button>} />
      {user ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{user.openAiConnected ? "OCR·해설은 연결한 OpenAI API key를 사용하고, 이미지 생성은 크레딧을 사용합니다." : "OCR·해설과 이미지 생성을 실행하려면 크레딧이 필요합니다."}</p>
          <UserCreditPill credits={user.credits} usedCredits={user.usedCredits} openAiConnected={user.openAiConnected} actionLabel={user.credits <= 10 ? "이미지 충전" : "이미지 추가"} onAction={() => navigate("/pricing")} />
        </div>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardStatCard label="전체 작업" value={jobs.length} icon={Box} />
        <DashboardStatCard label="처리 중" value={jobs.filter((job) => job.status === "running").length} icon={Cpu} />
        <DashboardStatCard label="완료" value={jobs.filter((job) => job.status === "completed" || job.status === "exported").length} icon={CheckCircle2} />
        <DashboardStatCard label="총 영역" value={jobs.reduce((total, job) => total + job.regions.length, 0)} icon={Layers} />
      </div>
      <div className="space-y-4">
        <div className="flex items-end justify-between gap-4"><div><h2>최근 작업</h2><p className="text-sm text-muted-foreground">최근 생성한 작업부터 바로 이어서 확인할 수 있습니다.</p></div><p className="text-sm text-muted-foreground">{jobs.length}개 작업</p></div>
        {jobs.length === 0 ? <StatusPanel title="작업이 없습니다" description="수학 문제 이미지를 업로드하여 첫 번째 작업을 시작하세요." tone="default" primaryAction={{ label: "이미지 업로드", href: "/new", variant: "outline" }} /> : <div className="space-y-3">{jobs.map((job) => { const config = getStatusConfig(job.status); return <JobListItemCard key={job.id} fileName={job.fileName} imageUrl={job.imageUrl} regionCount={job.regions.length} createdLabel={new Date(job.createdAt).toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} jobIdLabel={`${job.id.slice(0, 16)}...`} statusLabel={config.label} statusVariant={config.variant} statusIcon={config.icon} isRunning={job.status === "running"} onOpen={() => navigate(`/workspace/job/${job.id}`)} onDelete={() => deleteJob(job.id)} />; })}</div>}
      </div>
    </div>
  );
}
