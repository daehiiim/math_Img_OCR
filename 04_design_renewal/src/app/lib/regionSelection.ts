import type { Region, SelectionMode } from "../store/jobStore";

export const AUTO_FULL_RISK_MESSAGE =
  "영역을 지정하지 않으면 이미지 전체를 자동 인식하지만, 배경·여백·여러 문항이 함께 잡혀 정확도가 낮아질 수 있습니다. 정확한 결과가 필요하면 직접 영역을 지정하세요.";

export const AUTO_FULL_LOW_CONFIDENCE_MESSAGE =
  "자동 전체 인식 결과의 신뢰도가 낮을 수 있습니다. 직접 영역을 지정하면 더 정확할 수 있습니다.";

/** 현재 편집 상태가 수동 영역인지 자동 전체 인식인지 계산한다. */
export function getSelectionMode(regions: Region[]): SelectionMode {
  if (regions.length === 0) {
    return "none";
  }
  return regions.some((region) => region.selectionMode !== "auto_full") ? "manual" : "auto_full";
}


/** 사용자가 직접 그린 수동 영역이 하나라도 있는지 계산한다. */
export function hasUserDrawnRegion(regions: Region[]): boolean {
  return getSelectionMode(regions) === "manual";
}


/** 자동 전체 인식 결과인지 판단한다. */
export function isAutoFullRegion(region: Region): boolean {
  return region.selectionMode === "auto_full";
}


/** 자동 전체 인식 결과가 빈약하면 재지정을 유도한다. */
export function isLowConfidenceAutoFullRegion(region: Region): boolean {
  if (!isAutoFullRegion(region)) {
    return false;
  }
  const textLength = `${region.problemMarkdown ?? region.ocrText ?? ""} ${region.explanationMarkdown ?? region.explanation ?? ""}`
    .replace(/\s+/g, " ")
    .trim().length;
  return region.status === "failed" || textLength < 24 || (region.verificationWarnings?.length ?? 0) > 0;
}
