import { useEffect } from "react";

import {
  appendGoogleAdSenseScript,
  DEFAULT_GOOGLE_ADSENSE_CLIENT_ID,
} from "../lib/googleAdSense";

type AdSenseTrackerProps = {
  enabled?: boolean;
  clientId?: string;
};

/** Google AdSense 기본 스크립트를 앱 전역에 한 번만 연결한다. */
export function AdSenseTracker({
  enabled = import.meta.env.PROD,
  clientId = DEFAULT_GOOGLE_ADSENSE_CLIENT_ID,
}: AdSenseTrackerProps) {
  useEffect(() => {
    if (!enabled || !clientId) {
      return;
    }

    appendGoogleAdSenseScript(clientId);
  }, [enabled, clientId]);

  return null;
}
