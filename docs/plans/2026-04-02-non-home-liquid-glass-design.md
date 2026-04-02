# 비홈 화면 리퀴드 글라스 리디자인 설계

## 목표

홈(`/`)을 제외한 모든 화면을 `흰색 기반 + 옅은 푸른 포인트 + 반투명 글라스` 방향으로 재설계해, 현재의 묵직하고 촌스러운 인상을 걷어내고 더 가볍고 현대적인 제품 경험으로 전환한다.

## 범위

- 포함 라우트
  - `/new`
  - `/workspace`
  - `/workspace/job/:jobId`
  - `/login`
  - `/pricing`
  - `/payment/:planId`
  - `/connect-openai`
  - `404`
- 포함 공통 레이어
  - [Layout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.tsx)
  - [StudioLayout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/StudioLayout.tsx)
  - [AuthLayout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AuthLayout.tsx)
  - [AppSidebar.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AppSidebar.tsx)
  - [AccountSheet.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AccountSheet.tsx)
  - [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css)
  - [fonts.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/fonts.css)
- 제외
  - 홈(`/`)의 구조와 시각 방향
  - 백엔드 API, 인증, 결제, OCR 비즈니스 로직

## 현재 상태

- 비홈 화면은 이미 `liquid-*` 계열 공통 클래스를 사용하지만, 실제 시각 언어는 `세이지/그린` 계열과 두꺼운 카드 중심 구조에 가깝다.
- [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css) 에 색상, 글라스, 카드, 버튼, 입력 필드가 한 파일에 밀집되어 있어 디자인 의도는 있으나 질감이 통일되지 않는다.
- [fonts.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/fonts.css) 는 현재 `Noto Sans KR`만 로드한다.
- 홈은 다크 중심 브랜딩이고, 비홈은 밝은 리퀴드 글라스 계열이라도 충분히 공존 가능하다.

## 참고 이미지 해석

사용자가 제공한 레퍼런스의 핵심은 다음 네 가지다.

- 거의 흰색에 가까운 넓은 여백
- 둥글고 얇은 `pill` 네비게이션/컨트롤
- 무겁지 않은 유리 질감과 흐린 반사광
- 검은 텍스트 위에 아주 얇은 푸른색 포인트

이 질감을 그대로 제품 화면에 복제하면 작업 화면의 정보 밀도 때문에 가독성이 무너질 수 있다. 따라서 이번 설계는 레퍼런스의 `분위기`를 가져오되, 실제 제품 UI에서는 `컨트롤 캡슐`, `부유하는 상태 패널`, `얇은 보더`, `약한 블루 글로우` 중심으로 번역한다.

## 요구사항 해석

- 홈(`/`)은 유지하고, 나머지 모든 라우트만 새 테마를 적용한다.
- 글라스 강도는 과하지 않게 유지한다.
- 폰트는 전부 `Pretendard`로 통일하고 self-host 방식으로 넣는다.
- 롤아웃은 `공통 테마/레이아웃 -> 핵심 화면 -> 나머지 화면` 순으로 단계 적용한다.

## 접근 방식

### 권장안

공통 토큰, 공통 레이아웃, UI primitive, 페이지 레이아웃을 분리해 리디자인한다. 먼저 [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css) 와 [fonts.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/fonts.css) 에서 비홈 전용 시각 시스템을 다시 정의하고, 그 위에 공통 레이아웃과 페이지를 순서대로 얹는다.

### 대안 1

색상과 그림자만 수정하는 토큰 리스킨으로 끝낸다. 구현은 가장 빠르지만, 레이아웃 밀도와 컴포넌트 판형이 그대로라 체감 개선 폭이 작다.

### 대안 2

정보 구조까지 다시 짜는 전면 UX 재구성으로 간다. 결과는 가장 강하지만, 현재 범위에는 비용과 회귀 리스크가 과하다.

## 선택 이유

권장안은 시각 품질을 크게 끌어올리면서도 기존 라우트 구조와 비즈니스 로직을 건드리지 않는다. 또한 홈과 비홈의 세계관을 분리 유지하기 쉽고, 단계적 QA에도 유리하다.

## 아키텍처와 비즈니스 로직 구분

### 아키텍처

- 비홈 전용 디자인 시스템을 [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css) 의 `liquid-shell` 스코프 안에서 재정의한다.
- 공통 레이아웃은 `header`, `sidebar`, `sheet`, `panel`, `button`, `input`, `badge` 역할 단위로 나눠 스타일 책임을 명확히 한다.
- 페이지는 공통 shell 위에서 `요약 영역`, `컨트롤 영역`, `콘텐츠 영역`, `보조 상태 영역` 순으로 구조를 정리한다.

### 비즈니스 로직

- 인증, 결제, OCR 실행, 결과 표시, export는 모두 기존 흐름을 유지한다.
- 사용자가 체감하는 변화는 화면 구조, 밀도, 위계, 타이포, 표면 질감이다.

## 비주얼 시스템

### 색상

- 기본 배경은 `#f7fbff`에서 `#eef4fb`로 흐르는 아주 밝은 블루-화이트 그라데이션을 사용한다.
- 메인 텍스트는 짙은 네이비 계열, 보조 텍스트는 채도를 뺀 블루그레이 계열로 맞춘다.
- 강조색은 `#4da3ff` 전후의 차가운 블루로 제한한다.
- 성공/경고/오류 색도 채도를 약간 눌러 전체 톤을 깨지 않게 조정한다.

### 표면

- 글라스 표면은 `rgba(255,255,255,0.58~0.72)` 범위에서만 사용한다.
- 핵심 표면은 `header`, `sidebar`, `sheet`, `primary panel`, `summary strip` 에만 적용한다.
- 작은 리스트 아이템까지 모두 blur를 적용하지 않고, 내부 요소는 주로 얇은 보더와 반투명 fill로 정리한다.

