# SEO 변경 사항

## 무엇을 바꿨는가

- `04_design_renewal` 프런트가 Vite + React SPA임을 기준으로 SEO 구현을 정리했다.
- 홈 기본 메타를 [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html)에 추가했다.
  - title, description, canonical, Open Graph, Twitter, favicon
- 라우트 변경 시 메타를 갱신하는 [SeoManager.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/SeoManager.tsx)를 추가했다.
  - `/`, `/new`, `/pricing`는 index 대상
  - `/login`, `/payment/:planId`, `/connect-openai`, `/workspace*`, 404는 `noindex`
- SEO 규칙과 sitemap/robots 생성 로직을 [siteSeo.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/seo/siteSeo.ts)에 모았다.
- Vite 빌드 시 `robots.txt` 와 `sitemap.xml`을 실제 루트 파일로 생성하도록 [seoVitePlugin.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/seoVitePlugin.ts)를 추가했다.
- 홈페이지 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)를 검색 의도형 한국어 콘텐츠로 재작성했다.
  - 단일 H1
  - 소개 문단
  - 핵심 기능
  - 입력/출력 형식
  - 학생/교사/문서 작성자 활용 사례
  - FAQ
  - 개인정보·업로드 가이드
  - 크롤 가능한 내부 링크
- 정적 fallback HTML도 [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html)에 넣어 JS 렌더 이전에도 홈에 의미 있는 한국어 콘텐츠가 보이도록 했다.
- OG/Twitter 공유용 에셋을 추가했다.
  - [favicon.svg](/D:/03_PROJECT/05_mathOCR/04_design_renewal/public/favicon.svg)
  - [og-image.svg](/D:/03_PROJECT/05_mathOCR/04_design_renewal/public/og-image.svg)

## 환경 변수

- 권장 canonical host 변수
  - `SITE_URL`
- 호환 fallback
  - `NEXT_PUBLIC_SITE_URL`
  - `APP_URL`
- Google Search Console 검증 토큰
  - `GOOGLE_SITE_VERIFICATION`
  - `NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION`
  - `VITE_GOOGLE_SITE_VERIFICATION`

## 검증 토큰은 어디에 넣는가

- 배포 환경 변수에 검증 토큰 문자열만 넣는다.
- 예시:
  - `GOOGLE_SITE_VERIFICATION=abc123...`
- 빌드 시 `<meta name="google-site-verification" ...>` 가 자동 주입된다.

## 배포 후 수동 작업

1. 프런트 정적 빌드를 재배포한다.
2. 배포 사이트에서 다음 경로를 직접 확인한다.
   - `/robots.txt`
   - `/sitemap.xml`
3. Google Search Console에 `https://mathhwp.vercel.app` 또는 실제 custom domain을 속성으로 등록한다.
4. Search Console에서 sitemap 제출란에 `https://<도메인>/sitemap.xml` 을 넣는다.
5. URL 검사로 홈(`/`)과 주요 페이지(`/new`, `/pricing`)를 재색인 요청한다.

## 새 페이지 메타 추가 방법

1. [siteSeo.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/seo/siteSeo.ts)의 `getRouteSeo()`에 경로 규칙을 추가한다.
2. index 대상이면 `robots: "index,follow"`와 canonical path를 지정한다.
3. 비공개/내부 페이지면 `robots: "noindex,nofollow"`를 지정한다.
4. sitemap에 포함할 공개 페이지면 `PUBLIC_SITEMAP_PATHS`에 경로를 추가한다.
5. 홈처럼 구조화 데이터가 필요한 경우 `getStructuredDataForPath()`에서 경로별 payload를 확장한다.
