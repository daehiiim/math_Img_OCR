# 비홈 리퀴드 글라스 리디자인 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 홈(`/`)을 제외한 전 라우트를 흰색 기반의 리퀴드 글라스 + 옅은 블루 포인트 + Pretendard 전역 폰트 시스템으로 리디자인한다.

**Architecture:** 비홈 전용 시각 시스템을 [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css) 의 `liquid-shell` 스코프 안에서 다시 정의하고, 공통 레이아웃과 UI primitive를 먼저 정리한 뒤 페이지를 순차적으로 얹는다. 비즈니스 로직과 라우트 구조는 유지하고, 레이아웃/타이포/표면 질감만 단계적으로 교체한다.

**Tech Stack:** React, TypeScript, Tailwind CSS v4, Radix UI, Vite, Vitest, Testing Library

---

### Task 1: Pretendard self-host 폰트 파이프라인 고정

**Files:**
- Create: `D:\03_PROJECT\05_mathOCR\04_design_renewal\public\fonts\PretendardVariable.woff2`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\fonts.css`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\theme.css`

**Skill fit:**
- `frontend-design`

**Step 1: Write the failing test**

- `fonts.css` 에 Pretendard `@font-face` 가 없고, `theme.css` 의 전역 stack이 아직 Pretendard 기준이 아닌 상태를 확인하는 파일 기반 테스트를 추가한다.
- 필요하면 `src/app/fontPlacement.test.ts` 를 만들어 `fonts.css` 에 `Pretendard`와 self-host 경로가 존재하는지 검증한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/fontPlacement.test.ts`

Expected: `Pretendard` 또는 self-host 경로 미존재로 FAIL

**Step 3: Write minimal implementation**

- `PretendardVariable.woff2` 를 `public/fonts/` 에 추가한다.
- [fonts.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/fonts.css) 에 `@font-face` 를 선언한다.
- [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css) 의 전역 sans stack을 Pretendard 우선순위로 바꾼다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/fontPlacement.test.ts`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/public/fonts/PretendardVariable.woff2 04_design_renewal/src/styles/fonts.css 04_design_renewal/src/styles/theme.css 04_design_renewal/src/app/fontPlacement.test.ts
git commit -m "feat: add self-hosted pretendard font stack"
```

### Task 2: 비홈 전역 토큰과 글라스 표면 재정의

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\theme.css`

**Skill fit:**
- `frontend-design`

**Step 1: Write the failing test**

- 기존 [Layout.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.test.tsx), [AuthLayout.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AuthLayout.test.tsx), [StudioLayout.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/StudioLayout.test.tsx) 에 새 shell class 또는 구조 계약을 추가한다.
- 예: 공통 shell 내부에 `liquid-shell--workspace`, `liquid-shell--auth`, `liquid-shell--studio` 가 유지되고, 비홈 전용 래퍼가 홈과 분리된다는 기대값을 더 강화한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/Layout.test.tsx src/app/components/AuthLayout.test.tsx src/app/components/StudioLayout.test.tsx`

Expected: 새 구조 계약과 스타일 훅이 없어서 FAIL

**Step 3: Write minimal implementation**

- [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css) 의 `liquid-shell`, `liquid-header-shell`, `liquid-sidebar-shell`, `liquid-frost-panel`, `liquid-inline-note`, `liquid-stat-orb`, `button`, `input`, `badge`, `tabs`, `sheet`, `dropdown` 계열 토큰을 화이트/아이스블루 방향으로 재정의한다.
- 배경, 그림자, stroke, blur 강도를 한 체계 안에서 정리한다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/Layout.test.tsx src/app/components/AuthLayout.test.tsx src/app/components/StudioLayout.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/src/styles/theme.css 04_design_renewal/src/app/components/Layout.test.tsx 04_design_renewal/src/app/components/AuthLayout.test.tsx 04_design_renewal/src/app/components/StudioLayout.test.tsx
git commit -m "feat: redefine non-home liquid glass theme tokens"
```

### Task 3: 공통 셸과 사이드바를 새 언어로 재구성

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\Layout.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\StudioLayout.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\AuthLayout.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\AppSidebar.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\AccountSheet.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\Layout.test.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\AuthLayout.test.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\StudioLayout.test.tsx`

**Skill fit:**
- `frontend-design`
- `vercel-react-best-practices`

**Step 1: Write the failing test**

- 헤더 상태칩, 사이드바 내비게이션, 계정 시트의 새 계층 구조를 테스트에 반영한다.
- 주요 CTA와 계정 메뉴가 유지되는지 검증한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/Layout.test.tsx src/app/components/AuthLayout.test.tsx src/app/components/StudioLayout.test.tsx`

Expected: 구조 변경 기대값 때문에 FAIL

**Step 3: Write minimal implementation**

