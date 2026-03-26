Done
- `04_design_renewal` 최근 디자인 리뉴얼 화면을 디자인 변경 전 스타일 기준으로 롤백했다.
- `PublicHomePage`, `/login`, `/pricing`, `/payment/:planId`, `/connect-openai`, `/new`, `/workspace`, `/workspace/job/:jobId`, `*`, shell(`AuthLayout`, `StudioLayout`, `Layout`, `AppSidebar`, `AccountSheet`)을 이전 UI로 복원했다.
- 미사용 `src/app/components/shared/*` 를 삭제했고 `npm run test:run` 134 passed, `npm run build` 가 통과했다.

In Progress
- 최우선 과제: 복원된 구버전 UI의 실브라우저 smoke QA와 재배포 판단
- 진행 상태: 디자인은 이전 스타일로 되돌렸고 `MathHWP` 표기와 현재 도메인 계약은 유지했다. 다음 단계는 실제 브라우저에서 홈 첫 화면과 주요 라우트 전환이 기대대로 보이는지 확인하는 것이다.

Next
- 홈 첫 화면, `/login`, `/pricing`, `/payment/:planId`, `/new`, `/workspace` 수동 시각 QA
- auth/billing redirect (`returnTo`, `resumeDraft`, `checkout`, `checkout_id`) 실브라우저 점검
- 운영 프런트 재배포 및 배포본 확인

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\LoginPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PricingPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PaymentPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\Layout.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\index.html`

Last State
- SEO/runtime 계약(`SeoManager`, `siteSeo`, 공개 앱 URL`)은 유지했다.
- backend/env 계약 변경은 없다.
- build 경고는 기존 번들 크기 경고만 남아 있다.
