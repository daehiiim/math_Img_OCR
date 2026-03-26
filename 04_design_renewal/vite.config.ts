import { defineConfig, loadEnv } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { DEFAULT_SITE_URL, resolveSeoSiteUrl } from './src/app/seo/siteSeo'
import { createSeoVitePlugin } from './seoVitePlugin'

// 셸 환경변수가 있으면 .env.local 보다 우선해서 API base 값을 고정한다.
function getDefinedApiBase(mode: string): string {
  const env = loadEnv(mode, __dirname, "");
  if (Object.prototype.hasOwnProperty.call(process.env, "VITE_API_BASE_URL")) {
    return process.env.VITE_API_BASE_URL ?? "";
  }

  return env.VITE_API_BASE_URL ?? "";
}

// 셸 환경변수와 env 파일에서 첫 번째 유효한 값을 읽는다.
function getDefinedEnvValue(mode: string, keys: string[]): string {
  const env = loadEnv(mode, __dirname, "");

  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(process.env, key)) {
      return process.env[key] ?? "";
    }
  }

  for (const key of keys) {
    if (env[key]) {
      return env[key];
    }
  }

  return "";
}

// canonical host는 SITE_URL 계열 변수를 우선으로 사용한다.
function getDefinedSiteUrl(mode: string): string {
  return resolveSeoSiteUrl(
    getDefinedEnvValue(mode, ["SITE_URL", "NEXT_PUBLIC_SITE_URL", "APP_URL"]),
    DEFAULT_SITE_URL
  );
}

// Search Console 검증 토큰은 공개/비공개 키 이름을 모두 허용한다.
function getDefinedGoogleSiteVerification(mode: string): string {
  return getDefinedEnvValue(mode, [
    "GOOGLE_SITE_VERIFICATION",
    "NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION",
    "VITE_GOOGLE_SITE_VERIFICATION",
  ]);
}

export default defineConfig(({ mode }) => ({
  define: {
    __MATH_OCR_VITE_API_BASE__: JSON.stringify(getDefinedApiBase(mode)),
    __MATH_OCR_PUBLIC_APP_URL__: JSON.stringify(getDefinedSiteUrl(mode)),
    __MATH_OCR_SITE_URL__: JSON.stringify(getDefinedSiteUrl(mode)),
    __MATH_OCR_GOOGLE_SITE_VERIFICATION__: JSON.stringify(getDefinedGoogleSiteVerification(mode)),
  },
  plugins: [
    // React 와 Tailwind 플러그인은 현재 빌드 계약의 일부다.
    react(),
    tailwindcss(),
    createSeoVitePlugin({
      siteUrl: getDefinedSiteUrl(mode),
      googleSiteVerification: getDefinedGoogleSiteVerification(mode),
    }),
  ],
  resolve: {
    alias: {
      // src 루트를 @ 경로로 고정한다.
      '@': path.resolve(__dirname, './src'),
    },
  },
  // raw import 를 허용할 파일만 명시한다.
  assetsInclude: ['**/*.svg', '**/*.csv'],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
}))
