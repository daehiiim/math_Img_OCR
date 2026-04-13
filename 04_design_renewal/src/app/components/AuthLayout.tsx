import { Link, Outlet, useLocation, useNavigate } from "react-router";
import { ImageIcon, KeyRound, LogOut, Settings } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { BrandLogo } from "./BrandLogo";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

/** 인증 관련 화면 공통 헤더와 본문 레이아웃을 렌더링한다. */
export function AuthLayout() {
  const navigate = useNavigate();
  const auth = useAuth();
  const { user, isAuthenticated, logout } = auth;
  const location = useLocation();
  const isLoginPage = location.pathname === "/login";

  return (
    <div className="liquid-shell liquid-shell--auth flex min-h-screen flex-col">
      <header
        className="liquid-header-shell sticky z-20 mx-auto w-[min(100%-1.5rem,1200px)] rounded-[32px] border border-white/70 px-4 py-4 shadow-[0_28px_72px_-48px_rgba(86,118,164,0.42)]"
        style={{
          marginTop: "calc(env(safe-area-inset-top) + 1rem)",
          top: "calc(env(safe-area-inset-top) + 1rem)",
        }}
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <Link to={isAuthenticated ? "/workspace" : "/"} className="flex items-center gap-2.5">
              <BrandLogo className="h-9 w-9 rounded-[22px]" />
              <div>
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">MathHWP</p>
                <p className="text-[14px] tracking-[-0.02em] text-foreground">
                  {isLoginPage ? "로그인" : "인증 허브"}
                </p>
              </div>
            </Link>
            <span className="liquid-chip liquid-chip--accent hidden rounded-full px-3 py-1.5 text-[12px] text-muted-foreground sm:inline-flex">
              인증 / 결제 / 계정
            </span>
          </div>

          {isAuthenticated && user && !isLoginPage ? (
            <>
              <div
                aria-label="인증 상태"
                className="liquid-chip liquid-chip--accent flex flex-wrap items-center gap-2 rounded-full px-4 py-2 text-[12px] text-muted-foreground"
              >
                <span className="flex items-center gap-1.5">
                  <ImageIcon className="h-3.5 w-3.5" />
                  <span className="text-foreground">{`${user.credits}개 이미지 남음`}</span>
                </span>
                {user.openAiConnected ? (
                  <span className="flex items-center gap-1.5 text-sky-700">
                    <KeyRound className="h-3.5 w-3.5" />
                    OpenAI 연결됨
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <KeyRound className="h-3.5 w-3.5" />
                    OpenAI 미연결
                  </span>
                )}
              </div>

              <div aria-label="주요 작업" className="flex flex-wrap items-center justify-start gap-2 lg:justify-end">
                <Button variant="outline" className="rounded-full px-4" onClick={() => navigate("/workspace")}>
                  내 작업실
                </Button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      aria-label="계정 메뉴 열기"
                      className="liquid-avatar-badge flex h-10 w-10 cursor-pointer items-center justify-center rounded-full text-[11px] text-white transition-shadow hover:ring-[3px] hover:ring-white/45"
                    >
                      {user.avatarInitials}
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    className="w-56 rounded-[24px] border border-white/80 p-2 shadow-[0_24px_48px_-28px_rgba(86,118,164,0.32)]"
                  >
                    <div className="px-3 py-2">
                      <p className="text-[13px] text-foreground">{user.name}</p>
                      <p className="text-[11px] text-muted-foreground">{user.email}</p>
                    </div>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/connect-openai" className="flex cursor-pointer items-center gap-2">
                        <Settings className="h-3.5 w-3.5" />
                        <span className="text-[13px]">설정</span>
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/pricing" className="flex cursor-pointer items-center gap-2">
                        <ImageIcon className="h-3.5 w-3.5" />
                        <span className="text-[13px]">이미지 구매</span>
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => {
                        void logout();
                        navigate("/");
                      }}
                      className="flex cursor-pointer items-center gap-2 text-red-600"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      <span className="text-[13px]">로그아웃</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </>
          ) : (
            <div aria-label="주요 작업" className="flex flex-wrap items-center justify-start gap-2 lg:justify-end">
              <Button variant="ghost" className="min-h-11 rounded-full px-4" onClick={() => navigate("/pricing")}>
                가격
              </Button>
              <Button className="min-h-11 rounded-full px-4" onClick={() => navigate("/login")}>
                로그인
              </Button>
            </div>
          )}
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
        <Outlet />
      </main>

      <footer className="px-4 pb-6 text-center text-[11px] text-muted-foreground">
        MathHWP &middot; AI 기반 수학 이미지를 HWPX로 변환
      </footer>
    </div>
  );
}
