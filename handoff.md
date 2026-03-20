Done
- `exporter.py`가 canonical source로 `/D:/03_PROJECT/05_mathOCR/templates/style_guide.hwpx`를 직접 풀어 쓰도록 바꿨다.
- 공개 홈 `/` 랜딩을 Apple식 sans-first 톤으로 재정렬했고 `PublicHomePage.tsx`, `fonts.css`, `theme.css`, `PublicHomePage.test.tsx`를 갱신했다.
- 공개 홈 회귀 검증: `npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `4 passed`, `npm run build` 성공

In Progress
- 최우선 과제: 공개 홈 sans 리디자인 마감 점검
- 진행 상태: serif 초안을 철회하고 hero/섹션 타이틀/오브제를 sans로 재구성했으며 데스크톱·모바일 수동 확인까지 끝냈다
- 다음 단계: 사용자 추가 피드백이 오면 카피 밀도와 간격만 미세 조정한다

Next
- 필요 시 공개 홈 전체 회귀 범위를 `App.tsx` 진입 기준으로 넓혀 로그인/새 작업/가격 동선을 추가 점검
- 한글에서 canonical export 산출물 육안 검증도 별도 후속 과제로 남아 있다

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.test.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\fonts.css`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\theme.css`

Last State
- `cd D:\03_PROJECT\05_mathOCR\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `4 passed`
- `cd D:\03_PROJECT\05_mathOCR\04_design_renewal && npm run build` -> 성공
- 공개 홈 수동 확인: `1440px`, `390px` viewport에서 헤드라인 줄바꿈과 CTA 노출 정상
- 배포 환경 변경 없음
