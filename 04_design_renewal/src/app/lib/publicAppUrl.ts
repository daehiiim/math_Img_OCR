import { isLocalUiMockEnabled } from "./localUiMock";
import { normalizeSiteUrl } from "../seo/siteSeo";

const LOCAL_APP_HOSTNAMES = ["localhost", "127.0.0.1", "0.0.0.0"] as const;

type PublicAppRuntimeConfig = typeof globalThis & {
  __MATH_OCR_PUBLIC_APP_URL__?: string;
  __MATH_OCR_SITE_URL__?: string;
  process?: {
    env?: {
      APP_URL?: string;
      NEXT_PUBLIC_SITE_URL?: string;
      SITE_URL?: string;
    };
  };
};

// 공개 앱 URL 관련 런타임 설정 접근을 한 곳으로 모은다.
function getRuntimeConfig(): PublicAppRuntimeConfig {
  return globalThis as PublicAppRuntimeConfig;
}

// URL 문자열의 공백과 마지막 슬래시를 정규화한다.
function normalizePublicAppUrl(value: string): string {
  return normalizeSiteUrl(value);
}

// 런타임 override, process env, Vite define 순서로 공개 앱 URL을 읽는다.
function getConfiguredPublicAppUrl(): string {
  const siteRuntimeValue = getRuntimeConfig().__MATH_OCR_SITE_URL__;
  if (typeof siteRuntimeValue === "string" && siteRuntimeValue.trim()) {
    return normalizePublicAppUrl(siteRuntimeValue);
  }

  const runtimeValue = getRuntimeConfig().__MATH_OCR_PUBLIC_APP_URL__;
  if (typeof runtimeValue === "string" && runtimeValue.trim()) {
    return normalizePublicAppUrl(runtimeValue);
  }

  const siteValue = getRuntimeConfig().process?.env?.SITE_URL;
  if (typeof siteValue === "string" && siteValue.trim()) {
    return normalizePublicAppUrl(siteValue);
  }

  const nextSiteValue = getRuntimeConfig().process?.env?.NEXT_PUBLIC_SITE_URL;
  if (typeof nextSiteValue === "string" && nextSiteValue.trim()) {
    return normalizePublicAppUrl(nextSiteValue);
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

// mock 모드에서는 localhost origin도 공개 앱 URL로 사용한다.
function getLocalMockOriginFallback(): string {
  const currentLocation = globalThis.location;
  if (!isLocalUiMockEnabled() || !currentLocation?.origin) {
    return "";
  }

  return normalizePublicAppUrl(currentLocation.origin);
}

// 공개 앱 URL의 최종 기준값을 반환한다.
export function getPublicAppUrl(): string {
  return getConfiguredPublicAppUrl() || getLocalMockOriginFallback() || getDeployedOriginFallback();
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
