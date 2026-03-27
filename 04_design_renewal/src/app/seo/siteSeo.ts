export const DEFAULT_SITE_URL = "https://mathhwp.vercel.app";
export const SITE_NAME = "MathHWP";
export const OG_IMAGE_PATH = "/og-image.svg";
export const ADSENSE_ADS_TXT_PUBLISHER = "pub-4088422118336195";
export const ADSENSE_SELLER_ACCOUNT_ID = "f08c47fec0942fa0";
const CANONICAL_SITE_HOSTNAME = new URL(DEFAULT_SITE_URL).hostname;
const LEGACY_SITE_HOSTNAME = CANONICAL_SITE_HOSTNAME.replace("mathhwp", "mathtohwp");

export type RouteSeo = {
  canonicalPath: string;
  description: string;
  robots: string;
  title: string;
};

type StructuredDataEntry = Record<string, unknown>;

const PUBLIC_SITEMAP_PATHS = ["/", "/new", "/pricing"] as const;

/** 후보 URL 중 첫 번째 유효한 값을 canonical host로 정규화한다. */
export function resolveSeoSiteUrl(...candidates: Array<string | undefined>): string {
  for (const candidate of candidates) {
    const normalizedValue = normalizeSiteUrl(candidate);
    if (normalizedValue) {
      return normalizedValue;
    }
  }

  return DEFAULT_SITE_URL;
}

/** canonical host 비교를 위해 공백과 마지막 슬래시를 제거한다. */
export function normalizeSiteUrl(value: string | undefined): string {
  const trimmedValue = value?.trim() ?? "";
  return trimmedValue ? rewriteLegacySiteHost(trimmedValue.replace(/\/$/, "")) : "";
}

/** 내부 경로를 절대 canonical URL로 조합한다. */
export function buildAbsoluteUrl(siteUrl: string, path: string): string {
  const normalizedSiteUrl = resolveSeoSiteUrl(siteUrl);
  const normalizedPath = path === "/" ? "/" : `/${path.replace(/^\/+|\/+$/g, "")}`;
  return normalizedPath === "/" ? `${normalizedSiteUrl}/` : `${normalizedSiteUrl}${normalizedPath}`;
}

/** 현재 경로에 대응하는 title, description, robots 규칙을 반환한다. */
export function getRouteSeo(pathname: string): RouteSeo {
  const normalizedPath = normalizePathname(pathname);

  if (normalizedPath === "/") {
    return {
      title: "수식 OCR로 이미지 수식을 편집 가능한 한글 문서로 변환 | MathHWP",
      description:
        "MathHWP는 수학 OCR과 수식 OCR을 통해 문제 사진을 편집 가능한 한글 수식 문서로 바꾸는 도구입니다. 학생, 교사, 문서 작성자가 수식 이미지 변환과 HWPX 워크플로를 더 빠르게 처리할 수 있습니다.",
      canonicalPath: "/",
      robots: "index,follow",
    };
  }

  if (normalizedPath === "/new") {
    return {
      title: "새 작업 생성 | 수식 이미지 변환 작업실 | MathHWP",
      description:
        "PNG, JPG, JPEG 수식 이미지를 업로드하고 영역을 지정해 MathHWP 작업실에서 OCR, 해설, HWPX 변환 워크플로를 시작하세요.",
      canonicalPath: "/new",
      robots: "index,follow",
    };
  }

  if (normalizedPath === "/pricing") {
    return {
      title: "가격 안내 | 수식 OCR 크레딧 플랜 | MathHWP",
      description:
        "MathHWP 수식 OCR 작업에 필요한 크레딧 플랜과 결제 흐름을 확인하세요. 학생, 교사, 문서 작성자에게 맞는 작업량 기준으로 비교할 수 있습니다.",
      canonicalPath: "/pricing",
      robots: "index,follow",
    };
  }

  if (normalizedPath === "/login") {
    return {
      title: "로그인 | MathHWP",
      description: "MathHWP 로그인 페이지입니다.",
      canonicalPath: "/login",
      robots: "noindex,nofollow",
    };
  }

  if (
    normalizedPath === "/connect-openai" ||
    normalizedPath.startsWith("/payment/") ||
    normalizedPath.startsWith("/workspace")
  ) {
    return {
      title: "MathHWP",
      description: "MathHWP 내부 작업 페이지입니다.",
      canonicalPath: normalizedPath,
      robots: "noindex,nofollow",
    };
  }

  return {
    title: "페이지를 찾을 수 없습니다 | MathHWP",
    description: "요청한 페이지를 찾을 수 없습니다.",
    canonicalPath: normalizedPath,
    robots: "noindex,nofollow",
  };
}

