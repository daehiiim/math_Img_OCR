const GOOGLE_ANALYTICS_SCRIPT_BASE_URL = "https://www.googletagmanager.com/gtag/js?id=";

export const DEFAULT_GOOGLE_ANALYTICS_MEASUREMENT_ID = "G-SM6ETGCFGP";

const initializedMeasurementIds = new Set<string>();

type AnalyticsWindow = Window & {
  dataLayer?: unknown[][];
  gtag?: (...args: unknown[]) => void;
};

type GoogleAnalyticsConfig = {
  send_page_view: boolean;
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

// 측정 ID별 스크립트 DOM id를 일관되게 만든다.
function getGoogleAnalyticsScriptId(measurementId: string): string {
  return `math-ocr-google-analytics-${measurementId}`;
}

// Google Analytics 로더 URL을 측정 ID 기준으로 조합한다.
export function buildGoogleAnalyticsScriptUrl(measurementId: string): string {
  return `${GOOGLE_ANALYTICS_SCRIPT_BASE_URL}${measurementId}`;
}

// dataLayer 배열이 없으면 초기화하고 재사용한다.
function ensureDataLayer(): unknown[][] {
  const analyticsWindow = getAnalyticsWindow();
  analyticsWindow.dataLayer ??= [];
  return analyticsWindow.dataLayer;
}

// gtag 호출 함수를 한 번만 만들고 이후에는 재사용한다.
function ensureGtag(): (...args: unknown[]) => void {
  const analyticsWindow = getAnalyticsWindow();
  if (typeof analyticsWindow.gtag === "function") {
    return analyticsWindow.gtag;
  }

  analyticsWindow.gtag = (...args: unknown[]) => {
    ensureDataLayer().push(args);
  };

  return analyticsWindow.gtag;
}

// 외부 gtag 로더 스크립트를 head에 한 번만 주입한다.
export function appendGoogleAnalyticsScript(measurementId: string): void {
  const scriptId = getGoogleAnalyticsScriptId(measurementId);
  if (document.getElementById(scriptId)) {
    return;
  }

  const scriptElement = document.createElement("script");
  scriptElement.id = scriptId;
  scriptElement.async = true;
  scriptElement.dataset.googleAnalytics = "math-ocr";
  scriptElement.src = buildGoogleAnalyticsScriptUrl(measurementId);
  document.head.append(scriptElement);
}

// 자동 page_view를 끄고 수동 추적 모드로 Analytics를 초기화한다.
export function initializeGoogleAnalytics(measurementId: string): void {
  if (initializedMeasurementIds.has(measurementId)) {
    return;
  }

  const config: GoogleAnalyticsConfig = { send_page_view: false };
  const gtag = ensureGtag();

  gtag("js", new Date());
  gtag("config", measurementId, config);
  initializedMeasurementIds.add(measurementId);
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
  initializedMeasurementIds.clear();

  const analyticsWindow = getAnalyticsWindow();
  analyticsWindow.dataLayer = [];
  delete analyticsWindow.gtag;

  document
    .querySelectorAll('script[data-google-analytics="math-ocr"]')
    .forEach((scriptElement) => scriptElement.remove());
}
