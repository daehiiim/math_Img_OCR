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
  const plugin = createSeoVitePlugin({
    siteUrl: "https://mathtohwp.vercel.app",
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
});
