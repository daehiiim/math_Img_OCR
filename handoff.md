Done
- `siteSeo`/`publicAppUrl`/`seoVitePlugin`에 legacy host 정규화를 추가해 `mathtohwp` 입력이 들어와도 SEO 자산과 공개 URL을 `mathhwp.vercel.app`로 고정했다.
- 회귀 테스트 4개 묶음과 stale `SITE_URL=mathtohwp...` 빌드 검증을 통과했다.
- 홈페이지 원본 head에 Naver Search Advisor 검증 메타 태그를 추가했고, placement 테스트와 프로덕션 빌드에서 반영을 확인했다.

In Progress
- 최우선 과제: 프런트 재배포 후 운영 `mathhwp.vercel.app`에서 sitemap/canonical 응답 재검증
- 진행 상태: 현재 운영 `https://mathhwp.vercel.app/sitemap.xml`과 runtime canonical은 아직 `mathtohwp`를 가리킨다. 코드 수정은 로컬 빌드/브라우저 검증까지 완료됐다.

Next
- Vercel 프런트 재배포
- Vercel 환경 변수 `SITE_URL`/`APP_URL`/`NEXT_PUBLIC_SITE_URL`에 legacy host가 남아 있으면 `https://mathhwp.vercel.app`로 정리
- 운영 `/sitemap.xml`의 `<loc>` 3개가 모두 `https://mathhwp.vercel.app/...`인지 확인
- 운영 홈 DOM canonical이 `https://mathhwp.vercel.app/`인지 확인 후 Search Console sitemap 재제출
- 운영 홈 page source에 `naver-site-verification` 메타 태그가 노출되는지 확인 후 Naver Search Advisor 검증 재시도

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\index.html`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\naverVerificationPlacement.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\seo\siteSeo.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\publicAppUrl.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\seoVitePlugin.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\seo\siteSeo.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\publicAppUrl.test.ts`

Last State
- 로컬 `npm run build`는 stale `SITE_URL=mathtohwp...` 조건에서도 `dist/robots.txt`, `dist/sitemap.xml`, runtime canonical을 모두 `mathhwp`로 생성했다.
- 로컬 `npm run test:run -- src/app/naverVerificationPlacement.test.ts src/app/googleAnalyticsPlacement.test.ts src/app/adsensePlacement.test.ts`는 `4 passed`였다.
- 로컬 `npm run build` 산출물 `dist/index.html`에도 Naver 검증 메타 태그가 포함됐다.
- 배포 환경 반영 전까지 Search Console의 `Couldn't fetch`는 지속될 수 있다.
- 백엔드 코드 변경은 없지만, 실제 로그인/결제 복귀 URL 일관성을 위해 프런트 공개 URL 환경값도 함께 정리하는 편이 안전하다.
