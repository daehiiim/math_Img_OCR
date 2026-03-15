import { useMemo } from "react";
import { RouterProvider, createBrowserRouter } from "react-router";
import { AuthProvider } from "./context/AuthContext";
import { JobProvider } from "./context/JobContext";
import { Toaster } from "./components/ui/sonner";
import { Layout } from "./components/Layout";
import { AuthLayout } from "./components/AuthLayout";
import { StudioLayout } from "./components/StudioLayout";
import { DashboardPage } from "./components/DashboardPage";
import { NewJobPage } from "./components/NewJobPage";
import { JobDetailPage } from "./components/JobDetailPage";
import { NotFoundPage } from "./components/NotFoundPage";
import { LoginPage } from "./components/LoginPage";
import { OpenAiConnectionPage } from "./components/OpenAiConnectionPage";
import { PricingPage } from "./components/PricingPage";
import { PaymentPage } from "./components/PaymentPage";
import { PublicHomePage } from "./components/PublicHomePage";

// Wrapper component that provides AuthContext to all routes
function AppWrapper() {
  const router = useMemo(
    () =>
      createBrowserRouter([
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
            { path: "job/:jobId", Component: JobDetailPage },
            { path: "*", Component: NotFoundPage },
          ],
        },
        {
          path: "*",
          Component: NotFoundPage,
        },
      ]),
    []
  );

  return <RouterProvider router={router} />;
}

export default function App() {
  return (
    <AuthProvider>
      <JobProvider>
        <AppWrapper />
      </JobProvider>
      <Toaster />
    </AuthProvider>
  );
}
