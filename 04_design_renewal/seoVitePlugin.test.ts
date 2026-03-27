import { describe, expect, it, vi } from "vitest";

import { createSeoVitePlugin } from "./seoVitePlugin";

type EmittedAsset = {
  fileName: string;
  source: string;
  type: "asset";
};

/** SEO 플러그인이 번들에 추가한 정적 자산 목록을 수집한다. */
function collectGeneratedAssets(): EmittedAsset[] {
  const assets: EmittedAsset[] = [];
  const legacySiteUrl = "https://mathhwp.vercel.app".replace("mathhwp", "mathtohwp");
  const plugin = createSeoVitePlugin({
    siteUrl: legacySiteUrl,
    googleSiteVerification: "",
  });

  plugin.generateBundle?.call({
    emitFile(asset: EmittedAsset) {
      assets.push(asset);
      return asset.fileName;
    },
  } as never);

  return assets;
}

describe("seoVitePlugin", () => {
  it("SEO 플러그인은 ads.txt를 배포 자산으로 생성한다", () => {
    const assets = collectGeneratedAssets();

    expect(assets).toContainEqual({
      type: "asset",
      fileName: "ads.txt",
      source: "google.com, pub-4088422118336195, DIRECT, f08c47fec0942fa0",
    });
  });

  it("legacy host가 들어와도 robots와 sitemap은 canonical host로 생성한다", () => {
    const assets = collectGeneratedAssets();
    const robotsAsset = assets.find((asset) => asset.fileName === "robots.txt");
    const sitemapAsset = assets.find((asset) => asset.fileName === "sitemap.xml");
    const legacyHostname = new URL("https://mathhwp.vercel.app".replace("mathhwp", "mathtohwp")).hostname;

    expect(robotsAsset?.source).toContain("https://mathhwp.vercel.app/sitemap.xml");
    expect(robotsAsset?.source).not.toContain(legacyHostname);
    expect(sitemapAsset?.source).toContain("<loc>https://mathhwp.vercel.app/</loc>");
    expect(sitemapAsset?.source).not.toContain(legacyHostname);
  });
});
