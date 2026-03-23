# 히어로 비디오 다크 루프 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 공개 홈 히어로 비디오를 항상 재생시키고, 밝은 후반부 대신 어두운 초반부만 반복 재생되게 만든다.

**Architecture:** 히어로 비디오 노출 조건을 단순화해 환경별 분기를 제거하고, 기존 이벤트 기반 구간 루프 구조는 유지한 채 시작/재시작 구간만 다크 루프로 옮긴다. 회귀 테스트를 먼저 수정해 새 계약을 고정한 뒤 최소 구현으로 통과시킨다.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, Vite

---

### Task 1: 테스트로 새 재생 계약 고정

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.test.tsx`

**Step 1: Write the failing test**

- 모바일 환경에서도 비디오가 렌더된다고 기대값을 바꾼다.
- `prefers-reduced-motion` 이 활성화돼도 비디오가 렌더된다고 기대값을 바꾼다.
- `loadedmetadata` 이후 시작 시간이 `0.3초` 근처인지 검증한다.
- `timeupdate` 시 재루프 기준이 `4.3초` 근처인지 검증한다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/PublicHomePage.test.tsx`

Expected: 기존 `viewport-blocked`, `reduced-motion`, `4.8초`, `5.7초` 계약 때문에 실패

### Task 2: 최소 구현으로 조건 제거

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.tsx`

**Step 3: Write minimal implementation**

- 히어로 비디오 렌더 조건에서 뷰포트와 `prefers-reduced-motion` 분기를 제거한다.
- 시작 시간과 재루프 시간을 어두운 초반 구간 값으로 옮긴다.
- 비디오 에러 시 poster 폴백은 유지한다.

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/PublicHomePage.test.tsx`

Expected: PASS

### Task 3: 기록과 최종 검증

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\log.md`
- Modify if needed: `D:\03_PROJECT\05_mathOCR\handoff.md`

**Step 5: Update project records**

- 변경 목적, 구간 값, 검증 결과를 한국어로 기록한다.
- 향후 작업 방향이 달라질 때만 `handoff.md` 를 덮어쓴다.

**Step 6: Run final verification**

Run: `npm run test:run -- src/app/components/PublicHomePage.test.tsx`
Run: `npm run build`

Expected: 둘 다 성공
