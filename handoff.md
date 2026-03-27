Done
- `siteSeo`/`publicAppUrl`/`seoVitePlugin`의 legacy host 정규화와 Naver verification head 삽입을 유지한 상태로 `/rss.xml` 생성까지 추가했다.
- `siteSeo`는 공개 페이지 3개(`/`, `/new`, `/pricing`)를 canonical host 기준 RSS item으로 생성하고, `seoVitePlugin`은 `ads.txt`/`robots.txt`/`sitemap.xml`/`rss.xml`을 함께 배포 자산으로 만든다.
- `index.html`에 RSS alternate 링크를 넣었고 `docs/seo.md`, `log.md`를 갱신했다.

In Progress
- 최우선 과제: 프런트 재배포 후 운영 `mathhwp.vercel.app`에서 canonical/sitemap/rss/naver meta 응답 재검증
- 진행 상태: 로컬 테스트와 빌드에서는 `dist/sitemap.xml`, `dist/rss.xml`, `dist/index.html`이 모두 `https://mathhwp.vercel.app` 기준으로 생성된다. 운영 반영은 아직 미확인이다.

Next
- Vercel 프런트 재배포
- Vercel 환경 변수 `SITE_URL`/`APP_URL`/`NEXT_PUBLIC_SITE_URL`에 legacy host가 남아 있으면 `https://mathhwp.vercel.app`로 정리
- 운영 `/sitemap.xml`의 `<loc>` 3개와 `/rss.xml`의 `channel/item link`가 모두 `https://mathhwp.vercel.app/...`인지 확인
- 운영 홈 DOM canonical이 `https://mathhwp.vercel.app/`인지 확인 후 Search Console sitemap 재제출
- 운영 홈 page source에 `naver-site-verification` 메타 태그와 RSS alternate 링크가 노출되는지 확인 후 Naver Search Advisor/RSS 제출 재시도

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\index.html`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\seo\siteSeo.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\seoVitePlugin.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\seo\siteSeo.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\seoVitePlugin.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\publicAppUrl.ts`
- `D:\03_PROJECT\05_mathOCR\docs\seo.md`

Last State
- 로컬 `npm run test:run -- src/app/seo/siteSeo.test.ts seoVitePlugin.test.ts src/app/naverVerificationPlacement.test.ts src/app/googleAnalyticsPlacement.test.ts src/app/adsensePlacement.test.ts`는 `16 passed`였다.
- 로컬 `npm run build`는 `dist/ads.txt`, `dist/robots.txt`, `dist/sitemap.xml`, `dist/rss.xml`, `dist/index.html`을 성공적으로 생성했다.
- `dist/rss.xml`의 self link는 `https://mathhwp.vercel.app/rss.xml`이고 item은 홈/새 작업/가격 안내 3개다.
- 배포 환경 반영 전까지 Search Console `Couldn't fetch`와 RSS 제출 실패는 계속될 수 있다.
