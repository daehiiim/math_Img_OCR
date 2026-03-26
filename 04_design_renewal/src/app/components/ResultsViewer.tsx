import { FileText } from "lucide-react";

import type { Region } from "../store/jobStore";
import { ResultRegionCard } from "./shared/ResultRegionCard";

interface ResultsViewerProps {
  regions: Region[];
}

/** 결과 영역 목록을 shared result card 조합으로 렌더링한다. */
export function ResultsViewer({ regions }: ResultsViewerProps) {
  if (regions.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        <FileText className="mx-auto mb-3 h-10 w-10 opacity-50" />
        <p className="text-sm">영역이 없습니다</p>
        <p className="text-xs">먼저 영역을 지정하고 파이프라인을 실행하세요.</p>
      </div>
    );
  }

  return <div className="space-y-4">{regions.map((region) => <ResultRegionCard key={region.id} region={region} />)}</div>;
}
