import { useEffect } from "react";

import {
  DEFAULT_MICROSOFT_CLARITY_PROJECT_ID,
  appendMicrosoftClarityScript,
} from "../lib/microsoftClarity";

type ClarityTrackerProps = {
  enabled?: boolean;
  projectId?: string;
};

/** Microsoft Clarity 기본 스크립트를 앱 전역에 한 번만 연결한다. */
export function ClarityTracker({
  enabled = import.meta.env.PROD,
  projectId = DEFAULT_MICROSOFT_CLARITY_PROJECT_ID,
}: ClarityTrackerProps) {
  useEffect(() => {
    if (!enabled || !projectId) {
      return;
    }

    appendMicrosoftClarityScript(projectId);
  }, [enabled, projectId]);

  return null;
}
