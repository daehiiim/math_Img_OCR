import { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { AccountSheet } from "./AccountSheet";
import { AppSidebar } from "./AppSidebar";
import { useAuth } from "../context/AuthContext";

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
    <div className="liquid-shell liquid-shell--workspace flex h-screen overflow-hidden">
      <AppSidebar onOpenAccount={() => setIsAccountOpen(true)} isAccountOpen={isAccountOpen} />
      <AccountSheet open={isAccountOpen} onOpenChange={setIsAccountOpen} />
      <main className="relative flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
