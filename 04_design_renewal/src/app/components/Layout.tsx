import { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { AccountSheet } from "./AccountSheet";
import { AppSidebar } from "./AppSidebar";
import { BrandLogo } from "./BrandLogo";
import { WorkspaceMobileMenu } from "./WorkspaceMobileMenu";
import { useAuth } from "../context/AuthContext";

/** 인증된 워크스페이스 전용 셸과 사이드바 레이아웃을 구성한다. */
export function Layout() {
  const { isAuthenticated, isLoading, prepareLogin } = useAuth();
  const location = useLocation();
  const [isAccountOpen, setIsAccountOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    prepareLogin(`${location.pathname}${location.search}`);
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="liquid-shell liquid-shell--workspace min-h-screen">
      <div
        className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-3 px-3 pb-3 lg:gap-4 lg:p-4"
        style={{ paddingTop: "calc(env(safe-area-inset-top) + 0.75rem)" }}
      >
        <header
          className="liquid-header-shell sticky z-20 flex items-center justify-between rounded-[28px] px-4 py-3 lg:hidden"
          style={{ top: "calc(env(safe-area-inset-top) + 0.75rem)" }}
        >
          <div className="flex items-center gap-3">
            <BrandLogo className="h-10 w-10 rounded-[22px]" />
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Workspace</p>
              <p className="text-[15px] tracking-[-0.02em] text-foreground">MathHWP</p>
            </div>
          </div>
          <WorkspaceMobileMenu
            open={isMobileMenuOpen}
            onOpenChange={setIsMobileMenuOpen}
            onOpenAccount={() => setIsAccountOpen(true)}
            isAccountOpen={isAccountOpen}
          />
        </header>

        <div className="flex min-h-0 flex-1 gap-3 lg:gap-4">
          <div className="hidden lg:block">
            <AppSidebar onOpenAccount={() => setIsAccountOpen(true)} isAccountOpen={isAccountOpen} />
          </div>
          <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
            <div className="liquid-page-shell min-h-full rounded-[32px] px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
      <AccountSheet open={isAccountOpen} onOpenChange={setIsAccountOpen} />
    </div>
  );
}
