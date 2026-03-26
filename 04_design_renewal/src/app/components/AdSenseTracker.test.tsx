import { render } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, describe, expect, it } from "vitest";

/** 테스트마다 AdSense 스크립트 흔적을 정리한다. */
function cleanupAdSenseArtifacts() {
  document
    .querySelectorAll('script[data-google-adsense="math-ocr"]')
    .forEach((scriptElement) => scriptElement.remove());
}

afterEach(() => {
  cleanupAdSenseArtifacts();
});

describe("AdSenseTracker", () => {
  it("광고 추적이 비활성화되면 스크립트를 주입하지 않는다", async () => {
    const { AdSenseTracker } = await import("./AdSenseTracker");

    render(<AdSenseTracker enabled={false} clientId="ca-pub-4088422118336195" />);

    expect(
      document.head.querySelector('script[src*="pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"]')
    ).not.toBeInTheDocument();
  });

  it("StrictMode 에서도 AdSense 스크립트를 한 번만 삽입한다", async () => {
    const { AdSenseTracker } = await import("./AdSenseTracker");

    render(
      <StrictMode>
        <AdSenseTracker enabled clientId="ca-pub-4088422118336195" />
      </StrictMode>
    );

    const scriptElements = document.head.querySelectorAll(
      'script[src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4088422118336195"]'
    );

    expect(scriptElements).toHaveLength(1);
    expect(scriptElements[0]).toHaveAttribute("crossorigin", "anonymous");
    expect((scriptElements[0] as HTMLScriptElement).async).toBe(true);
  });
});
