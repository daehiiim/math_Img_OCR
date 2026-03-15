import { Outlet, Navigate } from "react-router";
import { AppSidebar } from "./AppSidebar";
import { JobProvider } from "../context/JobContext";
import { useAuth } from "../context/AuthContext";

export function Layout() {
  const { isAuthenticated, user } = useAuth();

  // Not logged in → redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Logged in but no credits and no ChatGPT → redirect to pricing
  if (user && user.credits <= 0 && !user.chatGptConnected) {
    return <Navigate to="/pricing" replace />;
  }

  return (
    <JobProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        <AppSidebar />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </JobProvider>
  );
}
