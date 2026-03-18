import React, { createContext, useContext } from "react";
import { useJobStore, type Job, type Region } from "../store/jobStore";

interface JobContextType {
  jobs: Job[];
  createJob: (fileName: string, imageUrl: string, width: number, height: number, imageFile: File) => Promise<string>;
  saveRegions: (jobId: string, regions: Region[]) => Promise<void>;
  runPipeline: (jobId: string) => Promise<void>;
  saveEditedSvg: (jobId: string, regionId: string, svg: string) => Promise<void>;
  loadRegionSvg: (jobId: string, regionId: string) => Promise<string>;
  hydrateJob: (jobId: string) => Promise<Job>;
  exportHwpx: (jobId: string) => Promise<void>;
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
