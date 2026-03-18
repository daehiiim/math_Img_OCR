const DEFAULT_API_BASE = "http://localhost:8000";
export const DEFAULT_LOCAL_API_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"];

// 개발/테스트에서만 localhost fallback 허용 여부를 계산한다.
function shouldAllowLocalApiFallback(): boolean {
  const runtimeOverride = (globalThis as { __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean })
    .__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__;
  if (typeof runtimeOverride === "boolean") {
    return runtimeOverride;
  }

  return Boolean(import.meta.env.DEV || import.meta.env.MODE === "test");
}

// 현재 브라우저 호스트에서 localhost fallback 사용 가능 여부를 판별한다.
function canUseLocalApiFallback(hostname: string | undefined): boolean {
  if (!shouldAllowLocalApiFallback()) {
    return false;
  }

  return !hostname || DEFAULT_LOCAL_API_HOSTS.includes(hostname.toLowerCase());
}

// 배포 환경과 로컬 환경을 모두 고려해 API base URL을 결정한다.
export function getApiBaseUrl(): string {
  const viteEnvBase = (import.meta as { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL;
  const runtimeBase = (globalThis as { __MATH_OCR_API_BASE__?: string }).__MATH_OCR_API_BASE__;
  const configuredBase = runtimeBase ?? viteEnvBase;

  if (configuredBase?.trim()) {
    return configuredBase.replace(/\/$/, "");
  }

  if (canUseLocalApiFallback(globalThis.location?.hostname)) {
    return DEFAULT_API_BASE;
  }

  throw new Error("API base URL is not configured. Set VITE_API_BASE_URL for deployed environments.");
}
