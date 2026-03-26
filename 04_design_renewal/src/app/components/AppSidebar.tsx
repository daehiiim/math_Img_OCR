import { Cpu, LayoutDashboard, Upload, UserRound } from "lucide-react";
import { Link, useLocation } from "react-router";

import { Button } from "./ui/button";
import { Separator } from "./ui/separator";
import { cn } from "./ui/utils";

const navItems = [
  { path: "/workspace", label: "대시보드", icon: LayoutDashboard },
  { path: "/new", label: "새 작업", icon: Upload },
];

interface AppSidebarProps {
  onOpenAccount: () => void;
  isAccountOpen: boolean;
}

/** 사이드바 링크 활성 상태를 현재 경로 기준으로 계산한다. */
function isActivePath(currentPath: string, targetPath: string) {
  return targetPath === "/workspace" ? currentPath === "/workspace" : currentPath.startsWith(targetPath);
}

/** 워크스페이스 좌측 내비게이션과 계정 진입 버튼을 공통 shell 패턴으로 렌더링한다. */
export function AppSidebar({ onOpenAccount, isAccountOpen }: AppSidebarProps) {
  const location = useLocation();

  return (
    <aside className="hidden w-72 flex-col border-r bg-background md:flex">
      <div className="flex items-center gap-3 px-5 py-5"><div className="flex size-10 items-center justify-center rounded-2xl bg-foreground text-background"><Cpu /></div><div><p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">MathHWP</p><h1 className="text-sm">워크스페이스</h1></div></div>
      <Separator />
      <nav className="flex-1 space-y-2 px-3 py-4">
        <p className="px-3 text-xs uppercase tracking-[0.2em] text-muted-foreground">메인</p>
        {navItems.map((item) => <Button key={item.path} asChild variant={isActivePath(location.pathname, item.path) ? "default" : "ghost"} className={cn("w-full justify-start", !isActivePath(location.pathname, item.path) && "text-muted-foreground")}><Link to={item.path}><item.icon data-icon="inline-start" />{item.label}</Link></Button>)}
        <Button type="button" variant={isAccountOpen ? "default" : "ghost"} className={cn("w-full justify-start", !isAccountOpen && "text-muted-foreground")} onClick={onOpenAccount}><UserRound data-icon="inline-start" />내 계정</Button>
      </nav>
      <div className="px-5 pb-5 text-xs text-muted-foreground">작업 상세와 HWPX 내보내기는 오른쪽 메인 패널에서 계속 이어집니다.</div>
    </aside>
  );
}
