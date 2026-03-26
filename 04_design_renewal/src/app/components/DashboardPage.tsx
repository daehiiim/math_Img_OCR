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
  Loader2,
  FileDown,
  Cpu,
  Box,
  Workflow,
  Coins,
  TrendingUp,
  Zap,
} from "lucide-react";
import { getStatusConfig } from "../lib/jobPresentation";

export function DashboardPage() {
  const { jobs, deleteJob } = useJobs();
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1>작업 대시보드</h1>
          
        </div>
        <Button onClick={() => navigate("/new")} className="gap-2">
          <Upload className="w-4 h-4" />
          새 작업
        </Button>
      </div>

      {/* Credits Overview */}
      {user && (
        <Card className="mb-8 border-primary/20 bg-gradient-to-r from-primary/5 via-background to-background">
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
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {/* Remaining Credits */}
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                  <Coins className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <p className="text-[12px] text-muted-foreground mb-1">남은 이미지</p>
                  <p className="text-[24px]">{user.credits.toLocaleString()}</p>
                </div>
              </div>

              {/* Used Credits */}
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center shrink-0">
                  <TrendingUp className="w-6 h-6 text-amber-500" />
                </div>
                <div>
                  <p className="text-[12px] text-muted-foreground mb-1">사용한 이미지</p>
                  <p className="text-[24px]">{user.usedCredits.toLocaleString()}</p>
                </div>
              </div>

              {/* Action Button */}
              <div className="flex flex-col items-start gap-3 sm:items-end">
                {user.openAiConnected ? (
                  <div className="flex items-center gap-2 text-emerald-500">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="text-[14px]">OpenAI 연결됨</span>
                  </div>
                ) : null}
                <Button
                  onClick={() => navigate("/pricing")}
                  variant={user.credits <= 10 ? "default" : "outline"}
                  className="gap-2"
                >
                  <Coins className="w-4 h-4" />
                  {user.credits <= 10 ? "이미지 충전" : "이미지 추가"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[12px] text-muted-foreground">전체 작업</p>
                <p className="text-[28px] mt-1">{jobs.length}</p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Box className="w-5 h-5 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[12px] text-muted-foreground">처리 중</p>
                <p className="text-[28px] mt-1">
                  {jobs.filter((j) => j.status === "running").length}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[12px] text-muted-foreground">완료</p>
                <p className="text-[28px] mt-1">
                  {
                    jobs.filter(
                      (j) => j.status === "completed" || j.status === "exported"
                    ).length
                  }
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[12px] text-muted-foreground">총 영역</p>
                <p className="text-[28px] mt-1">
                  {jobs.reduce((acc, j) => acc + j.regions.length, 0)}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Layers className="w-5 h-5 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Overview */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Workflow className="w-4 h-4" />
            파이프라인 흐름
          </CardTitle>
          
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-0 overflow-x-auto pb-2">
            {[
              { step: "1", label: "이미지 업로드", desc: "POST /jobs", color: "bg-blue-500" },
              { step: "2", label: "영역 지정", desc: "PUT /jobs/{id}/regions", color: "bg-violet-500" },
              { step: "3", label: "파이프라인 실행", desc: "POST /jobs/{id}/run", color: "bg-amber-500" },
              { step: "4", label: "결과 조회", desc: "GET /jobs/{id}", color: "bg-emerald-500" },
              { step: "5", label: "HWPX 내보내기", desc: "POST /.../export/hwpx", color: "bg-rose-500" },
            ].map((item, i) => (
              <div key={item.step} className="flex items-center shrink-0">
                <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-accent/50 min-w-[160px]">
                  <div
                    className={`w-7 h-7 rounded-full ${item.color} text-white flex items-center justify-center text-[12px] shrink-0`}
                  >
                    {item.step}
                  </div>
                  <div>
                    <p className="text-[13px]">{item.label}</p>
                    
                  </div>
                </div>
                {i < 4 && (
                  <ArrowRight className="w-4 h-4 text-muted-foreground mx-1 shrink-0" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Job List */}
      <div className="mb-4 flex items-center justify-between">
        <h2>작업 목록</h2>
        <p className="text-[13px] text-muted-foreground">
          {jobs.length}개 작업
        </p>
      </div>

      {jobs.length === 0 ? (
        <Card>
          <CardContent className="py-16 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
              <FileImage className="w-7 h-7 text-muted-foreground" />
            </div>
            <h3 className="text-[15px] mb-1">작업이 없습니다</h3>
            <p className="text-[13px] text-muted-foreground mb-4">
              수학 문제 이미지를 업로드하여 첫 번째 작업을 시작하세요.
            </p>
            <Button onClick={() => navigate("/new")} variant="outline" className="gap-2">
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
              <Card
                key={job.id}
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/workspace/job/${job.id}`)}
              >
                <CardContent className="py-4">
                  <div className="flex items-center gap-4">
                    {/* Thumbnail */}
                    <div className="w-14 h-14 rounded-lg bg-muted overflow-hidden shrink-0">
                      <img
                        src={job.imageUrl}
                        alt={job.fileName}
                        className="w-full h-full object-cover"
                      />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-[14px] truncate">{job.fileName}</p>
                        <Badge variant={cfg.variant} className="shrink-0">
                          <StatusIcon
                            className={`w-3 h-3 ${
                              job.status === "running" ? "animate-spin" : ""
                            }`}
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

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/workspace/job/${job.id}`);
                        }}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteJob(job.id);
                        }}
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
