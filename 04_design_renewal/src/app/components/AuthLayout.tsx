import { Link, Outlet, useLocation, useNavigate } from "react-router";
import { ImageIcon, KeyRound, LogOut, Settings } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

export function AuthLayout() {
  const navigate = useNavigate();
  const auth = useAuth();
  const { user, isAuthenticated, logout } = auth;
  const location = useLocation();
  const isLoginPage = location.pathname === "/login";

  return (
    <div className="min-h-screen bg-[#fafafa] flex flex-col">
      {/* Header */}
      <header className="h-14 border-b border-black/[0.06] bg-white flex items-center justify-between px-5 shrink-0">
        <Link to={isAuthenticated ? "/workspace" : "/"} className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-[#111] flex items-center justify-center">
            <span className="text-[11px] text-white tracking-tight">M</span>
          </div>
          <span className="text-[14px] tracking-[-0.01em] text-[#111]">Math OCR</span>
        </Link>

        {isAuthenticated && user && !isLoginPage && (
          <div className="flex items-center gap-3">
            {/* Credits indicator */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#f4f4f5] text-[12px] text-[#71717a]">
              <span className="flex items-center gap-1.5">
                <ImageIcon className="w-3 h-3" />
                <span className="text-[#111]">{`${user.credits}개 이미지 남음`}</span>
              </span>
              {user.openAiConnected ? (
                <span className="flex items-center gap-1 text-emerald-600">
                  <KeyRound className="w-3 h-3" />
                  OpenAI 연결됨
                </span>
              ) : null}
            </div>

            {/* Avatar dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-white flex items-center justify-center text-[11px] cursor-pointer hover:ring-2 hover:ring-indigo-200 transition-shadow">
                  {user.avatarInitials}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <div className="px-3 py-2">
                  <p className="text-[13px] text-[#111]">{user.name}</p>
                  <p className="text-[11px] text-[#71717a]">{user.email}</p>
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

      {/* Content */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <Outlet />
      </main>

      {/* Minimal footer */}
      <footer className="py-4 text-center text-[11px] text-[#a1a1aa]">
        Math OCR &middot; AI 기반 수학 이미지를 HWPX로 변환
      </footer>
    </div>
  );
}
