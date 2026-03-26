import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter, Route, Routes, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { resetGoogleAnalyticsState } from "../lib/googleAnalytics";
import { GoogleAnalyticsTracker } from "./GoogleAnalyticsTracker";

type DataLayerCommand = [string, ...unknown[]];
type AnalyticsWindow = Window & { dataLayer?: unknown[] };

type PageViewPayload = {
  page_location: string;
  page_path: string;
  page_title: string;
};

/** 테스트에서 dataLayer 원본 엔트리를 그대로 읽어온다. */
function getRawDataLayerEntries(): unknown[] {
  const analyticsWindow = window as AnalyticsWindow;

  return analyticsWindow.dataLayer ?? [];
}

/** 공식 gtag queue 엔트리를 배열 형태로 정규화해 검증에 사용한다. */
function toDataLayerCommand(entry: unknown): DataLayerCommand | null {
  if (!entry || typeof entry !== "object" || !("length" in entry)) {
    return null;
  }

  const arrayLikeEntry = entry as ArrayLike<unknown>;
  return Array.from(arrayLikeEntry) as DataLayerCommand;
}

/** 테스트마다 dataLayer 누적 상태를 읽기 쉽게 가져온다. */
function getDataLayerCommands(): DataLayerCommand[] {
  return getRawDataLayerEntries()
    .map(toDataLayerCommand)
    .filter((command): command is DataLayerCommand => command !== null);
}

/** 기록된 page_view 이벤트만 추려서 검증에 사용한다. */
function getPageViewEvents(): PageViewPayload[] {
  return getDataLayerCommands()
    .filter((command) => command[0] === "event" && command[1] === "page_view")
    .map((command) => command[2] as PageViewPayload);
}

/** 라우트 이동 버튼과 트래커를 함께 렌더링하는 테스트 전용 셸이다. */
function TrackerHarness() {
  const navigate = useNavigate();

  return (
    <>
      <GoogleAnalyticsTracker enabled measurementId="G-SM6ETGCFGP" />
      <button type="button" onClick={() => navigate("/pricing?plan=pro#summary")}>
        가격으로 이동
      </button>
    </>
  );
}

describe("GoogleAnalyticsTracker", () => {
  beforeEach(() => {
    document.title = "Math OCR Test";
    window.history.pushState({}, "", "/");
    resetGoogleAnalyticsState();
  });

  afterEach(() => {
    resetGoogleAnalyticsState();
  });

  it("운영 추적이 비활성화되면 스크립트와 이벤트를 만들지 않는다", () => {
    render(
      <BrowserRouter>
        <GoogleAnalyticsTracker enabled={false} measurementId="G-SM6ETGCFGP" />
      </BrowserRouter>
    );

    expect(document.head.querySelector('script[src*="googletagmanager.com/gtag/js"]')).not.toBeInTheDocument();
    expect(getDataLayerCommands()).toHaveLength(0);
  });

  it("초기 진입과 라우트 변경마다 page_view를 기록한다", async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<TrackerHarness />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(document.head.querySelector('script[src="https://www.googletagmanager.com/gtag/js?id=G-SM6ETGCFGP"]')).toBeInTheDocument();
    });

    expect(getDataLayerCommands()).toContainEqual(["config", "G-SM6ETGCFGP", { send_page_view: false }]);
    expect(getPageViewEvents()[0]).toMatchObject({
      page_location: `${window.location.origin}/`,
      page_path: "/",
      page_title: "Math OCR Test",
    });

    await user.click(screen.getByRole("button", { name: "가격으로 이동" }));

    await waitFor(() => {
      expect(getPageViewEvents()).toHaveLength(2);
    });

    expect(getPageViewEvents()[1]).toMatchObject({
      page_location: `${window.location.origin}/pricing?plan=pro#summary`,
      page_path: "/pricing?plan=pro#summary",
      page_title: "Math OCR Test",
    });
  });

  it("공식 gtag 스니펫과 같은 arguments queue 형식으로 명령을 적재한다", async () => {
    render(
      <BrowserRouter>
        <GoogleAnalyticsTracker enabled measurementId="G-SM6ETGCFGP" />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(getRawDataLayerEntries()).toHaveLength(3);
    });

    const [jsCommand, configCommand, pageViewCommand] = getRawDataLayerEntries();

    expect(Array.isArray(jsCommand)).toBe(false);
    expect(Array.isArray(configCommand)).toBe(false);
    expect(Array.isArray(pageViewCommand)).toBe(false);

    expect(getDataLayerCommands()).toContainEqual(["config", "G-SM6ETGCFGP", { send_page_view: false }]);
    expect(getDataLayerCommands()).toContainEqual([
      "event",
      "page_view",
      {
        page_location: `${window.location.origin}/`,
        page_path: "/",
        page_title: "Math OCR Test",
      },
    ]);
  });
});
