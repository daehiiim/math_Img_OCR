import { useEffect, useRef } from "react";
import { useLocation } from "react-router";

import {
  DEFAULT_GOOGLE_ANALYTICS_MEASUREMENT_ID,
  trackPageView,
} from "../lib/googleAnalytics";

type GoogleAnalyticsTrackerProps = {
  enabled?: boolean;
  measurementId?: string;
};

// pathname, search, hash를 합쳐 Analytics에 보낼 정규 경로를 만든다.
function buildTrackedPath(pathname: string, search: string, hash: string): string {
  return `${pathname}${search}${hash}`;
}

// SPA 라우트 변경마다 Google Analytics page_view를 수동 전송한다.
export function GoogleAnalyticsTracker({
  enabled = import.meta.env.PROD,
  measurementId = DEFAULT_GOOGLE_ANALYTICS_MEASUREMENT_ID,
}: GoogleAnalyticsTrackerProps) {
  const location = useLocation();
  const hasSkippedInitialPageViewRef = useRef(false);

  useEffect(() => {
    if (!enabled || !measurementId) {
      return;
    }

    if (!hasSkippedInitialPageViewRef.current) {
      hasSkippedInitialPageViewRef.current = true;
      return;
    }

    trackPageView(buildTrackedPath(location.pathname, location.search, location.hash));
  }, [enabled, measurementId, location.hash, location.pathname, location.search]);

  return null;
}
