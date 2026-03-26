Done
- `04_design_renewal` 전역 라우트에 Microsoft Clarity(`w1jgubofnf`) 를 추가했고 `TrackingLayout` 에서 `ClarityTracker` 와 `GoogleAnalyticsTracker` 를 함께 마운트했다.
- `04_design_renewal` AdSense(`ca-pub-4088422118336195`) 로더를 [`index.html`](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html) head 직접 삽입으로 교체했고 검증 테스트를 고정했다.
- `04_design_renewal` Google Analytics(`G-SM6ETGCFGP`) 를 [`index.html`](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html) `<head>` 바로 다음에 가이드 원문 그대로 삽입했고, `GoogleAnalyticsTracker` 는 SPA 라우트 변경 추적만 담당하도록 정리했다.
- Clarity 운영 수집은 정상(`b.clarity.ms/collect` 204)으로 확인돼 이번 턴에는 코드 변경하지 않았다.

In Progress
- 최우선 과제: 프런트 재배포로 GA4/Clarity/AdSense 운영 반영
- 진행 상태: [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html), [GoogleAnalyticsTracker.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.tsx), [googleAnalytics.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/googleAnalytics.ts), [googleAnalyticsPlacement.test.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/googleAnalyticsPlacement.test.ts), [GoogleAnalyticsTracker.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.test.tsx) 반영 완료. `npm run test:run -- src/app/googleAnalyticsPlacement.test.ts src/app/components/GoogleAnalyticsTracker.test.tsx src/app/adsensePlacement.test.ts` 와 `npm run build` 는 통과했고 아직 운영 프런트 재배포는 하지 않았다.
- 다음 단계: 운영 프런트를 재배포한 뒤 실제 사이트에서 페이지 소스의 GA 스니펫, `https://www.google-analytics.com/g/collect?...tid=G-SM6ETGCFGP`, `https://www.clarity.ms/tag/w1jgubofnf`, `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4088422118336195` 를 확인한다.

Next
- HWPX 실문서 수동 QA
- `02_main/schemas/2026-03-25_ocr_verification_fields.sql` 운영 적용
- 프런트 재배포 후 GA4/Clarity/AdSense 운영 수집 확인

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\index.html`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\GoogleAnalyticsTracker.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\GoogleAnalyticsTracker.test.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\googleAnalyticsPlacement.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\adsensePlacement.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.test.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\googleAnalytics.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\microsoftClarity.ts`
- `D:\03_PROJECT\05_mathOCR\docs\plans\2026-03-26-clarity-tracker-design.md`

Last State
- 신규 환경 변수와 백엔드 변경은 없다.
- Clarity 는 루트 라우트 레이아웃에서 전역 주입되고, AdSense 와 GA4 는 공급자 요구에 맞춰 배포 HTML head 에 직접 삽입된다.
- 실제 사이트 반영에는 프런트 정적 배포가 한 번 더 필요하다.
