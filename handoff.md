Done
- `04_design_renewal` 전역 라우트에 Microsoft Clarity(`w1jgubofnf`) 를 추가했고 `TrackingLayout` 에서 `ClarityTracker` 와 `GoogleAnalyticsTracker` 를 함께 마운트했다.
- `ClarityTracker` 비활성화 no-op, `StrictMode` 단일 script 삽입, 기존 GA 추적기 회귀, production build 를 로컬에서 확인했다.
- `04_design_renewal` AdSense(`ca-pub-4088422118336195`) 로더를 React 런타임 주입에서 [`index.html`](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html) head 직접 삽입으로 교체했다.
- AdSense 검증 계약을 [`adsensePlacement.test.ts`](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/adsensePlacement.test.ts) 로 고정했고, 불필요해진 `AdSenseTracker`/`googleAdSense` 런타임 파일을 정리했다.

In Progress
- 최우선 과제: 프런트 재배포로 Clarity/AdSense 운영 반영
- 진행 상태: [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html), [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx), [adsensePlacement.test.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/adsensePlacement.test.ts) 반영 완료. `npm run test:run -- src/app/adsensePlacement.test.ts src/app/components/ClarityTracker.test.tsx src/app/components/GoogleAnalyticsTracker.test.tsx` 와 `npm run build` 는 통과했고 아직 운영 프런트 재배포는 하지 않았다.
- 다음 단계: 운영 프런트를 재배포한 뒤 실제 사이트에서 `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4088422118336195` 와 `https://www.clarity.ms/tag/w1jgubofnf` script 가 각각 1회만 삽입되는지 확인한다.

Next
- HWPX 실문서 수동 QA
- `02_main/schemas/2026-03-25_ocr_verification_fields.sql` 운영 적용
- 프런트 재배포 후 Clarity 수집 및 AdSense 로더 삽입 확인

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\index.html`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\App.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\adsensePlacement.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.test.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\microsoftClarity.ts`
- `D:\03_PROJECT\05_mathOCR\docs\plans\2026-03-26-clarity-tracker-design.md`

Last State
- 신규 환경 변수와 백엔드 변경은 없다.
- Clarity 는 루트 라우트 레이아웃에서 전역 주입되고, AdSense 는 공급자 요구에 맞춰 배포 HTML head 에 직접 삽입되도록 수정했다.
- 실제 사이트 반영에는 프런트 정적 배포가 한 번 더 필요하다.
