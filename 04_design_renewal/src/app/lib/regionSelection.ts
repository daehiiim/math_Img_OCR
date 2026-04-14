import type { Region, SelectionMode } from "../store/jobStore";

export const AUTO_FULL_RISK_MESSAGE =
  "영역을 지정하지 않으면 이미지 전체를 자동 인식하지만, 배경·여백·여러 문항이 함께 잡혀 정확도가 낮아질 수 있습니다. 정확한 결과가 필요하면 직접 영역을 지정하세요.";

export const AUTO_FULL_LOW_CONFIDENCE_MESSAGE =
  "자동 전체 인식 결과의 신뢰도가 낮을 수 있습니다. 직접 영역을 지정하면 더 정확할 수 있습니다.";

export const AUTO_DETECT_GUIDE_MESSAGE =
  "영역을 직접 그리지 않아도 AI가 문항·지문·수식·표·답안칸을 읽기 단위로 묶어서 찾아줍니다. 실행 전 박스를 확인하고 필요하면 수정하세요.";

export const AUTO_DETECT_LOW_CONFIDENCE_MESSAGE =
  "AI가 문항을 찾았지만 경계 신뢰도가 낮거나 애매한 영역이 있습니다. 실행 전에 박스를 확인해 주세요.";

/** 현재 편집 상태가 수동/자동 분할/자동 전체 중 어느 쪽인지 계산한다. */
export function getSelectionMode(regions: Region[]): SelectionMode {
  if (regions.length === 0) {
    return "none";
  }
  if (regions.some((region) => region.selectionMode === "manual" || !region.selectionMode)) {
    return "manual";
  }
  if (regions.some((region) => region.selectionMode === "auto_detected")) {
    return "auto_detected";
  }
  return "auto_full";
}


/** 사용자가 직접 그린 수동 영역이 하나라도 있는지 계산한다. */
export function hasUserDrawnRegion(regions: Region[]): boolean {
  return getSelectionMode(regions) === "manual";
}


/** 자동 전체 인식 결과인지 판단한다. */
export function isAutoFullRegion(region: Region): boolean {
  return region.selectionMode === "auto_full";
}


/** AI 자동 분할 결과인지 판단한다. */
export function isAutoDetectedRegion(region: Region): boolean {
  return region.selectionMode === "auto_detected";
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


/** 자동 분할 결과가 재검토가 필요한지 판단한다. */
export function isLowConfidenceAutoDetectedRegion(region: Region): boolean {
  if (!isAutoDetectedRegion(region)) {
    return false;
  }
  if (region.warningLevel === "high_risk") {
    return true;
  }
  return (region.autoDetectConfidence ?? 0) > 0 && (region.autoDetectConfidence ?? 0) < 0.62;
}
