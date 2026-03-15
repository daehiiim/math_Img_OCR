import { Navigate, Outlet, useLocation } from "react-router";
import { AppSidebar } from "./AppSidebar";
import { useAuth } from "../context/AuthContext";

export function Layout() {
  const { isAuthenticated, isLoading, prepareLogin } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    prepareLogin(`${location.pathname}${location.search}`);
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
