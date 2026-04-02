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
      <header className="liquid-header-shell border-b-0">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <BrandLogo className="h-10 w-10 rounded-2xl" />
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">MathHWP</p>
              <p className="text-[15px] tracking-[-0.02em] text-foreground">문제 이미지 작업실</p>
            </div>
          </Link>

          <div className="flex items-center gap-2">
            {isAuthenticated && user ? (
              <>
                <div className="liquid-chip liquid-chip--accent hidden rounded-full px-3 py-1.5 text-[12px] text-muted-foreground sm:block">
                  <span className="flex items-center gap-2">
                    <span className="flex items-center gap-1.5">
                      <ImageIcon className="h-3.5 w-3.5" />
                      {`${user.credits}개 이미지 남음`}
                    </span>
                    {user.openAiConnected ? (
                      <span className="flex items-center gap-1.5 text-emerald-600">
                        <KeyRound className="h-3.5 w-3.5" />
                        OpenAI 연결됨
                      </span>
                    ) : null}
                  </span>
                </div>
                <Button variant="outline" onClick={() => navigate("/workspace")}>
                  내 작업실
                </Button>
                <Button
                  variant="ghost"
                  className="gap-2"
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
                <Button variant="ghost" onClick={() => navigate("/pricing")}>
                  가격
                </Button>
                <Button onClick={() => navigate("/login")}>로그인</Button>
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