### radius / shadow

- 버튼, 칩, 탭은 `pill` 또는 `24~999px radius`를 사용한다.
- 카드와 패널은 `28~36px` radius로 맞춘다.
- 그림자는 검은색보다 푸른 회색 그림자를 써서 무게감을 줄인다.

### 타이포

- 전역 폰트는 `Pretendard`로 통일한다.
- 큰 타이틀은 과한 display font 대신 `Pretendard`의 굵기, 자간, 줄간격으로 해결한다.
- 숫자와 ID는 필요한 곳만 `font-mono`를 유지한다.

## 라우트별 디자인 방향

### 작업실 공통 셸

- [Layout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.tsx)
- [AppSidebar.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AppSidebar.tsx)
- [AccountSheet.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AccountSheet.tsx)

사이드바를 두꺼운 패널처럼 보이게 하지 않고, 넓은 배경 위에 얇게 떠 있는 글라스 컬럼처럼 보이게 만든다. 계정 상태와 CTA는 작은 카드 묶음 대신 pill cluster로 단순화한다.

### 새 작업

- [NewJobPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx)
- [RegionEditor.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/RegionEditor.tsx)

업로드와 영역 지정은 가장 중요한 작업 화면이므로 `왼쪽 메인 캔버스 + 오른쪽 컨트롤 도크` 느낌으로 재정리한다. 업로드 dropzone은 “점선 박스”보다 부유하는 라이트 패널 느낌으로 바꾼다.

### 대시보드

- [DashboardPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/DashboardPage.tsx)

현재는 카드가 많고 위계가 균일하다. `상단 요약 바`, `핵심 지표 strip`, `작업 리스트 row`로 단계를 줄여 더 가볍게 만든다.

### 작업 상세 / 결과

- [JobDetailPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx)
- [ResultsViewer.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ResultsViewer.tsx)

진행 상태, 결과, API 정보가 현재 카드로 분산되어 있다. `상단 상태 배지`, `결과 중심 패널`, `보조 도구 패널` 구조로 압축하고, 상태 배지는 레퍼런스 이미지의 pill 언어를 적극적으로 쓴다.

### 인증 / 결제

- [AuthLayout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AuthLayout.tsx)
- [LoginPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/LoginPage.tsx)
- [PricingPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PricingPage.tsx)
- [PaymentPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PaymentPage.tsx)
- [OpenAiConnectionPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/OpenAiConnectionPage.tsx)
- [NotFoundPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NotFoundPage.tsx)

중앙 정렬 카드 한 장 패턴을 그대로 유지하되, 내부 레이아웃을 더 얇고 정교하게 바꾼다. 가격표는 “판매 카드”보다 “설정 가능한 plan surface”처럼 보여야 한다.

## 폰트 전략

- self-host 방식으로 `PretendardVariable.woff2` 또는 동급 자산을 `04_design_renewal/public/fonts/` 에 둔다.
- [fonts.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/fonts.css) 에 `@font-face` 를 선언한다.
- [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css) 의 `--font-ui-sans-stack`, `--font-landing-heading-stack`, `html`, `body`, utility class를 전부 Pretendard 기준으로 맞춘다.

## 성능과 접근성

- `backdrop-filter` 는 고정 헤더, 사이드바, sheet, 핵심 panel에만 적용한다.
- hover/entry animation은 2~3종만 유지해 시각적 일관성을 만든다.
- contrast는 흰색 배경 위 회색 텍스트가 너무 연해지지 않도록 최소 WCAG AA 수준을 목표로 맞춘다.
- 아이콘-only 버튼, 계정 메뉴, 작업 row 클릭 영역은 기존 접근성 계약을 유지한다.

## 에러 처리

### 예상 가능한 에러

- self-host 폰트 경로 누락 또는 build 누락
- blur, shadow, translucent surface 남발로 인한 모바일 성능 저하
- 인증/결제/작업 상세 화면에서 시각 구조가 바뀌며 테스트 계약이 깨지는 경우

### 사용자 메시지

- 폰트 로드 실패는 별도 사용자 메시지 없이 시스템 fallback sans로 안전하게 내려간다.
- 데이터 로드/결제/인증 오류 메시지는 기존 문구를 유지한다.

## 테스트 전략

- 레이아웃 컴포넌트 테스트에서 비홈 전용 shell class와 구조 계약을 고정한다.
- 페이지 테스트에서 핵심 CTA, 상태 배지, 설명 문구, 네비게이션 흐름이 유지되는지 확인한다.
- `npm run test:run` 전체와 `npm run build` 로 회귀를 막는다.
- 최종적으로 `/login`, `/pricing`, `/connect-openai`, `/new`, `/workspace`, `/workspace/job/:jobId` 실브라우저 QA를 한다.

## 스킬 적용 후보

- `frontend-design`: 토큰, 레이아웃, 페이지 시각 방향 구현
- `web-design-guidelines`: 접근성 및 인터랙션 품질 점검
- `vercel-react-best-practices`: React 컴포넌트 구조와 상태/렌더링 품질 점검

VibeIndex 기반 점검 결과, 이번 범위는 위 세션 내 스킬로 충분하며 추가 설치가 필수인 외부 스킬은 없었다.

## 배포 영향

이번 변경은 [04_design_renewal](/D:/03_PROJECT/05_mathOCR/04_design_renewal) 프런트 범위다. 백엔드 API, Cloud Run, 환경 변수 변경은 없다. 운영 반영에는 프런트 정적 빌드 재배포가 필요하다.
