// Mock store for Math OCR MVP-1 Job management
import { useState, useCallback } from "react";

export type RegionType = "text" | "diagram" | "mixed";

export interface Region {
  id: string;
  polygon: number[][];
  type: RegionType;
  order: number;
  status?: "pending" | "running" | "completed";
  ocrText?: string;
  svgData?: string;
}

export type JobStatus =
  | "regions_pending"
  | "regions_saved"
  | "running"
  | "completed"
  | "exported";

export interface Job {
  id: string;
  fileName: string;
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  status: JobStatus;
  regions: Region[];
  createdAt: string;
  hwpxPath?: string;
}

// Mock OCR results
const MOCK_OCR_TEXTS: Record<string, string> = {
  text: "다음 이차방정식의 근을 구하시오.\n\nx² - 5x + 6 = 0\n\n풀이:\n(x-2)(x-3) = 0\nx = 2 또는 x = 3",
  diagram:
    "[도형 인식]\n삼각형 ABC\nAB = 5cm, BC = 4cm, AC = 3cm\n∠C = 90°\n넓이 = 6cm²",
  mixed:
    "다음 그림에서 삼각형 ABC의 넓이를 구하시오.\n[도형: 직각삼각형]\nAB = 5, BC = 4, CA = 3\n넓이 = (1/2) × 3 × 4 = 6",
};

function generateMockSvg(polygon: number[][], regionId: string): string {
  const points = polygon.map((p) => `${p[0]},${p[1]}`).join(" ");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 700">
  <polygon points="${points}" fill="none" stroke="#3b82f6" stroke-width="2"/>
  <text x="${polygon[0][0] + 10}" y="${polygon[0][1] + 20}" fill="#3b82f6" font-size="14">${regionId}</text>
</svg>`;
}

let jobCounter = 0;

export function useJobStore() {
  const [jobs, setJobs] = useState<Job[]>([]);

  const createJob = useCallback(
    (fileName: string, imageUrl: string, width: number, height: number) => {
      jobCounter += 1;
      const job: Job = {
        id: `job_${Date.now()}_${jobCounter}`,
        fileName,
        imageUrl,
        imageWidth: width,
        imageHeight: height,
        status: "regions_pending",
        regions: [],
        createdAt: new Date().toISOString(),
      };
      setJobs((prev) => [job, ...prev]);
      return job.id;
    },
    []
  );

  const saveRegions = useCallback((jobId: string, regions: Region[]) => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === jobId
          ? {
              ...j,
              regions: regions.map((r) => ({ ...r, status: "pending" })),
              status: "regions_saved",
            }
          : j
      )
    );
  }, []);

  const runPipeline = useCallback(
    (jobId: string): Promise<void> => {
      return new Promise((resolve) => {
        let regionCount = 0;

        setJobs((prev) => {
          const updated = prev.map((j) => {
            if (j.id !== jobId) return j;
            regionCount = j.regions.length;
            return {
              ...j,
              status: "running" as const,
              regions: j.regions.map((r) => ({
                ...r,
                status: "running" as const,
              })),
            };
          });
          return updated;
        });

        // Use setTimeout to let state settle, then get regionCount
        setTimeout(() => {
          if (regionCount === 0) {
            resolve();
            return;
          }

          let processed = 0;

          const processNext = () => {
            if (processed >= regionCount) {
              setJobs((prev) =>
                prev.map((j) =>
                  j.id === jobId ? { ...j, status: "completed" } : j
                )
              );
              resolve();
              return;
            }

            const regionIndex = processed;
            setTimeout(() => {
              setJobs((prev) =>
                prev.map((j) => {
                  if (j.id !== jobId) return j;
                  const newRegions = [...j.regions];
                  const region = newRegions[regionIndex];
                  if (region) {
                    newRegions[regionIndex] = {
                      ...region,
                      status: "completed",
                      ocrText:
                        MOCK_OCR_TEXTS[region.type] || MOCK_OCR_TEXTS.mixed,
                      svgData: generateMockSvg(region.polygon, region.id),
                    };
                  }
                  return { ...j, regions: newRegions };
                })
              );
              processed += 1;
              processNext();
            }, 800 + Math.random() * 400);
          };

          processNext();
        }, 50);
      });
    },
    []
  );

  const exportHwpx = useCallback((jobId: string) => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === jobId
          ? {
              ...j,
              status: "exported",
              hwpxPath: `runtime/jobs/${jobId}/exports/${jobId}.hwpx`,
            }
          : j
      )
    );
  }, []);

  const deleteJob = useCallback((jobId: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== jobId));
  }, []);

  const getJob = useCallback(
    (jobId: string) => {
      return jobs.find((j) => j.id === jobId) || null;
    },
    [jobs]
  );

  return { jobs, createJob, saveRegions, runPipeline, exportHwpx, deleteJob, getJob };
}