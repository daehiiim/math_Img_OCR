import { describe, expect, it } from "vitest";

import {
  DEFAULT_SITE_URL,
  buildHomeStructuredData,
  buildRssXml,
  buildRobotsTxt,
  buildSitemapXml,
  getRouteSeo,
  resolveSeoSiteUrl,
} from "./siteSeo";

describe("siteSeo", () => {
  it("site url 후보를 정규화하고 마지막 슬래시를 제거한다", () => {
    expect(resolveSeoSiteUrl("", " https://mathhwp.vercel.app/ ")).toBe(
      "https://mathhwp.vercel.app"
    );
  });

  it("legacy vercel host가 들어와도 canonical host로 정규화한다", () => {
    const legacySiteUrl = DEFAULT_SITE_URL.replace("mathhwp", "mathtohwp");

    expect(resolveSeoSiteUrl(legacySiteUrl)).toBe(DEFAULT_SITE_URL);
    expect(buildSitemapXml(legacySiteUrl)).toContain("<loc>https://mathhwp.vercel.app/</loc>");
  });

  it("site url 후보가 모두 비어 있으면 기본 production url을 사용한다", () => {
    expect(resolveSeoSiteUrl("", undefined)).toBe(DEFAULT_SITE_URL);
  });

  it("홈 경로는 index 대상 메타데이터를 반환한다", () => {
    expect(getRouteSeo("/")).toMatchObject({
      title: "수식 OCR로 이미지 수식을 편집 가능한 한글 문서로 변환 | MathHWP",
      canonicalPath: "/",
      robots: "index,follow",
    });
  });

  it("로그인 경로는 noindex 메타데이터를 반환한다", () => {
    expect(getRouteSeo("/login")).toMatchObject({
      canonicalPath: "/login",
      robots: "noindex,nofollow",
    });
  });

  it("robots.txt는 sitemap 위치와 전체 허용 규칙을 포함한다", () => {
    expect(buildRobotsTxt(DEFAULT_SITE_URL)).toContain("Allow: /");
    expect(buildRobotsTxt(DEFAULT_SITE_URL)).toContain(
      "Sitemap: https://mathhwp.vercel.app/sitemap.xml"
    );
  });

  it("sitemap.xml은 주요 공개 경로만 포함한다", () => {
    const sitemapXml = buildSitemapXml(DEFAULT_SITE_URL);

    expect(sitemapXml).toContain("<loc>https://mathhwp.vercel.app/</loc>");
    expect(sitemapXml).toContain("<loc>https://mathhwp.vercel.app/new</loc>");
    expect(sitemapXml).toContain("<loc>https://mathhwp.vercel.app/pricing</loc>");
    expect(sitemapXml).not.toContain("/workspace");
    expect(sitemapXml).not.toContain("/payment");
  });

  it("rss.xml은 주요 공개 경로를 canonical host 기준 피드로 생성한다", () => {
    const rssXml = buildRssXml(DEFAULT_SITE_URL);

    expect(rssXml).toContain("<title>MathHWP</title>");
    expect(rssXml).toContain("<link>https://mathhwp.vercel.app/</link>");
    expect(rssXml).toContain(
      '<atom:link href="https://mathhwp.vercel.app/rss.xml" rel="self" type="application/rss+xml" />'
    );
    expect(rssXml).toContain(
      "<item><title>수식 OCR로 이미지 수식을 편집 가능한 한글 문서로 변환 | MathHWP</title>"
    );
    expect(rssXml).toContain("<link>https://mathhwp.vercel.app/new</link>");
    expect(rssXml).toContain("<link>https://mathhwp.vercel.app/pricing</link>");
    expect(rssXml).not.toContain("/workspace");
  });

  it("홈 구조화 데이터는 웹사이트와 소프트웨어 앱 정보를 함께 제공한다", () => {
    const structuredData = buildHomeStructuredData(DEFAULT_SITE_URL);
    const schemaTypes = structuredData.map((entry) => entry["@type"]);

    expect(schemaTypes).toEqual(
      expect.arrayContaining(["WebSite", "SoftwareApplication", "Organization"])
    );
    expect(structuredData[0]).toMatchObject({
      name: "MathHWP",
      url: "https://mathhwp.vercel.app",
    });
  });
});
