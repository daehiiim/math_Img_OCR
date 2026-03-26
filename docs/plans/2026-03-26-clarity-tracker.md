# Clarity Tracker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 운영 프런트 전체 라우트에 Microsoft Clarity 스크립트를 중복 없이 주입한다.

**Architecture:** 기존 `GoogleAnalyticsTracker` 와 같은 전역 추적 레이어에 `ClarityTracker` 를 추가한다. 스크립트 삽입과 queue 초기화는 `microsoftClarity` 유틸로 분리해 테스트 가능성과 재사용성을 확보한다.

**Tech Stack:** React 18, TypeScript, React Router, Vite, Vitest, Testing Library

---

### Task 1: Clarity 유틸 계약 고정

**Files:**
- Create: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.test.tsx`
- Create: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\microsoftClarity.ts`

**Step 1: Write the failing test**

```tsx
it("StrictMode 에서도 Clarity 스크립트를 한 번만 삽입한다", () => {
  render(
    <StrictMode>
      <ClarityTracker enabled projectId="w1jgubofnf" />
    </StrictMode>
  );

  expect(document.head.querySelectorAll('script[src="https://www.clarity.ms/tag/w1jgubofnf"]')).toHaveLength(1);
});
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/ClarityTracker.test.tsx`
Expected: FAIL because `ClarityTracker` and `microsoftClarity` do not exist yet

**Step 3: Write minimal implementation**

```tsx
export function ClarityTracker() {
  useEffect(() => {
    appendMicrosoftClarityScript("w1jgubofnf");
  }, []);

  return null;
}
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/ClarityTracker.test.tsx`
Expected: PASS

### Task 2: 전역 앱 라우트에 연결

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\App.tsx`
- Test: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.test.tsx`

**Step 1: Write the failing test**

```tsx
it("비활성화면 스크립트를 삽입하지 않는다", () => {
  render(<ClarityTracker enabled={false} projectId="w1jgubofnf" />);
  expect(document.head.querySelectorAll("script")).toHaveLength(0);
});
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/ClarityTracker.test.tsx`
Expected: FAIL because enabled 분기와 reset 처리가 아직 없다

**Step 3: Write minimal implementation**

```tsx
if (!enabled || !projectId) {
  return null;
}
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/ClarityTracker.test.tsx`
Expected: PASS

### Task 3: 전체 검증

**Files:**
- Verify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ClarityTracker.tsx`
- Verify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\microsoftClarity.ts`
- Verify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\App.tsx`

**Step 1: Run focused tests**

Run: `npm run test:run -- src/app/components/ClarityTracker.test.tsx src/app/components/GoogleAnalyticsTracker.test.tsx`
Expected: PASS

**Step 2: Run app-level sanity check**

Run: `npm run build`
Expected: PASS

**Step 3: 기록 갱신**

Run: `git diff -- docs/plans/2026-03-26-clarity-tracker-design.md docs/plans/2026-03-26-clarity-tracker.md`
Expected: design and implementation notes match the code changes
