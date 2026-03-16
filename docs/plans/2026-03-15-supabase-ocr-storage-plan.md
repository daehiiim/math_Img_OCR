# Supabase OCR Storage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `02_main`의 OCR 저장 구조를 Supabase DB + Storage 중심으로 전환하고 프런트 인증 토큰 전달까지 연결한다.

**Architecture:** FastAPI는 Supabase JWT를 검증한 뒤 사용자 토큰으로 `rest/v1`와 `storage/v1`를 호출한다. OCR 처리와 HWPX 생성은 로컬 임시 디렉터리에서 수행하고, 최종 산출물만 Storage와 DB에 반영한다.

**Tech Stack:** FastAPI, requests, Pydantic, Supabase REST API, Supabase Storage REST API, Vitest, pytest

---

### Task 1: 저장소 계약과 테스트 더블 정의

**Files:**
- Create: `D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py`
- Create: `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\repository.py`

**Step 1: Write the failing test**

```python
def test_create_job_persists_source_asset_via_repository():
    ...
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py -q`
Expected: FAIL because repository module and helpers do not exist

**Step 3: Write minimal implementation**

- `PipelineRepository` 프로토콜
- 테스트용 메모리 저장소 더블

**Step 4: Run test to verify it passes**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py -q`
Expected: PASS

### Task 2: 인증과 Supabase REST/Storage 구현

**Files:**
- Create: `D:\03_PROJECT\05_mathOCR\02_main\app\auth.py`
- Create: `D:\03_PROJECT\05_mathOCR\02_main\app\supabase.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\config.py`
- Test: `D:\03_PROJECT\05_mathOCR\02_main\tests\test_auth.py`

**Step 1: Write the failing test**

```python
def test_get_current_user_accepts_valid_supabase_jwt():
    ...
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_auth.py -q`
Expected: FAIL because auth module does not exist

**Step 3: Write minimal implementation**

- JWT HS256 검증
- Supabase REST/Storage 요청 래퍼
- 설정 확장

**Step 4: Run test to verify it passes**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_auth.py -q`
Expected: PASS

### Task 3: 오케스트레이터를 저장소 계층으로 전환

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\orchestrator.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\schema.py`
- Test: `D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py`

**Step 1: Write the failing test**

```python
def test_save_edited_svg_increments_version_and_updates_asset_paths():
    ...
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py -q`
Expected: FAIL because orchestrator still writes to local runtime paths

**Step 3: Write minimal implementation**

- create/read/save를 repository 기반으로 변경
- temp dir 기반 OCR/HWPX 작업
- region 완료 시점마다 상태 저장

**Step 4: Run test to verify it passes**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py -q`
Expected: PASS

### Task 4: FastAPI 응답과 프록시 다운로드 경로 정리

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- Modify: `D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py`

**Step 1: Write the failing test**

```python
def test_get_job_returns_proxy_asset_urls():
    ...
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py -q`
Expected: FAIL because response still assumes local runtime paths

**Step 3: Write minimal implementation**

- 인증 dependency 연결
- asset proxy/download endpoint 추가
- exported 상태 반영

**Step 4: Run test to verify it passes**

Run: `py -m pytest D:\03_PROJECT\05_mathOCR\02_main\tests\test_job_response_fields.py -q`
Expected: PASS

### Task 5: 프런트 토큰 전달과 회귀 검증

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\api\jobApi.ts`
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\store\jobMappers.test.ts`

**Step 1: Write the failing test**

```ts
it("attaches the Supabase session token to backend requests", async () => {
  ...
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/store/jobMappers.test.ts src/app/api/jobApi.test.ts`
Expected: FAIL because Authorization header is not attached

**Step 3: Write minimal implementation**

- `browserSupabase.auth.getSession()` 기반 공통 헤더 주입
- 경로 해석 테스트 보정

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/app/store/jobMappers.test.ts src/app/api/jobApi.test.ts`
Expected: PASS
