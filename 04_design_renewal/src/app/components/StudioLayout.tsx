import { Link, Outlet, useNavigate } from "react-router";
import { ImageIcon, KeyRound, LogOut } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { BrandLogo } from "./BrandLogo";
import { Button } from "./ui/button";

/** 공개 작업실 화면의 상단 헤더와 본문 레이아웃을 렌더링한다. */
export function StudioLayout() {
  const navigate = useNavigate();
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <div className="liquid-shell liquid-shell--studio min-h-screen">
      <header
        className="liquid-header-shell sticky z-20 mx-auto w-[min(100%-1.5rem,1200px)] rounded-[32px] border border-white/70 px-4 py-4 shadow-[0_28px_72px_-48px_rgba(86,118,164,0.42)]"
        style={{
          marginTop: "calc(env(safe-area-inset-top) + 1rem)",
          top: "calc(env(safe-area-inset-top) + 1rem)",
        }}
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-3">
              <BrandLogo className="h-10 w-10 rounded-[24px]" />
              <div>
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">MathHWP</p>
                <p className="text-[15px] tracking-[-0.02em] text-foreground">문제 이미지 작업실</p>
              </div>
            </Link>
            <span className="liquid-chip liquid-chip--accent hidden rounded-full px-3 py-1.5 text-[12px] text-muted-foreground sm:inline-flex">
              공개 작업실
            </span>
          </div>

          <div
            aria-label="작업 상태"
            className="liquid-chip liquid-chip--accent flex flex-wrap items-center gap-2 rounded-full px-4 py-2 text-[12px] text-muted-foreground"
          >
            {isAuthenticated && user ? (
              <>
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
              </>
            ) : (
              <span className="text-foreground">로그인하면 작업 상태를 이어서 볼 수 있습니다.</span>
            )}
          </div>

          <div aria-label="주요 작업" className="flex flex-wrap items-center justify-start gap-2 lg:justify-end">
            {isAuthenticated && user ? (
              <>
                <Button variant="outline" className="min-h-11 rounded-full px-4" onClick={() => navigate("/workspace")}>
                  내 작업실
                </Button>
                <Button
                  variant="ghost"
                  className="min-h-11 rounded-full px-4"
                  onClick={() => {
                    void logout();
                    navigate("/");
                  }}
                >
                  <LogOut className="h-4 w-4" />
                  로그아웃
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" className="min-h-11 rounded-full px-4" onClick={() => navigate("/pricing")}>
                  가격
                </Button>
                <Button className="min-h-11 rounded-full px-4" onClick={() => navigate("/login")}>
                  로그인
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
