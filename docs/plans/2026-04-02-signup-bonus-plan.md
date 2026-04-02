# Signup Bonus Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 신규 로그인 사용자의 `profile` 최초 생성 시 무료 크레딧 3개와 `signup_bonus` 원장 기록을 자동으로 남긴다.

**Architecture:** 기존 `/billing/profile -> BillingService -> SupabaseBillingStore._ensure_profile()` 흐름을 유지하면서 신규 사용자 초기화 지점에만 보너스 지급을 삽입한다. DB 제약에는 `signup_bonus` reason을 추가하고, TDD로 신규/기존 사용자 경계를 고정한다.

**Tech Stack:** FastAPI, Supabase REST client, pytest, React billing profile fetch flow

---

### Task 1: 설계 문서 및 제약 반영 준비

**Files:**
- Modify: `D:/03_PROJECT/05_mathOCR/error_patterns.md`
- Create: `D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-04-02_signup_bonus.sql`

**Step 1: 실패 규칙을 먼저 확인한다**

- `error_patterns.md`에서 billing/schema 관련 규칙을 읽고 중복 reason/제약 불일치 위험을 확인한다.

**Step 2: 스키마 마이그레이션 초안을 작성한다**

```sql
alter table public.credit_ledger
  drop constraint if exists credit_ledger_reason_check;

alter table public.credit_ledger
  add constraint credit_ledger_reason_check
  check (
    reason in (
      'ocr_success_charge',
      'ocr_charge',
      'image_stylize_charge',
      'explanation_charge',
      'manual_adjustment',
      'purchase',
      'stripe_purchase',
      'signup_bonus'
    )
  );
```

**Step 3: 규칙 문구를 1줄로 추가한다**

- 신규 적립 reason을 추가할 때 앱 상수와 `credit_ledger_reason_check`를 동시에 갱신한다.

### Task 2: 신규 지급 요구사항을 failing test로 고정

**Files:**
- Modify: `D:/03_PROJECT/05_mathOCR/02_main/tests/test_billing.py`

**Step 1: 신규 사용자 기본 profile 생성 테스트를 추가한다**

```python
def test_supabase_store_creates_signup_bonus_profile_once():
    ...
    assert profile.credits_balance == 3
```

**Step 2: 원장 기록 검증 테스트를 추가한다**

```python
assert ledger_payload["reason"] == "signup_bonus"
assert ledger_payload["delta"] == 3
```

**Step 3: 기존 사용자 재조회 무적립 테스트를 추가한다**

```python
assert ledger_insert_count == 0
```

**Step 4: RED 검증을 실행한다**

Run: `py -m pytest 02_main/tests/test_billing.py -k signup_bonus`
Expected: 신규 기대값(`3`, `signup_bonus`) 때문에 FAIL

### Task 3: billing store 최소 구현

**Files:**
- Modify: `D:/03_PROJECT/05_mathOCR/02_main/app/billing.py`

**Step 1: signup bonus 상수를 추가한다**

```python
SIGNUP_BONUS_CREDITS = 3
SIGNUP_BONUS_REASON = "signup_bonus"
```

**Step 2: `_ensure_profile()` 신규 생성 경로를 수정한다**

- 신규 `profiles` insert 시 `credits_balance`를 3으로 생성한다.
- 관리자 쓰기 클라이언트로 `credit_ledger` 적립 이력을 남긴다.

**Step 3: 기존 사용자 경로는 그대로 유지한다**

- 이미 profile이 있으면 추가 원장/업데이트를 하지 않는다.

**Step 4: GREEN 검증을 실행한다**

Run: `py -m pytest 02_main/tests/test_billing.py -k signup_bonus`
Expected: PASS

### Task 4: API 회귀 테스트 추가

**Files:**
- Modify: `D:/03_PROJECT/05_mathOCR/02_main/tests/test_billing.py`

**Step 1: `/billing/profile` 최초 조회 응답 테스트를 추가한다**

```python
response = client.get("/billing/profile", headers={"Authorization": f"Bearer {token}"})
assert response.json()["credits_balance"] == 3
```

**Step 2: RED 검증을 실행한다**

Run: `py -m pytest 02_main/tests/test_billing.py -k "billing/profile and signup"`
Expected: 구현 전이라면 FAIL, 구현 후 새 테스트는 PASS

**Step 3: 필요한 최소 보정만 반영한다**

- 테스트가 store 구현과 어긋나면 응답 매핑/주입 경로만 조정한다.

### Task 5: 전체 검증과 문서 마감

**Files:**
- Modify: `D:/03_PROJECT/05_mathOCR/log.md`
- Modify: `D:/03_PROJECT/05_mathOCR/handoff.md`

**Step 1: 관련 테스트를 실행한다**

Run: `py -m pytest 02_main/tests/test_billing.py 02_main/tests/test_auth.py`
Expected: PASS

**Step 2: 작업 로그를 append 한다**

- 변경 목적, 파일, 검증 결과를 한국어로 기록한다.

**Step 3: handoff를 필요 시 overwrite 한다**

- 이후 세션 방향에 영향이 있을 때만 현재 변경 상태를 반영한다.

**Step 4: 배포 영향 메모를 남긴다**

- DB 마이그레이션 선배포 필요

**Step 5: 완료 전 최종 검증을 다시 실행한다**

Run: `py -m pytest 02_main/tests/test_billing.py`
Expected: PASS
