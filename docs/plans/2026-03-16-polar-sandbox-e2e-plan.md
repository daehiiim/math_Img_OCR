# Polar Sandbox E2E 완료 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Polar sandbox에서 결제 1회, `order.paid` webhook 적립, redelivery 중복 방지, OCR 1회 차감, customer portal 진입까지 실제로 검증한다.

**Architecture:** 기존 FastAPI billing API와 Supabase credit ledger를 유지한 채, Polar sandbox Dashboard 설정과 로컬 `ngrok` 노출을 연결해 실제 hosted checkout 흐름을 끝까지 검증한다. 실패 시에는 외부 설정 문제를 먼저 제거하고, 코드 결함이 확인될 때만 최소 범위 수정으로 대응한다.

**Tech Stack:** FastAPI, Supabase REST, Polar sandbox, ngrok, Vite, Playwright, pytest

---

### Task 1: 시작 조건과 blocker 재확인

**Files:**
- Modify: `02_main/.env`
- Verify: `02_main/scripts/polar_sandbox_preflight.py`
- Verify: `02_main/app/polar_preflight.py`

**Step 1: 현재 환경값 존재 여부를 점검**

Run: `cd D:\03_PROJECT\05_mathOCR\02_main && py scripts/polar_sandbox_preflight.py`
Expected: 실패가 나더라도 blocker가 Supabase 누락이 아니라 Polar/ngrok 관련 항목 중심으로 수렴한다.

**Step 2: `.env`의 핵심 sandbox 값 상태를 확인**

Run: `cd D:\03_PROJECT\05_mathOCR\02_main && py -c "from app.config import get_settings; from pathlib import Path; s=get_settings(Path('.')); print(bool(s.auth.supabase_url), bool(s.auth.supabase_service_role_key), s.billing.polar_server)"`
Expected: `True True sandbox`

**Step 3: blocker 목록을 기록**

Run: `cd D:\03_PROJECT\05_mathOCR\02_main && py scripts/polar_sandbox_preflight.py`
Expected: 남은 blocker가 `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`, `POLAR_PRODUCT_*`, `ngrok` 여부 중심으로 정리된다.

### Task 2: Polar sandbox catalog와 webhook 구성

**Files:**
- Modify: `02_main/.env`
- Verify: `02_main/scripts/bootstrap_polar_sandbox_catalog.py`
- Verify: `02_main/docs/polar_sandbox_runbook_ko.md`

**Step 1: sandbox 로그인 상태를 확인하고 organization access token을 발급**

Run: Playwright로 `https://sandbox.polar.sh` 접속 후 로그인 상태와 Access Token 생성 화면 확인
Expected: sandbox organization 기준 token 확보

**Step 2: 상품 3개를 준비**

Run: `cd D:\03_PROJECT\05_mathOCR\02_main && py scripts/bootstrap_polar_sandbox_catalog.py`
Expected: `single`, `starter`, `pro` product id가 출력되거나 이미 존재하는 id가 재사용된다.

**Step 3: `.env`에 token과 product id를 반영**

Run: 수집한 `POLAR_ACCESS_TOKEN`, `POLAR_PRODUCT_SINGLE_ID`, `POLAR_PRODUCT_STARTER_ID`, `POLAR_PRODUCT_PRO_ID`를 `02_main/.env`에 기록
Expected: catalog bootstrap 재실행 시 401 없이 product mapping이 고정된다.

**Step 4: webhook endpoint와 secret을 구성**

Run: Polar sandbox dashboard에서 `order.paid` 전용 webhook 생성
Expected: `POLAR_WEBHOOK_SECRET` 확보 및 `.env` 반영

### Task 3: 로컬 서버와 ngrok 연결

**Files:**
- Modify: `02_main/.env`
- Verify: `README.md`
- Verify: `04_design_renewal/src/app/api/billingApi.ts`

**Step 1: 백엔드 실행**

Run: `cd D:\03_PROJECT\05_mathOCR\02_main && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
Expected: `http://localhost:8000/docs` 접근 가능

**Step 2: ngrok 실행**

Run: `ngrok http 8000`
Expected: 외부 HTTPS URL 확보

**Step 3: webhook URL을 dashboard에 연결**

Run: Polar webhook URL을 `https://<ngrok-domain>/billing/webhooks/polar`로 저장
Expected: webhook delivery target이 활성화된다.

**Step 4: 프런트 실행**

Run: `cd D:\03_PROJECT\05_mathOCR\04_design_renewal && npm run dev -- --host 0.0.0.0 --port 5173`
Expected: `http://localhost:5173` 접근 가능

**Step 5: API 포함 preflight 재실행**

Run: `cd D:\03_PROJECT\05_mathOCR\02_main && py scripts/polar_sandbox_preflight.py --api-base-url http://localhost:8000`
Expected: catalog까지 통과하고 blocker가 사라진다.

### Task 4: 결제 1회와 webhook 적립 검증

**Files:**
- Verify: `02_main/app/main.py`
- Verify: `02_main/app/billing.py`
- Verify: `02_main/tests/test_billing.py`

**Step 1: 로그인 사용자 기준 checkout 생성**

Run: 프런트 결제 페이지 또는 `POST /billing/checkout`
Expected: sandbox hosted checkout URL이 생성된다.

**Step 2: sandbox 결제 1회를 완료**

Run: Playwright로 checkout 결제 진행
Expected: 앱으로 복귀하고 `checkout_id`가 있는 성공 흐름이 열린다.

**Step 3: checkout 상태와 적립 여부를 검증**

Run: `GET /billing/checkout/{checkout_id}`
Expected: `status=succeeded`와 `credits_applied=true`

**Step 4: Supabase 적립 row를 검증**

Run: `payment_events`, `credit_ledger`, `profiles` 조회
Expected: `provider='polar'` 1건, `reason='purchase'` 1건, `credits_balance` 증가

### Task 5: redelivery no-op와 OCR 차감 검증

**Files:**
- Verify: `02_main/app/billing.py`
- Verify: `02_main/app/main.py`

**Step 1: 동일 `order.paid` redelivery 1회 실행**

Run: Polar dashboard에서 webhook redelivery
Expected: 추가 적립 없이 no-op

**Step 2: 중복 방지 결과를 재검증**

Run: `payment_events`, `credit_ledger` 재조회
Expected: row 수 증가 없음

**Step 3: OCR job 1건 성공으로 차감 검증**

Run: 로그인 사용자로 업로드 후 OCR 실행
Expected: `credit_ledger`에 `ocr_success_charge` 1건, 잔액 정확히 1 감소

**Step 4: portal 진입 검증**

Run: `GET /billing/portal` 또는 프런트 버튼 클릭
Expected: customer portal URL이 열린다.

### Task 6: 검증 증거와 production 준비 메모 정리

**Files:**
- Modify: `handoff.md`
- Verify: `docs/plans/2026-03-16-polar-sandbox-e2e-plan.md`

**Step 1: 실행 결과를 기록**

Run: 성공/실패와 실제 blocker를 `handoff.md`에 업데이트
Expected: 다음 세션 없이도 sandbox 결과를 재현 가능하다.

**Step 2: production 전환 차이점을 메모**

Run: sandbox와 production의 차이를 짧게 정리
Expected: production 전환 작업이 별도 계획으로 분리된다.
