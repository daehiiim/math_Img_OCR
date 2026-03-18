import { describe, expect, it } from "vitest";

import { getJobProgressStatus, getStatusConfig } from "./jobPresentation";

describe("getStatusConfig", () => {
  it("queued 상태를 영역 저장됨으로 표시한다", () => {
    expect(getStatusConfig("queued").label).toBe("영역 저장됨");
  });

  it("failed 상태를 destructive로 표시한다", () => {
    expect(getStatusConfig("failed").variant).toBe("destructive");
  });
});

describe("getJobProgressStatus", () => {
  it("created 상태는 영역 대기로 정규화한다", () => {
    expect(getJobProgressStatus("created")).toBe("regions_pending");
  });

  it("failed 상태는 실행 단계에 정렬한다", () => {
    expect(getJobProgressStatus("failed")).toBe("running");
  });
});
