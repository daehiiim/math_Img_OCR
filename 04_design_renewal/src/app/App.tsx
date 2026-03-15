import { useMemo } from "react";
import { RouterProvider, createBrowserRouter } from "react-router";
import { AuthProvider } from "./context/AuthContext";
import { Toaster } from "./components/ui/sonner";
import { Layout } from "./components/Layout";
import { AuthLayout } from "./components/AuthLayout";
import { DashboardPage } from "./components/DashboardPage";
import { NewJobPage } from "./components/NewJobPage";
import { JobDetailPage } from "./components/JobDetailPage";
import { NotFoundPage } from "./components/NotFoundPage";
import { LoginPage } from "./components/LoginPage";
import { ChatGptConnectionPage } from "./components/ChatGptConnectionPage";
import { PricingPage } from "./components/PricingPage";
import { PaymentPage } from "./components/PaymentPage";

// Wrapper component that provides AuthContext to all routes
function AppWrapper() {
  const router = useMemo(
    () =>
      createBrowserRouter([
        // Auth & onboarding pages (centered layout, no sidebar)
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
          path: "/connect-chatgpt",
          Component: AuthLayout,
          children: [{ index: true, Component: ChatGptConnectionPage }],
        },
        // OCR workspace (sidebar layout)
        {
          path: "/",
          Component: Layout,
          children: [
            { index: true, Component: DashboardPage },
            { path: "new", Component: NewJobPage },
            { path: "job/:jobId", Component: JobDetailPage },
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
      <AppWrapper />
      <Toaster />
    </AuthProvider>
  );
}