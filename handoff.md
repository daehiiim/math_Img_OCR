Done
- 비홈 리퀴드 글라스 리디자인의 공통 토큰, Pretendard self-host, 공통 셸, UI primitive를 반영했다.
- `/workspace`, `/new`, `/pricing`, `/payment/:planId`, `/login`, `/connect-openai`, `NotFoundPage`를 화이트+아이스블루 glass 언어로 재구성했다.
- `/jobs/:jobId` 와 [`ResultsViewer.tsx`](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ResultsViewer.tsx) 도 상태 surface + 결과 보드 + 액션 도크 구조로 정리했다.
- 검증 완료: 전체 프런트 테스트 `40 files, 158 tests passed`, 프로덕션 빌드 `vite build` 통과.

In Progress
- 최우선 과제: 주요 비홈 라우트 실브라우저 시각 QA와 번들 chunk 경고 후속 검토
- 진행 상태: 구현/단위 회귀/전체 프런트 테스트/프로덕션 빌드는 완료됐고, 남은 일은 시각 검수와 선택적 성능 최적화다.
- 다음 단계: `/pricing`, `/payment/:planId`, `/login`, `/connect-openai`, `/workspace`, `/new`, `/jobs/:jobId` 를 브라우저에서 직접 확인하고 필요 시 chunk 분할 검토

Next
- `04_design_renewal/index.html` 의 Figma capture script 유지 여부 결정
- `.tmp` 삭제 흔적과 무관한 이번 프런트 변경분만 선별해 후속 커밋 범위를 정리
- `vite build` 의 `index-*.js 839 kB` chunk warning을 기준으로 라우트 분할 가능성 검토

Related Files
- `/D:/03_PROJECT/05_mathOCR/docs/plans/2026-04-02-non-home-liquid-glass-design.md`
- `/D:/03_PROJECT/05_mathOCR/docs/plans/2026-04-02-non-home-liquid-glass-plan.md`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/fonts.css`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/StudioLayout.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AuthLayout.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/DashboardPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PricingPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PaymentPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/LoginPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/OpenAiConnectionPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NotFoundPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx`
- `/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ResultsViewer.tsx`

Last State
- `2026-04-02 19:37 KST` 기준 홈(`/`) 제외 주요 라우트의 리퀴드 글라스 리디자인 구현은 완료됐다.
- 이번 단계는 프런트 전용 변경이며 백엔드/배포 환경 변수 변경은 없다.
- 테스트 증거: `JobDetail/ResultsViewer 18 passed`, 전체 프런트 `40 files 158 tests passed`, 프로덕션 빌드 통과
