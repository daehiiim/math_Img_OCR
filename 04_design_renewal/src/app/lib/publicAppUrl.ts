const LOCAL_APP_HOSTNAMES = ["localhost", "127.0.0.1", "0.0.0.0"] as const;

type PublicAppRuntimeConfig = typeof globalThis & {
  __MATH_OCR_PUBLIC_APP_URL__?: string;
  process?: {
    env?: {
      APP_URL?: string;
    };
  };
};

// 공개 앱 URL 관련 런타임 설정 접근을 한 곳으로 모은다.
function getRuntimeConfig(): PublicAppRuntimeConfig {
  return globalThis as PublicAppRuntimeConfig;
}

// URL 문자열의 공백과 마지막 슬래시를 정규화한다.
function normalizePublicAppUrl(value: string): string {
  const trimmed = value.trim();
  return trimmed ? trimmed.replace(/\/$/, "") : "";
}

// 런타임 override, process env, Vite define 순서로 공개 앱 URL을 읽는다.
function getConfiguredPublicAppUrl(): string {
  const runtimeValue = getRuntimeConfig().__MATH_OCR_PUBLIC_APP_URL__;
  if (typeof runtimeValue === "string" && runtimeValue.trim()) {
    return normalizePublicAppUrl(runtimeValue);
  }

  const processValue = getRuntimeConfig().process?.env?.APP_URL;
  if (typeof processValue === "string" && processValue.trim()) {
    return normalizePublicAppUrl(processValue);
  }

  return typeof __MATH_OCR_PUBLIC_APP_URL__ === "string"
    ? normalizePublicAppUrl(__MATH_OCR_PUBLIC_APP_URL__)
    : "";
}

// 현재 브라우저 origin 이 로컬 주소인지 판별한다.
function isLocalHostname(hostname: string | undefined): boolean {
  if (!hostname) {
    return false;
  }

  return LOCAL_APP_HOSTNAMES.includes(hostname.toLowerCase() as (typeof LOCAL_APP_HOSTNAMES)[number]);
}

// 배포 origin 에서만 현재 origin fallback 을 허용한다.
function getDeployedOriginFallback(): string {
  const currentLocation = globalThis.location;
  if (!currentLocation?.origin || isLocalHostname(currentLocation.hostname)) {
    return "";
  }

  return normalizePublicAppUrl(currentLocation.origin);
}

// 공개 앱 URL의 최종 기준값을 반환한다.
export function getPublicAppUrl(): string {
  return getConfiguredPublicAppUrl() || getDeployedOriginFallback();
}

// 공개 앱 URL에 내부 경로를 붙여 절대 URL을 만든다.
export function buildPublicAppUrl(path: string): string {
  const baseUrl = getPublicAppUrl();
  if (!baseUrl) {
    throw new Error("APP_URL is not configured");
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}
