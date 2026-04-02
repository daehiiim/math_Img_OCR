import { Link, useLocation } from "react-router";
import {
  LayoutDashboard,
  Upload,
  UserRound,
} from "lucide-react";
import { BrandLogo } from "./BrandLogo";
import { cn } from "./ui/utils";

const navItems = [
  { path: "/workspace", label: "대시보드", icon: LayoutDashboard },
  { path: "/new", label: "새 작업", icon: Upload },
];

interface AppSidebarProps {
  onOpenAccount: () => void;
  isAccountOpen: boolean;
}

/** 작업실 왼쪽 사이드바의 브랜드와 주요 이동 메뉴를 렌더링한다. */
export function AppSidebar({ onOpenAccount, isAccountOpen }: AppSidebarProps) {
  const location = useLocation();

  return (
    <aside className="liquid-sidebar-shell flex min-h-full w-[17.5rem] shrink-0 flex-col rounded-[32px] border border-white/70 px-3 py-4 shadow-[0_28px_72px_-52px_rgba(86,118,164,0.42)]">
      <div className="liquid-chip flex items-center gap-3 rounded-[28px] px-3 py-3">
        <BrandLogo className="h-10 w-10 rounded-[22px]" />
        <div>
          <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Workspace</p>
          <h1 className="text-[15px] tracking-[-0.02em] text-foreground">MathHWP</h1>
        </div>
      </div>

      <div className="px-3 pt-5">
        <h2 className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">작업 탐색</h2>
        <p className="mt-2 text-[12px] leading-5 text-muted-foreground">
          대시보드와 새 작업 흐름을 한 컬럼에서 빠르게 오간다.
        </p>
      </div>

      <nav aria-label="작업 탐색" className="flex-1 px-1 pt-4">
        <ul className="space-y-0.5">
          {navItems.map((item) => {
            const isActive =
              item.path === "/workspace"
                ? location.pathname === "/workspace"
                : location.pathname.startsWith(item.path);
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  data-active={isActive}
                  className={cn(
                    "liquid-sidebar-link flex items-center gap-2.5 rounded-2xl px-3 py-2.5 text-[13px] transition-colors",
                    isActive ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
          <li className="pt-2">
            <button
              type="button"
              onClick={onOpenAccount}
              data-active={isAccountOpen}
              className={cn(
                "liquid-sidebar-link flex w-full items-center gap-2.5 rounded-2xl px-3 py-2.5 text-[13px] transition-colors",
                isAccountOpen ? "text-foreground" : "text-muted-foreground"
              )}
            >
              <UserRound className="w-4 h-4" />
              내 계정
            </button>
          </li>
        </ul>
      </nav>

      <div className="space-y-3 border-t border-white/60 px-3 pt-4">
        <div className="liquid-chip liquid-chip--accent rounded-[24px] px-3 py-3 text-[11px] text-muted-foreground">
          업로드부터 HWPX 내보내기까지 한 흐름으로 정리했습니다.
        </div>
        <div className="liquid-inline-note rounded-[24px] px-3 py-3 text-[11px] leading-5 text-muted-foreground">
          현재 화면의 상태는 오른쪽 본문 보드에서 이어집니다.
        </div>
      </div>
    </aside>
  );
}
