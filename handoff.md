Done
- `04_design_renewal` 비홈 리디자인은 유지했고 홈 `/`은 그대로다.
- `ads.txt`를 Vite SEO 자산으로 추가했고 `seoVitePlugin.test.ts` RED-GREEN, `npm run build`로 `dist/ads.txt` 생성을 확인했다.

In Progress
- 최우선 과제: 프런트 재배포 후 운영 도메인 `ads.txt` 응답 검증
- 진행 상태: 로컬 테스트와 빌드는 통과했다. 다음 단계는 Vercel 프런트 재배포 후 `https://mathtohwp.vercel.app/ads.txt`가 plain text를 반환하는지 확인하고 애드센스 재크롤 반영을 기다리는 것이다.

Next
- 프런트 정적 빌드 재배포
- 운영 `ads.txt` 200 / `text/plain` 확인
- 필요 시 애드센스 등록 도메인과 canonical host(`mathtohwp`/`mathhwp`) 일치 여부 점검

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\seoVitePlugin.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\seoVitePlugin.test.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\seo\siteSeo.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\vercel.json`

Last State
- 백엔드/환경 변수 변경은 없다.
- 현재 운영 도메인 `/ads.txt`는 재배포 전까지 HTML fallback을 반환한다.
