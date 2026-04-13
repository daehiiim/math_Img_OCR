Done
- iPhone 14 기준 모바일 UI 정리 완료: 워크스페이스 모바일 헤더/우상단 메뉴, safe-area 반영, 주요 CTA 터치 타깃 확대를 적용했다.
- `/new`, `/login`, `/workspace`, `/jobs/:jobId` 문구/도크/사이드바/API 참조 제거 요구사항을 반영했다.
- 프런트 검증 완료: `npm.cmd run test:run` 기준 `41 files, 161 tests passed`, `npm.cmd run build` 통과.

In Progress
- 최우선 과제: Playwright MCP 복구 후 iPhone 14 실브라우저 시각 QA 재실행
- 진행 상태: 자동 테스트와 프로덕션 빌드는 모두 통과했고, 브라우저 메뉴 시트 시각 검수만 도구 세션 종료로 보류됐다.
- 다음 단계: `/login` → `/workspace` → 모바일 메뉴 열기 경로를 390x844 뷰포트에서 다시 확인하고 콘솔 에러 유무만 최종 체크

Next
- `assets/index-*.js` 837 kB chunk warning의 라우트 분할 여부 검토
- 이번 모바일 변경분만 기준으로 후속 커밋 범위 정리

Related Files
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/WorkspaceMobileMenu.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AppSidebar.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/LoginPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/RegionEditor.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ui/sheet.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.test.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ui/sheet.test.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/seo/siteSeo.ts
- /D:/03_PROJECT/05_mathOCR/error_patterns.md

Last State
- 2026-04-13 09:25 KST 기준 이번 단계는 프런트 전용 변경이며 백엔드/배포 환경 변수 변경은 없다.
- 시트 wrapper의 ref 안정성 규칙을 `error_patterns.md`에 추가했고, 열기/닫기 상호작용 회귀 테스트까지 포함했다.
