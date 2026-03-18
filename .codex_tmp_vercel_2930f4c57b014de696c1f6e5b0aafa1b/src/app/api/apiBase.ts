const LOCAL_API_PROTOCOL = "http";
const LOCAL_API_HOSTNAMES = ["localhost", "127.0.0.1", "0.0.0.0"] as const;
const LOCAL_API_PORT = "8000";

type ApiRuntimeConfig = typeof globalThis & {
  __MATH_OCR_API_BASE__?: string;
  __MATH_OCR_ALLOW_LOCAL_API_FALLBACK__?: boolean;
  process?: {
    env?: {
      VITE_API_BASE_URL?: string;
    };
  };
};

// 런타임 전역 설정 접근을 한 곳으로 모은다.
function getRuntimeConfig(): ApiRuntimeConfig {
  return globalThis as ApiRuntimeConfig;
}

// 로컬 개발용 API base URL 을 런타임에 조합한다.
function getLocalApiBaseUrl(): string {
  return [LOCAL_API_PROTOCOL, "://", LOCAL_API_HOSTNAMES[0], ":", LOCAL_API_PORT].join("");
}

// API base 값의 공백과 마지막 슬래시를 정규화한다.
function normalizeApiBase(value: string): string {
  const trimmed = value.trim();
  if (!trimmed || trimmed === "/" || trimmed.toLowerCase() === "same-origin") {
    return "";
  }

  return trimmed ? trimmed.replace(/\/$/, "") : "";
}

// 런타임 override 존재 여부를 명시적으로 판별한다.
function hasRuntimeApiBaseOverride(runtimeConfig: ApiRuntimeConfig): boolean {
  return Object.prototype.hasOwnProperty.call(runtimeConfig, "__MATH_OCR_API_BASE__");
}

// 테스트 환경에서도 읽을 수 있도록 process env fallback 을 지원한다.
function getProcessEnvApiBase(): string | undefined {
  const processEnv = getRuntimeConfig().process?.env;
  if (!processEnv || !Object.prototype.hasOwnProperty.call(processEnv, "VITE_API_BASE_URL")) {
    return undefined;
  }

  return normalizeApiBase(processEnv.VITE_API_BASE_URL ?? "");
}

// runtime override 와 env 값을 우선순위에 맞춰 읽는다.
function getConfiguredApiBaseFromEnv(): string | undefined {
  const processEnvBase = getProcessEnvApiBase();
  if (typeof processEnvBase === "string") {
    return processEnvBase;
  }

  const viteEnvBase = typeof __MATH_OCR_VITE_API_BASE__ === "string" ? __MATH_OCR_VITE_API_BASE__ : "";
  if (viteEnvBase?.trim()) {
    return normalizeApiBase(viteEnvBase);
  }

  return undefined;
}

// 런타임 override 는 배포 환경에서도 명시 설정으로 항상 우선한다.
function getRuntimeOverrideApiBase(): string | undefined {
  const runtimeConfig = getRuntimeConfig();
  if (hasRuntimeApiBaseOverride(runtimeConfig)) {
    const runtimeBase = runtimeConfig.__MATH_OCR_API_BASE__;
    return typeof runtimeBase === "string" ? normalizeApiBase(runtimeBase) : "";
  }

  return undefined;
}

// 개발과 테스트에서만 localhost fallback 허용 여부를 결정한다.
function shouldAllowLocalApiFallback(): boolean {
  const runtimeOverride = getRuntimeConfig().__MATH_OCR_ALLOW_LOCAL_API_FALLBACK__;
  if (typeof runtimeOverride === "boolean") {
    return runtimeOverride;
  }

  return Boolean(import.meta.env.DEV || import.meta.env.MODE === "test");
}

// 로컬 호스트에서만 localhost fallback 이 적용되도록 제한한다.
function canUseLocalApiFallback(hostname: string | undefined): boolean {
  if (!shouldAllowLocalApiFallback()) {
    return false;
  }

  return !hostname || LOCAL_API_HOSTNAMES.includes(hostname.toLowerCase() as (typeof LOCAL_API_HOSTNAMES)[number]);
}

// 배포 환경 규칙에 맞춰 최종 API base URL 을 계산한다.
export function getApiBaseUrl(): string {
  const hostname = globalThis.location?.hostname;
  const runtimeOverrideBase = getRuntimeOverrideApiBase();
  if (typeof runtimeOverrideBase === "string") {
    return runtimeOverrideBase;
  }

  // Vercel/운영 배포에서는 same-origin 프록시 계약을 우선하고 env 절대 URL은 로컬 개발에서만 사용한다.
  if (hostname && !canUseLocalApiFallback(hostname)) {
    return "";
  }

  const configuredEnvBase = getConfiguredApiBaseFromEnv();
  if (typeof configuredEnvBase === "string") {
    return configuredEnvBase;
  }

  if (canUseLocalApiFallback(hostname)) {
    return getLocalApiBaseUrl();
  }

  return "";
}

// API path 와 계산된 base URL 을 합쳐 요청 URL 을 만든다.
export function buildApiUrl(path: string): string {
  return `${getApiBaseUrl()}${path}`;
}
