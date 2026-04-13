import { useMemo } from "react";
import { Outlet, RouterProvider, createBrowserRouter } from "react-router";
import { AuthProvider } from "./context/AuthContext";
import { AdminProvider } from "./context/AdminContext";
import { JobProvider } from "./context/JobContext";
import { Toaster } from "./components/ui/sonner";
import { Layout } from "./components/Layout";
import { AuthLayout } from "./components/AuthLayout";
import { StudioLayout } from "./components/StudioLayout";
import { AdminDashboardPage } from "./components/AdminDashboardPage";
import { DashboardPage } from "./components/DashboardPage";
import { NewJobPage } from "./components/NewJobPage";
import { JobDetailPage } from "./components/JobDetailPage";
import { NotFoundPage } from "./components/NotFoundPage";
import { LoginPage } from "./components/LoginPage";
import { OpenAiConnectionPage } from "./components/OpenAiConnectionPage";
import { PricingPage } from "./components/PricingPage";
import { PaymentPage } from "./components/PaymentPage";
import { PublicHomePage } from "./components/PublicHomePage";
import { ClarityTracker } from "./components/ClarityTracker";
import { GoogleAnalyticsTracker } from "./components/GoogleAnalyticsTracker";
import { SeoManager } from "./components/SeoManager";

// 모든 브라우저 라우트에 전역 추적기를 공통 연결한다.
function TrackingLayout() {
  return (
    <>
      <SeoManager />
      <ClarityTracker />
      <GoogleAnalyticsTracker />
      <Outlet />
    </>
  );
}

// Wrapper component that provides AuthContext to all routes
function AppWrapper() {
  const router = useMemo(
    () =>
      createBrowserRouter([
        {
          Component: TrackingLayout,
          children: [
            {
              path: "/",
              Component: PublicHomePage,
            },
            {
              path: "/new",
              Component: StudioLayout,
              children: [{ index: true, Component: NewJobPage }],
            },
            // Auth & onboarding pages
            {
              path: "/login",
              Component: AuthLayout,
              children: [{ index: true, Component: LoginPage }],
            },
            {
              path: "/pricing",
              Component: AuthLayout,
              children: [{ index: true, Component: PricingPage }],
            },
            {
              path: "/payment/:planId",
              Component: AuthLayout,
              children: [{ index: true, Component: PaymentPage }],
            },
            {
              path: "/connect-openai",
              Component: AuthLayout,
              children: [{ index: true, Component: OpenAiConnectionPage }],
            },
            // OCR workspace (sidebar layout)
            {
              path: "/workspace",
              Component: Layout,
              children: [
                { index: true, Component: DashboardPage },
                { path: "admin", Component: AdminDashboardPage },
                { path: "job/:jobId", Component: JobDetailPage },
                { path: "*", Component: NotFoundPage },
              ],
            },
            { path: "*", Component: NotFoundPage },
          ],
        },
      ]),
    []
  );

  return <RouterProvider router={router} />;
}

export default function App() {
  return (
    <AuthProvider>
      <AdminProvider>
        <JobProvider>
          <AppWrapper />
        </JobProvider>
      </AdminProvider>
      <Toaster />
    </AuthProvider>
  );
}
