import type { JobExecutionOptions, Region } from "../store/jobStore";

/** 선택한 작업과 영역별 과금 상태를 기준으로 이번 실행의 최대 차감 크레딧을 계산한다. */
export function calculateRequiredCredits(
  options: JobExecutionOptions,
  openAiConnected: boolean,
  regions: Region[]
): number {
  let requiredCredits = 0;
  const targetRegions = regions;

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
