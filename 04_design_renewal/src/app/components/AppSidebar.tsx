import { Link, useLocation } from "react-router";
import {
  LayoutDashboard,
  Upload,
  Cpu,
  UserRound,
} from "lucide-react";
import { cn } from "./ui/utils";

const navItems = [
  { path: "/workspace", label: "대시보드", icon: LayoutDashboard },
  { path: "/new", label: "새 작업", icon: Upload },
];

interface AppSidebarProps {
  onOpenAccount: () => void;
  isAccountOpen: boolean;
}

export function AppSidebar({ onOpenAccount, isAccountOpen }: AppSidebarProps) {
  const location = useLocation();

  return (
    <aside className="liquid-sidebar-shell flex min-h-screen w-64 flex-col">
      <div className="border-b border-white/55 p-5">
        <div className="flex items-center gap-2.5">
          <div className="liquid-logo-mark flex h-8 w-8 items-center justify-center rounded-xl text-primary-foreground">
            <Cpu className="w-4 h-4 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-[15px]">MathHWP</h1>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3">
        <p className="text-[11px] text-muted-foreground px-3 mb-2 uppercase tracking-wider">
          메인
        </p>
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
          <li>
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

      <div className="border-t border-white/55 p-4">
        <div className="liquid-inline-note rounded-2xl px-3 py-3 text-[11px] text-muted-foreground">
          업로드부터 HWPX 내보내기까지 한 흐름으로 정리했습니다.
        </div>
      </div>
    </aside>
  );
}
