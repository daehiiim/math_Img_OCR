# 신규 가입 3크레딧 지급 설계

## 목표

신규 로그인 사용자가 백엔드에서 `profile`을 최초 생성할 때 무료 크레딧 `3개`를 자동 지급한다. 이미 `profiles` row가 있는 기존 사용자는 추가 지급하지 않는다.

## 범위

- 포함
  - `profiles` 최초 생성 시 기본 잔액을 `3`으로 초기화
  - `credit_ledger`에 `signup_bonus` reason으로 적립 이력 기록
  - `/billing/profile` 첫 호출에서 즉시 `3` 크레딧이 보이도록 보장
  - 관련 테스트와 운영 문서 보강
- 제외
  - 프런트 토스트/배너/가격 안내 문구 추가
  - 기존 사용자 일괄 보정 배치
  - 운영자가 금액을 바꾸는 설정 UI/환경 변수

## 아키텍처

### 백엔드

- 현재 로그인 직후 프런트는 `GET /billing/profile`을 호출하고, 백엔드는 `BillingService -> SupabaseBillingStore.get_or_create_profile()` 경로로 `profiles` row를 보장한다.
- 신규 보너스는 이 기존 흐름 안에서 처리한다. 즉, `SupabaseBillingStore._ensure_profile()`이 `profiles` 부재를 감지하면:
  - `profiles.credits_balance = 3`
  - `credit_ledger.delta = 3`
  - `credit_ledger.reason = 'signup_bonus'`
  를 같은 초기화 흐름으로 기록한다.
- 이미 `profiles`가 있으면 기존 row를 그대로 반환하므로 중복 지급이 발생하지 않는다.

### 비즈니스 로직

- 지급 대상: `profiles` row가 없는 사용자만
- 지급 수량: 고정값 `3`
- 지급 시점: 백엔드 `profile` 최초 생성 시점
- 지급 방식: 잔액 반영 + 원장 기록
- 사용자 노출: 별도 성공 메시지 없이 잔액만 반영

## 데이터 모델 변경

### `credit_ledger.reason`

- 기존 reason 제약에 `signup_bonus`를 추가한다.
- 이유:
  - 감사 추적 가능
  - 중복 지급 조사 용이
  - 향후 프로모션/추천인 보너스와 같은 적립 이벤트로 확장 가능

### 상수 배치

- 지급 수량 `3`은 백엔드 billing 모듈 내부 상수로 둔다.
- 현재 요구사항은 고정 프로모션이므로 환경 변수나 설정 테이블로 분리하지 않는다.

## 에러 처리

### 예상 가능한 에러

1. DB 제약 불일치
   - `credit_ledger_reason_check`에 `signup_bonus`가 없으면 원장 insert 실패
2. 관리자 쓰기 권한 문제
   - `SUPABASE_SERVICE_ROLE_KEY` 누락 또는 권한 오류로 원장 적재 실패
3. 인프라 일시 장애
   - Supabase API/network 오류로 `profiles` 또는 `credit_ledger` 생성 실패

### 사용자 메시지

- 사용자에게는 성공 메시지를 띄우지 않는다.
- 초기 프로필 생성 실패 시 기존 billing persistence 계열 오류 정책에 맞춰
  - "계정 초기화 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
  수준의 안전한 메시지로 귀결되도록 유지한다.

## 배포 순서

1. DB 마이그레이션 배포
   - `credit_ledger_reason_check`에 `signup_bonus` 추가
2. 백엔드 애플리케이션 배포

순서를 뒤집으면 신규 사용자의 최초 로그인에서 500 오류가 발생할 수 있다.

## 테스트 전략

- 단위 테스트
  - 신규 사용자 `profile` 생성 시 `3` 크레딧과 `signup_bonus` 원장 기록 검증
  - 기존 사용자 재조회 시 추가 적립이 없는지 검증
  - 원장 reason이 정확히 `signup_bonus`인지 검증
- API 테스트
  - `/billing/profile` 첫 호출 응답이 `credits_balance = 3`인지 검증
- 회귀 테스트
  - 기존 결제 적립/차감 테스트가 유지되는지 확인

## 대안 비교

### 대안 1. `profile` 최초 생성 시 지급

- 장점: 현재 구조에 가장 자연스럽고 중복 지급 방지가 단순하다.
- 단점: reason 제약과 앱 코드를 함께 관리해야 한다.

### 대안 2. `auth.users` 트리거 기반 지급

- 장점: 계정 생성 시점을 DB가 직접 보장한다.
- 단점: 로직이 앱 밖으로 분산되고 디버깅/운영 복잡도가 커진다.

### 대안 3. 별도 지급 API/배치

- 장점: 책임 분리가 명확하다.
- 단점: 최초 로그인 직후 잔액 불일치나 동기화 누락 위험이 생긴다.

현재 요구사항에는 대안 1이 가장 적합하다.
