Done
- `04_design_renewal` 비홈 라우트(`/login`, `/pricing`, `/payment/:planId`, `/connect-openai`, `/new`, `/workspace`, `/workspace/job/:jobId`, `*`)와 shell(`AuthLayout`, `StudioLayout`, `Layout`, `AppSidebar`, `AccountSheet`)을 shared shadcn 조합 기준으로 리팩터했다.
- `src/app/components/shared/*` 에 `PageIntro`, `StatusPanel`, `UserCreditPill`, `PlanCard`, `CheckoutSummaryCard`, `PaymentMethodSelector`, `ExecutionOptionsPanel`, `RegionWorkspaceShell`, `JobListItemCard`, `PipelineProgressHeader`, `ResultRegionCard` 를 추가했다.
- `npm run test:run` 138개 테스트와 `npm run build` 가 통과했다.

In Progress
- 최우선 과제: 비홈 페이지 UI 리팩터 후 수동 smoke QA와 배포 판단
- 진행 상태: 라우트/API/store/query 계약은 유지했고, 공유 presentation layer로 렌더링만 정리했다. 다음 단계는 `/login`, `/pricing`, `/payment/:planId`, `/connect-openai`, `/new`, `/workspace`, `/workspace/job/:jobId`, `*` 에서 실제 브라우저 상호작용과 반응형 포커스 이동을 확인하는 것이다.

Next
- 비홈 라우트 8개 수동 시각 QA
- auth/billing redirect (`returnTo`, `resumeDraft`, `checkout`, `checkout_id`) 실브라우저 점검
- 운영 프런트 재배포 필요 여부 결정 및 기존 SEO/analytics 반영분과 함께 묶어서 확인

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\shared\`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\LoginPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PricingPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PaymentPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\OpenAiConnectionPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\NewJobPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\DashboardPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\JobDetailPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.tsx`

Last State
- 홈/랜딩 `PublicHomePage.tsx` 와 route contract 는 건드리지 않았다.
- backend/env 계약 변경은 없고 배포 환경 영향도 없다.
- build 경고는 기존 번들 크기 경고만 남아 있으며 테스트/빌드 실패는 없다.
