import { Link, useLocation } from "react-router";
import {
  LayoutDashboard,
  Upload,
  UserRound,
} from "lucide-react";
import { BrandLogo } from "./BrandLogo";
import { cn } from "./ui/utils";

export const workspaceNavItems = [
  { path: "/workspace", label: "대시보드", icon: LayoutDashboard },
  { path: "/new", label: "새 작업", icon: Upload },
];

interface WorkspaceNavListProps {
  pathname: string;
  onNavigate?: () => void;
  onOpenAccount: () => void;
  isAccountOpen: boolean;
  listClassName?: string;
  itemClassName?: string;
}

interface AppSidebarProps {
  onOpenAccount: () => void;
  isAccountOpen: boolean;
}

/** 현재 경로가 워크스페이스 탐색 항목과 일치하는지 계산한다. */
export function isWorkspaceNavItemActive(pathname: string, itemPath: string) {
  return itemPath === "/workspace" ? pathname === "/workspace" : pathname.startsWith(itemPath);
}

/** 워크스페이스 공용 탐색 링크와 계정 버튼 목록을 렌더링한다. */
export function WorkspaceNavList({
  pathname,
  onNavigate,
  onOpenAccount,
  isAccountOpen,
  listClassName,
  itemClassName,
}: WorkspaceNavListProps) {
  return (
    <ul className={cn("space-y-0.5", listClassName)}>
      {workspaceNavItems.map((item) => {
        const isActive = isWorkspaceNavItemActive(pathname, item.path);
        return (
          <li key={item.path}>
            <Link
              to={item.path}
              onClick={onNavigate}
              data-active={isActive}
              className={cn(
                "liquid-sidebar-link flex items-center gap-2.5 rounded-2xl px-3 py-2.5 text-[13px] transition-colors",
                isActive ? "text-foreground" : "text-muted-foreground",
                itemClassName
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          </li>
        );
      })}
      <li className="pt-2">
        <button
          type="button"
          onClick={() => {
            onNavigate?.();
            onOpenAccount();
          }}
          data-active={isAccountOpen}
          className={cn(
            "liquid-sidebar-link flex w-full items-center gap-2.5 rounded-2xl px-3 py-2.5 text-[13px] transition-colors",
            isAccountOpen ? "text-foreground" : "text-muted-foreground",
            itemClassName
          )}
        >
          <UserRound className="h-4 w-4" />
          내 계정
        </button>
      </li>
    </ul>
  );
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
        <WorkspaceNavList
          pathname={location.pathname}
          onOpenAccount={onOpenAccount}
          isAccountOpen={isAccountOpen}
        />
      </nav>
    </aside>
  );
}
