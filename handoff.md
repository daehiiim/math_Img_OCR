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
- `PricingPage`는 Polar catalog 실패 시에도 KRW fallback 가격을 유지하도록 정리했다.
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

### 2.4 운영 Polar metadata/KRW 정합성 복구

- `billing.py`에 상품 검증 helper를 공통화해서 `catalog`, `checkout`, `order.paid webhook`가 같은 규칙으로 Polar 상품을 검증하도록 맞췄다.
- 운영 검증 규칙은 아래 5개다.
  - `metadata.plan_id` 존재
  - `metadata.credits` 숫자 변환 가능
  - 고정 price 존재
  - 통화가 `krw`
  - webhook/product payload의 Product ID와 Cloud Run `POLAR_PRODUCT_*` 매핑 일치
- 아래 에러 detail을 명시적으로 분리했다.
  - `POLAR_ACCESS_TOKEN does not match POLAR_SERVER`
  - `missing plan_id metadata`
  - `polar product metadata plan_id mismatch`
  - `invalid credits metadata`
  - `missing product price`
  - `product currency mismatch`
  - `configured Polar product id mismatch`
- 프런트 `billingApi`는 위 detail들을 사용자용 한국어 메시지로 매핑한다.
- `PricingPage`, `PaymentPage` fallback catalog는 USD에서 KRW 기준으로 바꿨다.
- 운영 점검용 `py scripts/polar_production_preflight.py`를 추가했다.
- production preflight는 `POLAR_SERVER=production`, live token, Product ID 3개, `plan_id`, `credits`, KRW 가격 정합성을 검사한다.

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

### 3.4 이번 세션 추가 검증

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
pytest -q tests/test_billing.py tests/test_polar_preflight.py
```

- 결과: `36 passed`

```bash
cd D:\03_PROJECT\05_mathOCR\04_design_renewal
npm run test:run -- src/app/api/billingApi.test.ts src/app/components/PricingPage.test.tsx src/app/components/PaymentPage.test.tsx
```

- 결과: `18 passed`

```bash
cd D:\03_PROJECT\05_mathOCR\04_design_renewal
npm run build
```

- 결과: 빌드 성공

### 3.5 운영 preflight 현재 상태

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
py scripts/polar_production_preflight.py
```

- 결과: 실패
- 현재 로컬 `.env` 기준으로 `polar.product.single`, `polar.product.starter`, `polar.product.pro` 모두 `POLAR_ACCESS_TOKEN does not match POLAR_SERVER`
- 해석: 로컬 저장소의 production token/server 조합은 실제 운영 Polar production 조회 조건과 아직 일치하지 않는다.

## 4. 다음 세션에서 바로 해야 할 일

### 4.1 운영 연동

1. Cloud Run 환경변수에 `POLAR_SERVER=production`, live `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`, `POLAR_PRODUCT_*` 3개가 실제 운영 값으로 들어갔는지 확인
2. Polar production 상품 3개의 metadata `plan_id`, `credits`와 KRW 고정 가격을 다시 확인
3. Product ID가 Cloud Run `POLAR_PRODUCT_*`와 정확히 일치하는지 대조
4. 공개 도메인의 `POST /billing/webhooks/polar`가 Polar production webhook에 연결되어 있는지 확인
5. `py scripts/polar_production_preflight.py` 기준으로 운영 설정을 재검증

### 4.2 실결제 검증

1. 배포 환경 `/billing/catalog` 응답에서 3개 플랜과 `currency=krw` 확인
2. same-origin `/billing/checkout` 호출로 Polar hosted checkout 진입 확인
3. 실제 checkout 화면에서 KRW 가격 노출 확인
4. `order.paid` webhook 1회 수신 확인
5. webhook redelivery 1회 재전송 후 중복 적립이 없는지 확인
6. 결제 후 OCR 성공 1회에서 크레딧 1 차감 확인

### 4.3 후속 개선

1. 환불 기능은 나중에 별도 설계
2. 영수증/주문 조회 UX는 Polar portal 링크를 더 눈에 띄게 보강 가능
3. 프런트 빌드의 large chunk 경고는 추후 코드 분할로 완화 가능

## 5. 주의사항

- 이 handoff 이후 기준 문서에서 direct Stripe 결제라는 표현은 모두 폐기해야 한다.
- 실제 영수증 발급과 세금 계산은 Polar checkout/customer portal 기준으로 보는 것이 맞다.
- 운영 실결제 E2E는 아직 이 저장소 로컬 세션에서 수행하지 않았다.
- 로컬 `.env`와 배포 Cloud Run 환경은 다를 수 있으므로, 최종 판단은 production preflight와 실제 `/billing` 응답 기준으로 해야 한다.
