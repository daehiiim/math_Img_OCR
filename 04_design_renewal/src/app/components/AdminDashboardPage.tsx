import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import {
  AlertTriangle,
  Link2Off,
  RefreshCw,
  ShieldCheck,
  UserRound,
  LogOut,
  Clock3,
} from "lucide-react";

import { getAdminDashboardApi, type AdminDashboardResponse } from "../api/adminApi";
import { useAdmin } from "../context/AdminContext";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

/** ISO 시각을 운영 화면에 맞는 한국어 로컬 문자열로 포맷한다. */
function formatAdminDateTime(value?: string | null) {
  if (!value) {
    return "시각 없음";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "시각 없음";
  }

  return date.toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** 관리자 세션이 끊겼을 때 사용자 안내 후 워크스페이스로 돌린다. */
function isAdminSessionError(message: string) {
  return message.includes("관리자 세션이 만료") || message.includes("관리자 인증이 필요");
}

/** 운영자가 오늘 상태와 최근 사용자 실행 흐름을 한 화면에서 점검한다. */
export function AdminDashboardPage() {
  const navigate = useNavigate();
  const { adminSession, exitAdminMode } = useAdmin();
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const hasRedirectedRef = useRef(false);

  /** 세션이 없거나 만료되면 정리 후 워크스페이스로 복귀시킨다. */
  const redirectToWorkspace = useCallback((message: string) => {
    if (hasRedirectedRef.current) {
      return;
    }

    hasRedirectedRef.current = true;
    exitAdminMode();
    toast(message);
    navigate("/workspace", { replace: true });
  }, [exitAdminMode, navigate]);

  /** 최신 관리자 집계를 읽어 KPI와 최근 실행 목록 상태를 갱신한다. */
  const loadDashboard = useCallback(async () => {
    if (!adminSession) {
      redirectToWorkspace("관리자 재인증이 필요합니다.");
      return;
    }

    setIsRefreshing(true);
    setErrorMessage(null);

    try {
      const nextDashboard = await getAdminDashboardApi(adminSession.sessionToken);
      setDashboard(nextDashboard);
    } catch (error) {
      const message = error instanceof Error ? error.message : "관리자 대시보드를 불러오지 못했습니다.";
      if (isAdminSessionError(message)) {
        redirectToWorkspace(message);
        return;
      }
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [adminSession, redirectToWorkspace]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  /** 관리자 세션만 종료하고 일반 워크스페이스로 돌아간다. */
  const handleExitAdminMode = () => {
    exitAdminMode();
    navigate("/workspace");
  };

  if (!adminSession) {
    return null;
  }

  return (
    <div className="liquid-workspace-page mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
        <Card className="liquid-frost-panel--accent border-primary/10">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-primary" />
              관리자 대시보드
            </CardTitle>
            <CardDescription>
              오늘 장애 신호와 최근 사용자 실행 흐름을 빠르게 확인하는 운영 보드입니다.
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-5 sm:pb-6">
            <div className="flex flex-wrap items-center gap-2 text-[12px] text-muted-foreground">
              <Badge variant="secondary" className="rounded-full">
                수동 새로고침 기반
              </Badge>
              <span>생성 시각 {formatAdminDateTime(dashboard?.generated_at)}</span>
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="glass" size="pill" className="gap-2" onClick={() => void loadDashboard()}>
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            수동 새로고침
          </Button>
          <Button type="button" variant="outline" size="pill" className="gap-2" onClick={handleExitAdminMode}>
            <LogOut className="h-4 w-4" />
            관리자 세션 종료
          </Button>
        </div>
      </section>

      {errorMessage ? (
        <Card className="border-destructive/20 bg-destructive/5">
          <CardContent className="flex items-start gap-3 py-5">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <p className="text-[13px] leading-6 text-foreground">{errorMessage}</p>
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2">
        <Card className="liquid-feature-row border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              오늘 실패 작업 수
            </CardTitle>
            <CardDescription>KST 00:00 이후 실패로 끝난 OCR 작업 건수입니다.</CardDescription>
          </CardHeader>
          <CardContent className="pb-6">
            <p className="text-[40px] leading-none tracking-[-0.04em]">
              {dashboard?.failed_jobs_today ?? (isLoading ? "..." : 0)}
            </p>
          </CardContent>
        </Card>

        <Card className="liquid-feature-row border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link2Off className="h-5 w-5 text-rose-500" />
              OpenAI 호출 누락 건
            </CardTitle>
            <CardDescription>결과는 있는데 request id가 비어 있는 OCR·이미지 분석 영역 수입니다.</CardDescription>
          </CardHeader>
          <CardContent className="pb-6">
            <p className="text-[40px] leading-none tracking-[-0.04em]">
              {dashboard?.missing_openai_request_regions_today ?? (isLoading ? "..." : 0)}
            </p>
          </CardContent>
        </Card>
      </section>

      <section>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="h-5 w-5 text-primary/80" />
              사용자별 최근 실행
            </CardTitle>
            <CardDescription>사용자마다 최신 작업 1건만 추려서 최근 순으로 보여줍니다.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pb-5 sm:pb-6">
            {dashboard?.recent_user_runs?.length ? (
              dashboard.recent_user_runs.map((run) => (
                <div
                  key={run.job_id}
                  className="liquid-inline-note grid gap-3 rounded-[24px] px-4 py-4 sm:grid-cols-[minmax(0,1fr)_auto]"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-[15px] text-foreground">{run.user_label}</p>
                      <Badge variant="outline" className="rounded-full font-mono text-[11px]">
                        {run.user_id_suffix}
                      </Badge>
                      <Badge variant="secondary" className="rounded-full">
                        {run.job_status}
                      </Badge>
                    </div>
                    <p className="mt-2 truncate text-[13px] text-foreground">{run.file_name}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-[12px] text-muted-foreground">
                      <span className="font-mono">{run.job_id}</span>
                      <span>{run.region_count}개 영역</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
                    <Clock3 className="h-4 w-4 shrink-0" />
                    <span>{formatAdminDateTime(run.ran_at)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="liquid-inline-note rounded-[24px] px-4 py-5 text-[13px] text-muted-foreground">
                {isLoading ? "최근 실행 목록을 불러오는 중입니다." : "표시할 최근 실행 작업이 없습니다."}
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
