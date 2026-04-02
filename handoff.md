Done
- 비홈 화면 리퀴드 글라스 리디자인 방향을 확정했고, 설계 문서와 구현 계획 문서를 작성했다.
- 홈(`/`) 제외 전 라우트, Pretendard self-host, 단계 적용 순서, 참고 이미지 해석 기준을 문서로 고정했다.
- 신규 로그인 사용자 `profile` 최초 생성 시 무료 3크레딧과 `signup_bonus` 원장을 남기도록 백엔드/스키마를 반영했다.

In Progress
- 최우선 과제: 비홈 화면 리퀴드 글라스 리디자인 구현 준비
- 진행 상태: 설계는 [2026-04-02-non-home-liquid-glass-design.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-04-02-non-home-liquid-glass-design.md), 구현 순서는 [2026-04-02-non-home-liquid-glass-plan.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-04-02-non-home-liquid-glass-plan.md) 로 정리했다.
- 다음 단계: Pretendard self-host 추가 -> 비홈 전역 토큰 교체 -> 공통 셸/primitive -> `/workspace`/`/new` -> 인증/결제 화면 순으로 구현

Next
- 운영 반영 시 `02_main/schemas/2026-04-02_signup_bonus.sql` 을 백엔드 배포 전에 먼저 적용
- `04_design_renewal/index.html` 에 남아 있는 Figma capture script 유지 여부 결정
- 기존 mobile auto_full QA와 새 비홈 리디자인 구현 일정 충돌 여부 조정

Related Files
- `D:\03_PROJECT\05_mathOCR\docs\plans\2026-04-02-non-home-liquid-glass-design.md`
- `D:\03_PROJECT\05_mathOCR\docs\plans\2026-04-02-non-home-liquid-glass-plan.md`
- `D:\03_PROJECT\05_mathOCR\docs\plans\2026-04-02-signup-bonus-design.md`
- `D:\03_PROJECT\05_mathOCR\docs\plans\2026-04-02-signup-bonus-plan.md`
- `D:\03_PROJECT\05_mathOCR\02_main\app\billing.py`
- `D:\03_PROJECT\05_mathOCR\02_main\schemas\2026-04-02_signup_bonus.sql`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_billing.py`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\fonts.css`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\theme.css`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\Layout.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\StudioLayout.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\AuthLayout.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\AppSidebar.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\DashboardPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\NewJobPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\JobDetailPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.tsx`

Last State
- `2026-04-02 18:48 KST` 기준 비홈 리디자인은 아직 구현 전이며, 신규 로그인 3크레딧 지급 백엔드 작업은 완료했다.
- signup bonus 반영에는 백엔드 코드와 Supabase 스키마가 함께 필요하고, 운영 반영 시 SQL 선적용 순서를 지켜야 한다.
- 현재 작업트리에는 사용자/이전 세션 변경과 `.tmp` 삭제 흔적이 많아, 구현 시 필요한 파일만 선별해서 건드려야 한다.
