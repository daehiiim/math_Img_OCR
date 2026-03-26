import type { Plugin } from "vite";

import { buildRobotsTxt, buildSitemapXml } from "./src/app/seo/siteSeo";

type SeoAsset = {
  contentType: string;
  fileName: string;
  source: string;
};

type SeoVitePluginOptions = {
  googleSiteVerification: string;
  siteUrl: string;
};

/** 빌드와 개발 서버에서 동일하게 제공할 SEO 정적 자산 목록을 만든다. */
function buildSeoAssets(siteUrl: string): SeoAsset[] {
  return [
    { fileName: "robots.txt", source: buildRobotsTxt(siteUrl), contentType: "text/plain; charset=utf-8" },
    { fileName: "sitemap.xml", source: buildSitemapXml(siteUrl), contentType: "application/xml; charset=utf-8" },
  ];
}

/** index.html placeholder를 실제 canonical host로 교체한다. */
function replaceSiteUrlPlaceholders(html: string, siteUrl: string): string {
  return html.replaceAll("__MATHHWP_SITE_URL__", siteUrl);
}

/** Search Console 검증 토큰이 있을 때만 meta 태그를 head에 주입한다. */
function buildVerificationTags(token: string) {
  return token
    ? [{ tag: "meta", injectTo: "head" as const, attrs: { name: "google-site-verification", content: token } }]
    : [];
}

/** 개발 서버에서 robots와 sitemap을 HTML fallback 대신 직접 응답한다. */
function registerSeoMiddleware(server: Parameters<NonNullable<Plugin["configureServer"]>>[0], assets: SeoAsset[]) {
  server.middlewares.use((request, response, next) => {
    const targetAsset = assets.find((asset) => request.url === `/${asset.fileName}`);
    if (!targetAsset) {
      next();
      return;
    }

    response.setHeader("Content-Type", targetAsset.contentType);
    response.end(targetAsset.source);
  });
}

/** Vite 빌드와 dev 모두에서 동일한 SEO 자산을 노출하는 플러그인을 만든다. */
export function createSeoVitePlugin(options: SeoVitePluginOptions): Plugin {
  const seoAssets = buildSeoAssets(options.siteUrl);

  return {
    name: "mathhwp-seo-assets",
    transformIndexHtml(html) {
      return {
        html: replaceSiteUrlPlaceholders(html, options.siteUrl),
        tags: buildVerificationTags(options.googleSiteVerification),
      };
    },
    configureServer(server) {
      registerSeoMiddleware(server, seoAssets);
    },
    generateBundle() {
      seoAssets.forEach((asset) => {
        this.emitFile({ type: "asset", fileName: asset.fileName, source: asset.source });
      });
    },
  };
}
