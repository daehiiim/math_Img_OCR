import { Link, Outlet, useLocation, useNavigate } from "react-router";
import { ImageIcon, KeyRound, LogOut, Settings } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { BrandLogo } from "./BrandLogo";
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
      <header className="liquid-header-shell flex h-16 shrink-0 items-center justify-between px-5 sm:px-6">
        <Link to={isAuthenticated ? "/workspace" : "/"} className="flex items-center gap-2">
          <BrandLogo className="h-8 w-8 rounded-xl" />
          <span className="text-[14px] tracking-[-0.02em] text-foreground">MathHWP</span>
        </Link>

        {isAuthenticated && user && !isLoginPage && (
          <div className="flex items-center gap-3">
            <div className="liquid-chip liquid-chip--accent flex items-center gap-2 rounded-full px-3 py-1.5 text-[12px] text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <ImageIcon className="w-3 h-3" />
                <span className="text-foreground">{`${user.credits}개 이미지 남음`}</span>
              </span>
              {user.openAiConnected ? (
                <span className="flex items-center gap-1 text-emerald-700">
                  <KeyRound className="w-3 h-3" />
                  OpenAI 연결됨
                </span>
              ) : null}
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  aria-label="계정 메뉴 열기"
                  className="liquid-avatar-badge flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[11px] text-white transition-shadow hover:ring-[3px] hover:ring-white/45"
                >
                  {user.avatarInitials}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52 rounded-2xl p-2">
                <div className="px-3 py-2">
                  <p className="text-[13px] text-foreground">{user.name}</p>
                  <p className="text-[11px] text-muted-foreground">{user.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/connect-openai" className="flex items-center gap-2 cursor-pointer">
                    <Settings className="w-3.5 h-3.5" />
                    <span className="text-[13px]">설정</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/pricing" className="flex items-center gap-2 cursor-pointer">
                    <ImageIcon className="w-3.5 h-3.5" />
                    <span className="text-[13px]">이미지 구매</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => {
                    void logout();
                    navigate("/");
                  }}
                  className="flex items-center gap-2 text-red-600 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="text-[13px]">로그아웃</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
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