- 상단 헤더와 사이드바를 `pill + floating panel` 방향으로 정리한다.
- 계정 시트 내부 정보 구조를 `요약 -> 상태 -> 액션` 순서로 재배치한다.
- 키보드 포커스, aria-label, 내비게이션 계약은 유지한다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/Layout.test.tsx src/app/components/AuthLayout.test.tsx src/app/components/StudioLayout.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/src/app/components/Layout.tsx 04_design_renewal/src/app/components/StudioLayout.tsx 04_design_renewal/src/app/components/AuthLayout.tsx 04_design_renewal/src/app/components/AppSidebar.tsx 04_design_renewal/src/app/components/AccountSheet.tsx 04_design_renewal/src/app/components/Layout.test.tsx 04_design_renewal/src/app/components/AuthLayout.test.tsx 04_design_renewal/src/app/components/StudioLayout.test.tsx
git commit -m "feat: refresh non-home layout shell and sidebar"
```

### Task 4: UI primitive를 리퀴드 글라스 규칙에 맞춘다

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ui\button.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ui\card.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ui\input.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ui\badge.tsx`
- Modify if needed: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ui\tabs.tsx`
- Modify if needed: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ui\sheet.tsx`

**Skill fit:**
- `frontend-design`

**Step 1: Write the failing test**

- 기존 버튼/배지 계약 테스트에 `data-slot`, variant, 크기 클래스 유지 여부를 보강한다.
- 필요하면 `src/app/components/ui/button.test.tsx` 같은 primitive 테스트를 추가한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/ui/button.test.tsx src/app/components/ui/badge.test.tsx`

Expected: 새 contract 미반영으로 FAIL

**Step 3: Write minimal implementation**

- primitive 내부 variant class를 새 토큰과 자연스럽게 맞물리게 조정한다.
- 페이지에서 반복적으로 쓰는 개별 스타일 해킹을 줄인다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/ui/button.test.tsx src/app/components/ui/badge.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/src/app/components/ui/button.tsx 04_design_renewal/src/app/components/ui/card.tsx 04_design_renewal/src/app/components/ui/input.tsx 04_design_renewal/src/app/components/ui/badge.tsx 04_design_renewal/src/app/components/ui/tabs.tsx 04_design_renewal/src/app/components/ui/sheet.tsx 04_design_renewal/src/app/components/ui/button.test.tsx 04_design_renewal/src/app/components/ui/badge.test.tsx
git commit -m "feat: align ui primitives with liquid glass system"
```

### Task 5: `/workspace` 대시보드를 새 정보 위계로 재구성

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\DashboardPage.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\DashboardPage.test.tsx`

**Skill fit:**
- `frontend-design`
- `vercel-react-best-practices`

**Step 1: Write the failing test**

- 상단 요약 바, CTA, 작업 목록 row 위계에 대한 새 기대값을 테스트에 추가한다.
- 기존 크레딧/연결 상태 계약은 그대로 유지한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/DashboardPage.test.tsx`

Expected: 구조/텍스트 변경 기대값 때문에 FAIL

**Step 3: Write minimal implementation**

- 카드 4개 균일 배열을 줄이고 요약 strip + metric tile + 작업 row 구조로 재배치한다.
- 작업 row는 더 얇은 글라스 surface와 pill 상태 배지 중심으로 정리한다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/DashboardPage.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/src/app/components/DashboardPage.tsx 04_design_renewal/src/app/components/DashboardPage.test.tsx
git commit -m "feat: redesign workspace dashboard hierarchy"
```

### Task 6: `/new` 작업 생성 화면을 캔버스 중심으로 재배치

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\NewJobPage.tsx`
- Modify if needed: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\RegionEditor.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\NewJobPage.test.tsx`
- Test if needed: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\RegionEditor.test.tsx`

**Skill fit:**
- `frontend-design`
- `web-design-guidelines`

**Step 1: Write the failing test**

- 업로드, 영역 지정, 실행 CTA가 새 레이아웃에서도 유지된다는 계약을 추가한다.
- 드래프트 저장, 로그인 유도, 결제 유도 같은 기존 흐름 테스트는 유지한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/NewJobPage.test.tsx src/app/components/RegionEditor.test.tsx`

Expected: 새 구조 기대값 때문에 FAIL

**Step 3: Write minimal implementation**

- 업로드 panel과 영역 캔버스를 크게 보이게 하고, 실행 관련 옵션은 오른쪽 도크 또는 하단 고정 action panel로 정리한다.
- 상태 캡슐, 선택 영역 요약, 경고 문구를 얇은 글라스 pill 언어로 통일한다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/NewJobPage.test.tsx src/app/components/RegionEditor.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/src/app/components/NewJobPage.tsx 04_design_renewal/src/app/components/RegionEditor.tsx 04_design_renewal/src/app/components/NewJobPage.test.tsx 04_design_renewal/src/app/components/RegionEditor.test.tsx
git commit -m "feat: redesign new job canvas workflow"
```

