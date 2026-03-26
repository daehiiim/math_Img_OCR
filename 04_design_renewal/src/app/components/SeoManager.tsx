import { useEffect } from "react";
import { useLocation } from "react-router";

import { getPublicAppUrl } from "../lib/publicAppUrl";
import {
  OG_IMAGE_PATH,
  SITE_NAME,
  buildAbsoluteUrl,
  getRouteSeo,
  getStructuredDataForPath,
  resolveSeoSiteUrl,
} from "../seo/siteSeo";

/** name/property 기준 메타 태그를 생성하거나 갱신한다. */
function upsertMeta(attribute: "name" | "property", key: string, content: string) {
  const selector = `meta[${attribute}="${key}"]`;
  const metaElement = document.head.querySelector(selector) ?? document.createElement("meta");

  metaElement.setAttribute(attribute, key);
  metaElement.setAttribute("content", content);

  if (!metaElement.parentNode) {
    document.head.append(metaElement);
  }
}

/** rel 기준 링크 태그를 생성하거나 갱신한다. */
function upsertLink(rel: string, href: string) {
  const linkElement =
    document.head.querySelector(`link[rel="${rel}"]`) ?? document.createElement("link");

  linkElement.setAttribute("rel", rel);
  linkElement.setAttribute("href", href);

  if (!linkElement.parentNode) {
    document.head.append(linkElement);
  }
}

/** 홈 구조화 데이터 스크립트를 현재 상태에 맞게 교체한다. */
function updateStructuredData(payload: Array<Record<string, unknown>>) {
  const selector = 'script[data-seo-structured-data="home"]';
  const scriptElement = document.head.querySelector(selector);

  if (payload.length === 0) {
    scriptElement?.remove();
    return;
  }

  const nextScript = scriptElement ?? document.createElement("script");
  nextScript.setAttribute("type", "application/ld+json");
  nextScript.setAttribute("data-seo-structured-data", "home");
  nextScript.textContent = JSON.stringify(payload);

  if (!nextScript.parentNode) {
    document.head.append(nextScript);
  }
}

/** 현재 라우트 메타데이터를 문서 head에 일괄 반영한다. */
function applyRouteSeo(pathname: string) {
  const siteUrl = resolveSeoSiteUrl(getPublicAppUrl());
  const routeSeo = getRouteSeo(pathname);
  const canonicalUrl = buildAbsoluteUrl(siteUrl, routeSeo.canonicalPath);
  const ogImageUrl = buildAbsoluteUrl(siteUrl, OG_IMAGE_PATH);

  document.title = routeSeo.title;
  upsertMeta("name", "description", routeSeo.description);
  upsertMeta("name", "robots", routeSeo.robots);
  upsertMeta("name", "application-name", SITE_NAME);
  upsertMeta("property", "og:type", "website");
  upsertMeta("property", "og:site_name", SITE_NAME);
  upsertMeta("property", "og:title", routeSeo.title);
  upsertMeta("property", "og:description", routeSeo.description);
  upsertMeta("property", "og:url", canonicalUrl);
  upsertMeta("property", "og:image", ogImageUrl);
  upsertMeta("name", "twitter:card", "summary_large_image");
  upsertMeta("name", "twitter:title", routeSeo.title);
  upsertMeta("name", "twitter:description", routeSeo.description);
  upsertMeta("name", "twitter:image", ogImageUrl);
  upsertLink("canonical", canonicalUrl);
  updateStructuredData(getStructuredDataForPath(siteUrl, pathname));
}

/** 라우트 변경마다 title, canonical, OG/Twitter 메타를 동기화한다. */
export function SeoManager() {
  const location = useLocation();

  useEffect(() => {
    applyRouteSeo(location.pathname);
  }, [location.pathname]);

  return null;
}
