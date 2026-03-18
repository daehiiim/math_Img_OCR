// 미리보기용 SVG URL에 안전하게 version 파라미터를 반영한다.
export function buildAssetPreviewUrl(url: string, version?: number): string {
  if (!Number.isFinite(version)) {
    return url;
  }

  const [pathWithQuery, hash = ""] = url.split("#", 2);
  const [path, rawQuery = ""] = pathWithQuery.split("?", 2);
  const query = new URLSearchParams(rawQuery);
  query.set("v", String(version));

  const nextUrl = `${path}?${query.toString()}`;
  return hash ? `${nextUrl}#${hash}` : nextUrl;
}
