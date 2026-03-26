const MICROSOFT_CLARITY_SCRIPT_BASE_URL = "https://www.clarity.ms/tag/";

export const DEFAULT_MICROSOFT_CLARITY_PROJECT_ID = "w1jgubofnf";

type ClarityCall = ((...args: unknown[]) => void) & { q?: unknown[][] };
type ClarityWindow = Window & { clarity?: ClarityCall };

/** Clarity 전역 함수에 접근할 브라우저 window 객체를 한 곳으로 고정한다. */
function getClarityWindow(): ClarityWindow {
  return window as ClarityWindow;
}

/** 프로젝트 id 기준으로 중복 삽입 방지용 script id를 만든다. */
function getMicrosoftClarityScriptId(projectId: string): string {
  return `math-ocr-microsoft-clarity-${projectId}`;
}

/** 외부 Clarity 로더 URL을 프로젝트 id 기준으로 조합한다. */
function buildMicrosoftClarityScriptUrl(projectId: string): string {
  return `${MICROSOFT_CLARITY_SCRIPT_BASE_URL}${projectId}`;
}

/** 스크립트 로드 전 호출도 누적되도록 Clarity queue 함수를 준비한다. */
function ensureClarityQueue(): void {
  const clarityWindow = getClarityWindow();
  if (typeof clarityWindow.clarity === "function") {
    return;
  }

  const queuedClarity = ((...args: unknown[]) => {
    queuedClarity.q ??= [];
    queuedClarity.q.push(args);
  }) as ClarityCall;

  queuedClarity.q = [];
  clarityWindow.clarity = queuedClarity;
}

/** Microsoft Clarity 스크립트를 head 에 한 번만 주입한다. */
export function appendMicrosoftClarityScript(projectId: string): void {
  if (!projectId || !document.head) {
    return;
  }

  ensureClarityQueue();

  const scriptId = getMicrosoftClarityScriptId(projectId);
  if (document.getElementById(scriptId)) {
    return;
  }

  const scriptElement = document.createElement("script");
  scriptElement.id = scriptId;
  scriptElement.async = true;
  scriptElement.type = "text/javascript";
  scriptElement.dataset.microsoftClarity = "math-ocr";
  scriptElement.src = buildMicrosoftClarityScriptUrl(projectId);
  document.head.append(scriptElement);
}