### Task 7: 작업 상세와 결과 화면을 상태 중심으로 정리

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\JobDetailPage.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\JobDetailPage.test.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.test.tsx`

**Skill fit:**
- `frontend-design`
- `web-design-guidelines`

**Step 1: Write the failing test**

- 상단 상태 영역, 결과 영역, 보조 액션 영역이 새 구조로 렌더된다는 기대값을 추가한다.
- 기존 export, 경고 배지, 실행 상태 계약은 유지한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/JobDetailPage.test.tsx src/app/components/ResultsViewer.test.tsx`

Expected: 새 layout contract 부재로 FAIL

**Step 3: Write minimal implementation**

- 상단 job meta와 상태 배지를 압축된 pill cluster로 정리한다.
- 결과 preview 영역을 가장 큰 panel로 올리고, API 참조와 보조 정보는 시각적 비중을 낮춘다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/JobDetailPage.test.tsx src/app/components/ResultsViewer.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/src/app/components/JobDetailPage.tsx 04_design_renewal/src/app/components/ResultsViewer.tsx 04_design_renewal/src/app/components/JobDetailPage.test.tsx 04_design_renewal/src/app/components/ResultsViewer.test.tsx
git commit -m "feat: redesign job detail and result surfaces"
```

### Task 8: 인증/결제/설정 화면을 동일한 언어로 통일

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\LoginPage.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PricingPage.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PaymentPage.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\OpenAiConnectionPage.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\NotFoundPage.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\LoginPage.test.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PricingPage.test.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PaymentPage.test.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\OpenAiConnectionPage.test.tsx`

**Skill fit:**
- `frontend-design`

**Step 1: Write the failing test**

- 로그인/가격/결제/OpenAI 연결 페이지에서 핵심 CTA와 문구는 유지하되, 새 visual section heading이나 helper text 구조를 기대하도록 테스트를 갱신한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/LoginPage.test.tsx src/app/components/PricingPage.test.tsx src/app/components/PaymentPage.test.tsx src/app/components/OpenAiConnectionPage.test.tsx`

Expected: 새 구조 기대값 때문에 FAIL

**Step 3: Write minimal implementation**

- 중앙 카드 1장 패턴은 유지하되 내부를 더 얇고 넓은 `floating panel` 중심으로 정리한다.
- 가격표는 판매 카드 느낌보다 plan selector surface 느낌으로 바꾼다.
- 404도 전체 테마와 어긋나지 않게 간결한 글라스 상태 화면으로 맞춘다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/LoginPage.test.tsx src/app/components/PricingPage.test.tsx src/app/components/PaymentPage.test.tsx src/app/components/OpenAiConnectionPage.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add 04_design_renewal/src/app/components/LoginPage.tsx 04_design_renewal/src/app/components/PricingPage.tsx 04_design_renewal/src/app/components/PaymentPage.tsx 04_design_renewal/src/app/components/OpenAiConnectionPage.tsx 04_design_renewal/src/app/components/NotFoundPage.tsx 04_design_renewal/src/app/components/LoginPage.test.tsx 04_design_renewal/src/app/components/PricingPage.test.tsx 04_design_renewal/src/app/components/PaymentPage.test.tsx 04_design_renewal/src/app/components/OpenAiConnectionPage.test.tsx
git commit -m "feat: unify auth and billing surfaces"
```

### Task 9: 접근성, 회귀, 기록을 마무리

**Files:**
- Modify if needed: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\*.test.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\handoff.md`
- Modify: `D:\03_PROJECT\05_mathOCR\log.md`

**Skill fit:**
- `web-design-guidelines`
- `verification-before-completion`

**Step 1: Run targeted page tests**

Run: `npm run test:run -- src/app/components/Layout.test.tsx src/app/components/AuthLayout.test.tsx src/app/components/StudioLayout.test.tsx src/app/components/DashboardPage.test.tsx src/app/components/NewJobPage.test.tsx src/app/components/RegionEditor.test.tsx src/app/components/JobDetailPage.test.tsx src/app/components/ResultsViewer.test.tsx src/app/components/LoginPage.test.tsx src/app/components/PricingPage.test.tsx src/app/components/PaymentPage.test.tsx src/app/components/OpenAiConnectionPage.test.tsx`

Expected: PASS

**Step 2: Run full frontend test suite**

Run: `npm run test:run`

Expected: PASS

**Step 3: Run production build**

Run: `npm run build`

Expected: PASS, 기존 chunk size warning 외 신규 오류 없음

**Step 4: Update project records**

- [log.md](/D:/03_PROJECT/05_mathOCR/log.md) 에 변경 목적, 주요 파일, 검증 결과를 한국어로 남긴다.
- 다음 작업 방향이 바뀌었으면 [handoff.md](/D:/03_PROJECT/05_mathOCR/handoff.md) 를 덮어쓴다.

**Step 5: Commit**

```bash
git add 04_design_renewal handoff.md log.md
git commit -m "feat: ship non-home liquid glass redesign"
```
