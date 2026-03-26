export const DEFAULT_GOOGLE_ANALYTICS_MEASUREMENT_ID = "G-SM6ETGCFGP";

type GtagFunction = (...args: unknown[]) => void;
type AnalyticsWindow = Window & {
  dataLayer?: unknown[];
  gtag?: GtagFunction;
};

type PageViewPayload = {
  page_location: string;
  page_path: string;
  page_title: string;
};

// Google Analytics 전역 상태에 접근할 창 객체를 한 곳으로 고정한다.
function getAnalyticsWindow(): AnalyticsWindow {
  return window as AnalyticsWindow;
}

// 현재 문서 기준 page_view payload를 만든다.
export function buildPageViewPayload(pagePath: string): PageViewPayload {
  return {
    page_location: window.location.href,
    page_path: pagePath,
    page_title: document.title,
  };
}

// 현재 라우트 경로에 대한 page_view 이벤트를 수동으로 보낸다.
export function trackPageView(pagePath: string): void {
  const gtag = getAnalyticsWindow().gtag;
  if (typeof gtag !== "function") {
    return;
  }

  gtag("event", "page_view", buildPageViewPayload(pagePath));
}

// 테스트마다 Analytics 전역 상태와 삽입된 스크립트를 초기화한다.
export function resetGoogleAnalyticsState(): void {
  const analyticsWindow = getAnalyticsWindow();
  analyticsWindow.dataLayer = [];
  delete analyticsWindow.gtag;
}
