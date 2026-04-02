import { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { AccountSheet } from "./AccountSheet";
import { AppSidebar } from "./AppSidebar";
import { useAuth } from "../context/AuthContext";

/** 인증된 워크스페이스 전용 셸과 사이드바 레이아웃을 구성한다. */
export function Layout() {
  const { isAuthenticated, isLoading, prepareLogin } = useAuth();
  const location = useLocation();
  const [isAccountOpen, setIsAccountOpen] = useState(false);

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    prepareLogin(`${location.pathname}${location.search}`);
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="liquid-shell liquid-shell--workspace min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] gap-3 p-3 lg:gap-4 lg:p-4">
        <AppSidebar onOpenAccount={() => setIsAccountOpen(true)} isAccountOpen={isAccountOpen} />
        <main className="min-w-0 flex-1 overflow-y-auto">
          <div className="liquid-page-shell min-h-full rounded-[32px] px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
            <Outlet />
          </div>
        </main>
      </div>
      <AccountSheet open={isAccountOpen} onOpenChange={setIsAccountOpen} />
    </div>
  );
}