/** 홈 경로에 노출할 구조화 데이터 묶음을 생성한다. */
export function buildHomeStructuredData(siteUrl: string): StructuredDataEntry[] {
  return [
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: SITE_NAME,
      url: siteUrl,
      inLanguage: "ko-KR",
      description:
        "수식 OCR, 수학 OCR, 수식 한글 변환 워크플로를 제공하는 MathHWP 공식 사이트",
    },
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: SITE_NAME,
      applicationCategory: "EducationalApplication",
      operatingSystem: "Browser",
      url: siteUrl,
      inLanguage: "ko-KR",
      description:
        "이미지 속 수식을 OCR로 읽고 편집 가능한 한글 문서 workflow로 연결하는 수학 OCR 도구",
      featureList: [
        "수식 OCR",
        "수학 OCR",
        "수식 이미지 변환",
        "수식 한글 변환",
        "영역 지정 기반 작업실",
      ],
    },
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: SITE_NAME,
      url: siteUrl,
      logo: buildAbsoluteUrl(siteUrl, "/favicon.svg"),
    },
  ];
}

/** robots.txt 본문을 빌드 시점에 생성한다. */
export function buildRobotsTxt(siteUrl: string): string {
  return ["User-agent: *", "Allow: /", "", `Sitemap: ${buildAbsoluteUrl(siteUrl, "/sitemap.xml")}`].join("\n");
}

/** ads.txt 본문을 AdSense 공급자 형식으로 생성한다. */
export function buildAdsTxt(): string {
  return ["google.com", ADSENSE_ADS_TXT_PUBLISHER, "DIRECT", ADSENSE_SELLER_ACCOUNT_ID].join(", ");
}

/** sitemap.xml 본문을 공개 경로 목록 기준으로 생성한다. */
export function buildSitemapXml(siteUrl: string): string {
  const lastModified = new Date().toISOString();
  const urlEntries = PUBLIC_SITEMAP_PATHS.map((path) => buildSitemapEntry(siteUrl, path, lastModified));

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urlEntries,
    "</urlset>",
  ].join("\n");
}

/** 홈이 아닌 경로에서는 구조화 데이터를 비워 중복 삽입을 막는다. */
export function getStructuredDataForPath(siteUrl: string, pathname: string): StructuredDataEntry[] {
  return normalizePathname(pathname) === "/" ? buildHomeStructuredData(siteUrl) : [];
}

/** 경로별 sitemap `<url>` 블록을 일관된 형식으로 만든다. */
function buildSitemapEntry(siteUrl: string, path: string, lastModified: string): string {
  return [
    "  <url>",
    `    <loc>${buildAbsoluteUrl(siteUrl, path)}</loc>`,
    `    <lastmod>${lastModified}</lastmod>`,
    "  </url>",
  ].join("\n");
}

/** 경로 비교 전에 슬래시 형태를 정규화한다. */
function normalizePathname(pathname: string): string {
  const trimmedValue = pathname.trim();
  if (!trimmedValue || trimmedValue === "/") {
    return "/";
  }

  return `/${trimmedValue.replace(/^\/+|\/+$/g, "")}`;
}

/** 이전 vercel host가 들어오면 현재 canonical host로 치환한다. */
function rewriteLegacySiteHost(value: string): string {
  try {
    const normalizedUrl = new URL(value);
    if (normalizedUrl.hostname !== LEGACY_SITE_HOSTNAME) {
      return value;
    }

    normalizedUrl.hostname = CANONICAL_SITE_HOSTNAME;
    return normalizedUrl.toString().replace(/\/$/, "");
  } catch {
    return value;
  }
}
