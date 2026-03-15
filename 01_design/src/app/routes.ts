import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./components/DashboardPage";
import { NewJobPage } from "./components/NewJobPage";
import { JobDetailPage } from "./components/JobDetailPage";
import { NotFoundPage } from "./components/NotFoundPage";

export const router = createBrowserRouter([
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
]);
