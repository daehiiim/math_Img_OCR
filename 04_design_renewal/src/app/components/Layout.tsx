import { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "../context/AuthContext";
import { AccountSheet } from "./AccountSheet";
import { AppSidebar } from "./AppSidebar";

/** 인증된 워크스페이스 라우트에 공통 사이드바와 계정 시트를 연결한다. */
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
    <div className="flex min-h-screen overflow-hidden bg-muted/20">
      <AppSidebar onOpenAccount={() => setIsAccountOpen(true)} isAccountOpen={isAccountOpen} />
      <AccountSheet open={isAccountOpen} onOpenChange={setIsAccountOpen} />
      <main className="flex-1 overflow-y-auto"><Outlet /></main>
    </div>
  );
}
