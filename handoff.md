Done
- `04_design_renewal` 전역 라우트에 Microsoft Clarity(`w1jgubofnf`) 를 추가했고 `TrackingLayout` 에서 `ClarityTracker` 와 `GoogleAnalyticsTracker` 를 함께 마운트했다.
- `ClarityTracker` 비활성화 no-op, `StrictMode` 단일 script 삽입, 기존 GA 추적기 회귀, production build 를 로컬에서 확인했다.

In Progress
- 최우선 과제: 프런트 재배포로 Clarity 운영 반영
- 진행 상태: [ClarityTracker.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ClarityTracker.tsx), [microsoftClarity.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/microsoftClarity.ts), [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx) 반영 완료. `npm run test:run -- src/app/components/ClarityTracker.test.tsx src/app/components/GoogleAnalyticsTracker.test.tsx` 와 `npm run build` 는 통과했고 아직 운영 프런트 재배포는 하지 않았다.
- 다음 단계: 운영 프런트를 재배포한 뒤 실제 사이트에서 `https://www.clarity.ms/tag/w1jgubofnf` script 가 1회만 삽입되는지 확인한다.

Next
- HWPX 실문서 수동 QA
- `02_main/schemas/2026-03-25_ocr_verification_fields.sql` 운영 적용
- 프런트 재배포 후 Clarity 수집 확인

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\App.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.test.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\microsoftClarity.ts`
- `D:\03_PROJECT\05_mathOCR\docs\plans\2026-03-26-clarity-tracker-design.md`

Last State
- 신규 환경 변수와 백엔드 변경은 없다.
- Clarity 는 루트 라우트 레이아웃에서 전역 주입되며 `StrictMode` 중복 mount 에도 script 가 한 번만 들어가도록 처리했다.
- 실제 사이트 반영에는 프런트 정적 배포가 한 번 더 필요하다.
