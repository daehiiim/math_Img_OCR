import { defineConfig, loadEnv } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

// 셸 환경변수가 있으면 .env.local 보다 우선해서 API base 값을 고정한다.
function getDefinedApiBase(mode: string): string {
  const env = loadEnv(mode, __dirname, "");
  if (Object.prototype.hasOwnProperty.call(process.env, "VITE_API_BASE_URL")) {
    return process.env.VITE_API_BASE_URL ?? "";
  }

  return env.VITE_API_BASE_URL ?? "";
}

// 셸 환경변수가 있으면 .env.local 보다 우선해서 공개 앱 URL을 고정한다.
function getDefinedAppUrl(mode: string): string {
  const env = loadEnv(mode, __dirname, "");
  if (Object.prototype.hasOwnProperty.call(process.env, "APP_URL")) {
    return process.env.APP_URL ?? "";
  }

  return env.APP_URL ?? "";
}

export default defineConfig(({ mode }) => ({
  define: {
    __MATH_OCR_VITE_API_BASE__: JSON.stringify(getDefinedApiBase(mode)),
    __MATH_OCR_PUBLIC_APP_URL__: JSON.stringify(getDefinedAppUrl(mode)),
  },
  plugins: [
    // React 와 Tailwind 플러그인은 현재 빌드 계약의 일부다.
    react(),
    tailwindcss(),
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
