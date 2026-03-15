import { Link, Outlet, useNavigate } from "react-router";
import { ImageIcon, KeyRound, LogOut } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/button";

export function StudioLayout() {
  const navigate = useNavigate();
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <div className="min-h-screen bg-[#fcfaf6]">
      <header className="border-b border-black/5 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#171717] text-white">
              M
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-[#8b8177]">Math OCR</p>
              <p className="text-[15px] tracking-[-0.02em] text-[#171717]">문제 이미지 작업실</p>
            </div>
          </Link>

          <div className="flex items-center gap-2">
            {isAuthenticated && user ? (
              <>
                <div className="hidden rounded-full border border-black/5 bg-[#f7f3ec] px-3 py-1.5 text-[12px] text-[#5c564f] sm:block">
                  {user.openAiConnected ? (
                    <span className="flex items-center gap-1.5">
                      <KeyRound className="h-3.5 w-3.5 text-emerald-600" />
                      OpenAI 연결됨
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <ImageIcon className="h-3.5 w-3.5" />
                      {user.credits}개 이미지 남음
                    </span>
                  )}
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

      <main className="mx-auto max-w-6xl px-5 py-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
