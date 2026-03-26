import { render } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, describe, expect, it } from "vitest";

type ClarityCall = ((...args: unknown[]) => void) & { q?: unknown[][] };
type ClarityWindow = Window & { clarity?: ClarityCall };

/** 테스트마다 Clarity 전역 상태와 삽입 스크립트를 수동으로 초기화한다. */
function cleanupClarityArtifacts() {
  document
    .querySelectorAll('script[data-microsoft-clarity="math-ocr"]')
    .forEach((scriptElement) => scriptElement.remove());

  delete (window as ClarityWindow).clarity;
}

/** 테스트에서 queue 상태를 읽기 위한 전역 window 타입을 반환한다. */
function getClarityWindow(): ClarityWindow {
  return window as ClarityWindow;
}

afterEach(() => {
  cleanupClarityArtifacts();
});

describe("ClarityTracker", () => {
  it("운영 추적이 비활성화되면 스크립트와 queue를 만들지 않는다", async () => {
    const { ClarityTracker } = await import("./ClarityTracker");

    render(<ClarityTracker enabled={false} projectId="w1jgubofnf" />);

    expect(document.head.querySelector('script[src*="clarity.ms/tag/"]')).not.toBeInTheDocument();
    expect(getClarityWindow().clarity).toBeUndefined();
  });

  it("StrictMode 에서도 Clarity 스크립트를 한 번만 삽입하고 queue를 준비한다", async () => {
    const { ClarityTracker } = await import("./ClarityTracker");

    render(
      <StrictMode>
        <ClarityTracker enabled projectId="w1jgubofnf" />
      </StrictMode>
    );

    const scriptElements = document.head.querySelectorAll('script[src="https://www.clarity.ms/tag/w1jgubofnf"]');

    expect(scriptElements).toHaveLength(1);
    expect(getClarityWindow().clarity).toBeTypeOf("function");

    getClarityWindow().clarity?.("set", "plan", "pro");

    expect(getClarityWindow().clarity?.q).toContainEqual(["set", "plan", "pro"]);
  });
});
