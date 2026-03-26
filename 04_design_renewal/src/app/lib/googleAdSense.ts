const GOOGLE_ADSENSE_SCRIPT_BASE_URL =
  "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=";

export const DEFAULT_GOOGLE_ADSENSE_CLIENT_ID = "ca-pub-4088422118336195";

/** 클라이언트 id 기준으로 중복 삽입 방지용 script id를 만든다. */
function getGoogleAdSenseScriptId(clientId: string): string {
  return `math-ocr-google-adsense-${clientId}`;
}

/** AdSense 로더 URL을 클라이언트 id 기준으로 조합한다. */
export function buildGoogleAdSenseScriptUrl(clientId: string): string {
  return `${GOOGLE_ADSENSE_SCRIPT_BASE_URL}${clientId}`;
}

/** 예상 가능한 에러는 clientId 누락과 head 미준비뿐이므로 사용자 메시지 없이 조용히 건너뛴다. */
export function appendGoogleAdSenseScript(clientId: string): void {
  if (!clientId || !document.head) {
    return;
  }

  const scriptId = getGoogleAdSenseScriptId(clientId);
  if (document.getElementById(scriptId)) {
    return;
  }

  const scriptElement = document.createElement("script");
  scriptElement.id = scriptId;
  scriptElement.async = true;
  scriptElement.crossOrigin = "anonymous";
  scriptElement.dataset.googleAdsense = "math-ocr";
  scriptElement.src = buildGoogleAdSenseScriptUrl(clientId);
  document.head.append(scriptElement);
}
