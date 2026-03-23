# Hybrid HWPX Markdown Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 기존 HWPX 출력 안정성을 유지하면서 Markdown 병행 계약을 백엔드와 프런트에 추가하고, 이후 HwpForge section writer 전환의 기반을 마련한다.

**Architecture:** OCR/해설 결과는 기존 `ocr_text`, `explanation`, `mathml`을 유지한 채 `problem_markdown`, `explanation_markdown`, `markdown_version`을 병행 저장한다. 기존 canonical-template exporter는 그대로 두고, 프런트 미리보기와 export 가능 판정은 Markdown 필드를 우선 사용하되 구필드로 안전하게 fallback 한다.

**Tech Stack:** FastAPI, Pydantic, pytest, React, Vitest

---

### Task 1: Markdown 병행 계약 테스트 추가

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.test.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\store\jobMappers.test.ts`

**Step 1: Write the failing test**

```python
def test_run_pipeline_persists_markdown_outputs(monkeypatch):
    ...
```

```ts
it("renders markdown math preview from problemMarkdown first", () => {
  ...
})
```

**Step 2: Run test to verify it fails**

Run: `py -3 -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py -q`
Expected: FAIL because markdown fields do not exist

Run: `npm run test:run -- src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts`
Expected: FAIL because frontend mapper and preview do not understand markdown fields

**Step 3: Write minimal implementation**

- 백엔드/프런트 테스트가 요구하는 최소 필드와 렌더링 경로만 추가

**Step 4: Run test to verify it passes**

Run: `py -3 -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py -q`
Expected: PASS

Run: `npm run test:run -- src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts`
Expected: PASS

### Task 2: 백엔드 Markdown 병행 필드 구현

**Files:**
- Create: `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\markdown_contract.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\schema.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\orchestrator.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\repository.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\billing.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\specs\mvp1_openapi.yaml`
- Create: `D:\03_PROJECT\05_mathOCR\02_main\schemas\2026-03-23_markdown_output_fields.sql`

**Step 1: Write the failing test**

```python
def test_get_job_returns_problem_markdown_fields(monkeypatch):
    ...
```

**Step 2: Run test to verify it fails**

Run: `py -3 -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py -q`
Expected: FAIL because response model omits markdown fields

**Step 3: Write minimal implementation**

- Markdown bridge helper
- schema/repository/api/billing fallback 로직
- DB migration 추가

**Step 4: Run test to verify it passes**

Run: `py -3 -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py D:\03_PROJECT\05_mathOCR\02_main\tests\test_billing.py -q`
Expected: PASS

### Task 3: 프런트 Markdown 우선 렌더링 구현

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\api\jobApi.ts`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\store\jobStore.ts`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\store\jobMappers.ts`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\JobDetailPage.tsx`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\mathMarkupPreview.ts`

**Step 1: Write the failing test**

```ts
it("maps problem_markdown and explanation_markdown into region state", () => {
  ...
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts src/app/api/jobApi.test.ts`
Expected: FAIL because frontend types and preview parser still only know legacy fields

**Step 3: Write minimal implementation**

- API 타입 확장
- store/mappers fallback 로직
- `$...$`, `$$...$$`, `<math>...</math>` 공존 미리보기

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts src/app/api/jobApi.test.ts`
Expected: PASS

### Task 4: 회귀 검증과 handoff 정리

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\handoff.md`
- Modify: `D:\03_PROJECT\05_mathOCR\log.md`

**Step 1: Run focused backend verification**

Run: `py -3 -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py D:\03_PROJECT\05_mathOCR\02_main\tests\test_billing.py -q`
Expected: PASS

**Step 2: Run focused frontend verification**

Run: `npm run test:run -- src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts src/app/api/jobApi.test.ts`
Expected: PASS

**Step 3: Update handoff/log**

- 이번 단계에서 끝난 범위와 남은 HwpForge helper 전환 범위를 한국어로 기록
