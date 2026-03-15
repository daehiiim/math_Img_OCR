import React, { createContext, useContext } from "react";
import { useJobStore, type Job, type Region } from "../store/jobStore";

interface JobContextType {
  jobs: Job[];
  createJob: (fileName: string, imageUrl: string, width: number, height: number) => string;
  saveRegions: (jobId: string, regions: Region[]) => void;
  runPipeline: (jobId: string) => Promise<void>;
  exportHwpx: (jobId: string) => void;
  deleteJob: (jobId: string) => void;
  getJob: (jobId: string) => Job | null;
}

const JobContext = createContext<JobContextType | null>(null);

export function JobProvider({ children }: { children: React.ReactNode }) {
  const store = useJobStore();
  return <JobContext.Provider value={store}>{children}</JobContext.Provider>;
}

export function useJobs() {
  const ctx = useContext(JobContext);
  if (!ctx) throw new Error("useJobs must be used within JobProvider");
  return ctx;
}
