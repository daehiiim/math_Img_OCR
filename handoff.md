# Math OCR Handoff

## 1. 현재 운영 기준

- 백엔드 기준 디렉터리: `D:\03_PROJECT\05_mathOCR\02_main`
- 프런트 기준 디렉터리: `D:\03_PROJECT\05_mathOCR\04_design_renewal`
- 결제 구조: `Polar hosted checkout + FastAPI webhook + Supabase credit ledger`
- Stripe 역할: 직접 결제 연동이 아니라 `Polar payout processor` 기준

## 2. 이번 세션에서 완료한 작업

### 2.1 결제 시스템 전환

- `StripeGateway` 중심 구조를 `PolarGateway` 중심 구조로 교체했다.
- canonical billing API를 아래 경로로 정리했다.
  - `GET /billing/catalog`
  - `POST /billing/checkout`
  - `GET /billing/checkout/{checkout_id}`
  - `GET /billing/portal`
  - `POST /billing/webhooks/polar`
- 기존 프런트 호환을 위해 아래 alias를 남겼다.
  - `POST /billing/checkout-session`
  - `GET /billing/checkout-session/{checkout_id}`
  - `POST /billing/webhook`
- webhook 적립 기준은 `order.paid`만 사용하고, event ID와 order ID 둘 다로 중복 처리하도록 만들었다.
- 크레딧은 계속 백엔드가 원장(`credit_ledger`)과 잔액(`profiles.credits_balance`) 기준으로 관리한다.

주요 파일:

- `D:\03_PROJECT\05_mathOCR\02_main\app\billing.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\config.py`
- `D:\03_PROJECT\05_mathOCR\02_main\schemas\supabase_saas_init.sql`
- `D:\03_PROJECT\05_mathOCR\02_main\schemas\2026-03-16_polar_billing_upgrade.sql`

### 2.2 프런트 결제 UX 전환

- `billingApi`를 Polar 기준 응답 모델로 변경했다.
- `PricingPage`는 USD 가격과 세금 안내 문구를 노출하도록 바꿨다.
- `PaymentPage`는 `checkout_id={CHECKOUT_ID}` 복귀 흐름으로 전환했다.
- 결제 완료 여부는 checkout 상태만이 아니라 `credits_applied`까지 확인한 뒤 성공 처리한다.
- 결제 실패/취소 시에는 잔액 변경 없이 재시도만 유도하도록 정리했다.
- 결제 완료 화면에서 Polar customer portal 진입 버튼을 제공한다.

주요 파일:

- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\api\billingApi.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PricingPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PaymentPage.tsx`

### 2.3 레거시 정리

- 구형 프런트 `01_design` 전체를 제거했다.
- 루트 레벨의 구형 MVP 백엔드 `app/`, `tests/`, `requirements.txt`를 제거했다.
- 루트 중복 문서(`docs/*` 중 운영과 무관한 구형 안내)를 제거하고 `docs/plans`만 남겼다.
- `02_main/app/demo_flow.py`를 제거했다.
- 루트 `Dockerfile`, `docker-compose.yml`, `README.md`를 현재 운영 경로 기준으로 다시 맞췄다.
- `01_design`에 의존하던 `ResultsViewer`, `SvgCanvasEditor`는 `04_design_renewal` 내부로 흡수했다.

## 3. 검증 결과

### 3.1 백엔드 테스트

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
py -m pytest tests -q
```

- 결과: `16 passed`

### 3.2 프런트 테스트

```bash
cd D:\03_PROJECT\05_mathOCR\04_design_renewal
npm run test:run
```

- 결과: `22 passed`

### 3.3 프런트 빌드

```bash
cd D:\03_PROJECT\05_mathOCR\04_design_renewal
npm run build
```

- 결과: 빌드 성공
- 참고: 메인 번들 크기 경고는 남아 있다.

## 4. 다음 세션에서 바로 해야 할 일

### 4.1 운영 연동

1. Polar Dashboard에서 USD one-time product 3개를 실제로 생성
2. 각 상품 metadata에 `plan_id`, `credits` 입력
3. `.env`에 `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`, `POLAR_PRODUCT_*` 채우기
4. Polar Finance에서 Stripe Connect Express payout account 연결
5. 공개 도메인으로 `POST /billing/webhooks/polar` 등록

### 4.2 실결제 검증

1. Polar sandbox checkout 1회 실행
2. `order.paid` webhook 1회 수신 확인
3. webhook redelivery 1회 재전송 후 중복 적립이 없는지 확인
4. 결제 후 OCR 성공 1회에서 크레딧 1 차감 확인

### 4.3 후속 개선

1. 환불 기능은 나중에 별도 설계
2. 영수증/주문 조회 UX는 Polar portal 링크를 더 눈에 띄게 보강 가능
3. 프런트 빌드의 large chunk 경고는 추후 코드 분할로 완화 가능

## 5. 주의사항

- 이 handoff 이후 기준 문서에서 direct Stripe 결제라는 표현은 모두 폐기해야 한다.
- 실제 영수증 발급과 세금 계산은 Polar checkout/customer portal 기준으로 보는 것이 맞다.
- 현재 구현은 실 sandbox/E2E까지는 아직 수행하지 않았다.
