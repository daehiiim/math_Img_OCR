import { Menu } from "lucide-react";
import { useLocation } from "react-router";

import { WorkspaceNavList } from "./AppSidebar";
import { BrandLogo } from "./BrandLogo";
import { Button } from "./ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "./ui/sheet";

interface WorkspaceMobileMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenAccount: () => void;
  isAccountOpen: boolean;
}

/** 모바일 워크스페이스 탐색 메뉴를 시트 형태로 렌더링한다. */
export function WorkspaceMobileMenu({
  open,
  onOpenChange,
  onOpenAccount,
  isAccountOpen,
}: WorkspaceMobileMenuProps) {
  const location = useLocation();

  return (
    <>
      <Button
        type="button"
        variant="glass"
        size="icon"
        aria-label="워크스페이스 메뉴 열기"
        className="h-11 w-11 rounded-full"
        onClick={() => onOpenChange(true)}
      >
        <Menu className="h-5 w-5" />
      </Button>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" aria-describedby={undefined} className="w-full max-w-[22rem] border-l-0 p-0">
          <SheetHeader className="border-b border-white/55 px-5 pb-4 pt-5">
            <div className="flex items-center gap-3">
              <BrandLogo className="h-10 w-10 rounded-[22px]" />
              <div>
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Workspace</p>
                <SheetTitle>워크스페이스 메뉴</SheetTitle>
              </div>
            </div>
          </SheetHeader>
          <div className="px-5 pb-6 pt-5">
            <nav aria-label="모바일 작업 탐색">
              <WorkspaceNavList
                pathname={location.pathname}
                onNavigate={() => onOpenChange(false)}
                onOpenAccount={onOpenAccount}
                isAccountOpen={isAccountOpen}
                itemClassName="min-h-11 rounded-[20px] px-4 text-[14px]"
              />
            </nav>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
