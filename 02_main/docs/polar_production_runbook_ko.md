# Polar Production 운영 런북

## 1. 이 문서의 목적

- 운영 결제 장애를 배포 전에 점검하기 위한 production 체크리스트다.
- 검증 대상은 Cloud Run 환경변수, Polar production 상품 metadata, KRW 가격, webhook 적립 흐름이다.

## 2. 먼저 알아둘 점

- 이 프로젝트는 Stripe를 직접 결제 API로 쓰지 않는다.
- 고객 결제와 영수증/주문 조회는 Polar hosted checkout/customer portal 기준이다.
- Stripe는 Polar Finance에서 연결하는 payout processor 역할이다.
- 운영 결제의 단일 진실 원천은 Polar production 상품/price 설정이다.
- 백엔드는 `plan_id`, `credits`, 상품 가격, 상품 통화, Product ID 매핑이 어긋나면 결제를 즉시 막는다.
- checkout 생성 시 billing country 기본값은 `South Korea (KR)`로 preset 된다. 이는 기본값일 뿐이며 고객이 국가를 바꾸지 못하게 잠그는 동작은 아니다.

## 3. Cloud Run 환경변수 계약

운영 배포 기준으로 아래 값을 반드시 맞춘다.

- `APP_URL=https://mathtohwp.vercel.app`
- `POLAR_SERVER=production`
- `POLAR_ACCESS_TOKEN`
- `POLAR_WEBHOOK_SECRET`
- `POLAR_PRODUCT_SINGLE_ID`
- `POLAR_PRODUCT_STARTER_ID`
- `POLAR_PRODUCT_PRO_ID`

추가 주의사항:

- `POLAR_ACCESS_TOKEN`은 Polar production 조직의 live access token이어야 한다.
- `POLAR_PRODUCT_*` 값은 Polar Dashboard의 실제 Product ID와 1:1로 일치해야 한다.
- webhook endpoint는 공개 HTTPS 주소의 `POST /billing/webhooks/polar`를 사용한다.

## 4. Polar Dashboard 상품 체크리스트

운영 상품 3개는 아래 규칙을 모두 만족해야 한다.

- 상품 유형: `one-time`
- 통화: `KRW`
- 가격: Polar Dashboard에 저장된 고정 가격
- metadata 키:
  - `plan_id`
  - `credits`

metadata 값 규칙:

- Single
  - `plan_id=single`
  - `credits=1`
- Starter
  - `plan_id=starter`
  - `credits=100`
- Pro
  - `plan_id=pro`
  - `credits=200`

운영 팁:

- 가격을 바꿀 때는 앱 코드가 아니라 Polar production price를 먼저 수정한다.
- metadata 키 이름이 바뀌면 백엔드는 `missing plan_id metadata`, `invalid credits metadata`로 즉시 실패한다.
- 상품을 새로 만들었다면 새 Product ID를 Cloud Run `POLAR_PRODUCT_*`에도 같이 반영해야 한다.

## 5. Production 사전 점검

### 5.1 환경과 상품 정합성 점검

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
py scripts/polar_production_preflight.py
```

이 스크립트는 아래를 점검한다.

- 필수 환경변수 존재 여부
- `POLAR_SERVER=production` 여부
- Polar production 상품 3개의 metadata/가격/통화 정합성
- token/server 불일치 여부

### 5.2 로컬 백엔드까지 같이 점검

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
py scripts/polar_production_preflight.py --api-base-url http://localhost:8000
```

이 단계는 `/billing/catalog`까지 함께 확인하므로, 배포 전 최종 확인에 가깝다.

### 5.3 checkout ID 기준 진단

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
py scripts/polar_checkout_inspect.py --checkout-id <CHECKOUT_ID>
```

이 스크립트는 아래를 출력한다.

- `status`
- `payment_processor`
- `is_payment_required`
- `is_payment_form_required`
- `customer_billing_address`
- `billing_address_fields`
- `currency`
- `amount`
- `product_id`
- `product_price_id`

## 6. 배포 후 운영 검증 순서

1. Cloud Run 환경변수와 revision이 최신인지 확인한다.
2. `GET /billing/catalog`가 3개 플랜을 반환하는지 확인한다.
3. `single`, `starter`, `pro`의 `currency`가 모두 `krw`인지 확인한다.
4. 프런트 결제 페이지에서 가격 표시가 KRW로 나오는지 확인한다.
5. `POST /billing/checkout` 호출 후 Polar hosted checkout으로 이동하는지 확인한다.
6. 생성 직후 `checkout_id`로 `py scripts/polar_checkout_inspect.py --checkout-id <CHECKOUT_ID>`를 실행해 `customer_billing_address.country=KR`와 `payment_processor`를 확인한다.
7. 실제 checkout 화면에서 KRW 가격과 `Billing address=South Korea` 기본값이 노출되는지 확인한다.
8. `Pay now` 클릭 후 같은 화면에 머무르면 동일 `checkout_id`로 진단 스크립트를 다시 실행해 `is_payment_form_required`, `payment_processor`, `status`를 확인한다.
9. 결제 완료 후 `checkout_id` 복귀와 `credits_applied=true`를 확인한다.
10. `order.paid` webhook 수신 후 `credit_ledger`, `profiles.credits_balance` 적립을 확인한다.
11. webhook redelivery를 1회 재전송해도 중복 적립이 없는지 확인한다.

## 7. 장애 문구 해석

- `POLAR_ACCESS_TOKEN does not match POLAR_SERVER`
  - production 서버에 sandbox token을 넣었거나, 반대로 sandbox 서버에 live token을 넣은 경우다.
- `missing plan_id metadata`
  - 상품 metadata에 `plan_id` 키가 없거나 빈 값이다.
- `polar product metadata plan_id mismatch`
  - 상품 metadata의 `plan_id` 값과 서버가 기대하는 플랜 키가 다르다.
- `invalid credits metadata`
  - `credits`가 비어 있거나 숫자로 변환되지 않는다.
- `missing product price`
  - 상품에 고정 가격이 없거나 price payload가 비어 있다.
- `product currency mismatch`
  - 상품 통화가 `KRW`가 아니다.
- `configured Polar product id mismatch`
  - Cloud Run `POLAR_PRODUCT_*` 값과 실제 checkout/webhook에 들어온 Product ID가 다르다.
- `is_payment_form_required=false`
  - checkout은 열렸지만 결제 폼이 요구되지 않는 상태다. 앱 코드보다 Polar 결제 프로세서 연결 상태와 조직 설정을 우선 점검한다.
- `payment_processor`가 비어 있음
  - Polar checkout 세션에 결제 프로세서가 연결되지 않았을 가능성이 높다. Polar Dashboard의 Finance/processor 설정을 먼저 확인한다.

## 8. 최종 체크리스트

- Polar production 상품 3개 존재
- 상품 3개 모두 `KRW` 고정 가격
- 상품 3개 모두 `plan_id`, `credits` metadata 존재
- Cloud Run `POLAR_SERVER=production`
- Cloud Run live `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET` 반영
- Cloud Run `POLAR_PRODUCT_*`와 Polar Product ID 일치
- `/billing/catalog` 응답 정상
- 실제 checkout KRW 노출 정상
- 실제 checkout 기본 billing country가 `South Korea`로 preset
- `py scripts/polar_checkout_inspect.py --checkout-id <CHECKOUT_ID>` 진단 가능
- `order.paid` 적립 및 redelivery 중복 방지 정상
