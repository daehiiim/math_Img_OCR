import type { JobExecutionOptions, Region } from "../store/jobStore";

/** 영역이 없으면 자동 전체 인식 1건을 가정한 preview region을 만든다. */
function buildAutoFullPreviewRegion(): Region {
  return {
    id: "auto_full_preview",
    polygon: [],
    type: "mixed",
    order: 1,
    selectionMode: "auto_full",
    inputDevice: "system",
    warningLevel: "high_risk",
  };
}

/** 선택한 작업과 영역별 과금 상태를 기준으로 이번 실행의 최대 차감 크레딧을 계산한다. */
export function calculateRequiredCredits(
  options: JobExecutionOptions,
  openAiConnected: boolean,
  regions: Region[]
): number {
  let requiredCredits = 0;
  const targetRegions = regions.length > 0 ? regions : [buildAutoFullPreviewRegion()];

  for (const region of targetRegions) {
    if (options.doImageStylize && !region.imageCharged) {
      requiredCredits += 1;
    }
    if (options.doOcr && !openAiConnected && !region.ocrCharged) {
      requiredCredits += 1;
    }
    if (options.doExplanation && !openAiConnected && !region.explanationCharged) {
      requiredCredits += 1;
    }
  }

  return requiredCredits;
}
