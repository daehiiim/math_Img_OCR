import { Outlet } from "react-router";
import { AppSidebar } from "./AppSidebar";
import { JobProvider } from "../context/JobContext";

export function Layout() {
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
