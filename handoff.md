Done
- `04_design_renewal` 비홈 화면에 스코프 기반 리퀴드 글라스 테마를 적용했고 홈 첫 화면 `/`은 수정하지 않았다.
- `theme.css`, `AuthLayout`, `StudioLayout`, `Layout`, `AppSidebar`, `AccountSheet`, 인증/결제/작업실 주요 화면과 공용 프리미티브를 실버+세이지 톤으로 정리했다.
- `npm run test:run` 139 passed, `npm run build` 통과. 로컬 UI mock으로 `/`, `/login`, `/pricing`, `/payment/starter`, `/connect-openai`, `/new`, `/workspace`, `/workspace/job/:jobId` 스모크 QA를 확인했다.

In Progress
- 최우선 과제: 운영 반영 전 최종 시각 미세 조정 여부 판단
- 진행 상태: 홈 비영향, 주요 라우트 표시, 접근성 보정, 자동 검증까지 끝났다. 다음 단계는 사용자 피드백에 따라 색 농도/블러 강도만 미세 조정하거나 그대로 반영하는 것이다.

Next
- 필요 시 카드 대비, blur 강도, 세이지 포인트 채도 1차 미세 조정
- 필요 시 프런트 정적 빌드 재배포

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\theme.css`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\AuthLayout.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\Layout.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\StudioLayout.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PricingPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\DashboardPage.tsx`

Last State
- 공개 API, 라우트 계약, 인증/결제 동작, 백엔드/환경 변수는 변경하지 않았다.
- build 경고는 기존과 동일한 chunk size warning만 남아 있다.
