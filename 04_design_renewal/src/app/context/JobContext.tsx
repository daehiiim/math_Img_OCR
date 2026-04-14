import React, { createContext, useContext } from "react";
import {
  useJobStore,
  type Job,
  type JobExecutionOptions,
  type JobHistoryItem,
  type Region,
} from "../store/jobStore";
import type { AutoDetectRegionsResult, RunPipelineResult } from "../api/jobApi";

interface JobContextType {
  jobs: Job[];
  jobHistory: JobHistoryItem[];
  createJob: (fileName: string, imageUrl: string, width: number, height: number, imageFile: File) => Promise<string>;
  loadJobHistory: () => Promise<void>;
  autoDetectRegions: (jobId: string) => Promise<AutoDetectRegionsResult>;
  saveRegions: (jobId: string, regions: Region[]) => Promise<void>;
  runPipeline: (jobId: string, options: JobExecutionOptions) => Promise<RunPipelineResult>;
  hydrateJob: (jobId: string) => Promise<Job>;
  exportHwpx: (jobId: string) => Promise<void>;
  deleteJob: (jobId: string) => Promise<void>;
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
