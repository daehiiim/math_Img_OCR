# Polar Sandbox 실행 런북

## 1. 이 문서의 목적

- 처음 Polar와 Stripe를 쓰는 상태에서 sandbox 결제를 끝까지 검증하기 위한 체크리스트다.
- 앱 코드는 이미 Polar 구조로 전환되어 있으므로, 이 문서는 주로 외부 대시보드 작업과 로컬 검증 순서를 설명한다.

## 2. 먼저 알아둘 점

- 이 프로젝트는 Stripe를 직접 결제 API로 쓰지 않는다.
- 고객 결제와 영수증/주문 조회는 Polar 기준이다.
- Stripe는 Polar Finance에서 연결하는 payout 계정 역할이다.
- 따라서 앱 `.env`에는 Stripe secret key를 넣지 않는다.
- 이 단계는 운영 배포 전 검증이므로 `POLAR_SERVER=sandbox`를 유지해야 한다.
- Polar sandbox는 production과 분리된 별도 환경이다.
- `https://polar.sh`에서 만든 사용자, 조직, access token은 `https://sandbox.polar.sh`에서 그대로 재사용되지 않는다.
- 즉, sandbox 검증은 반드시 `https://sandbox.polar.sh`에 로그인해서 따로 진행해야 한다.

## 3. 시작 전에 `.env`에서 먼저 채워야 하는 값

아래 값이 비어 있으면 결제 E2E를 시작해도 중간에서 멈춘다.

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `POLAR_ACCESS_TOKEN`
- `POLAR_WEBHOOK_SECRET`
- `POLAR_SERVER=sandbox`
- `POLAR_PRODUCT_SINGLE_ID`
- `POLAR_PRODUCT_STARTER_ID`
- `POLAR_PRODUCT_PRO_ID`

참고:

- 백엔드 기본 인증은 Supabase 공개 JWKS 기반 비대칭 JWT 검증이다.
- `SUPABASE_JWT_SECRET`는 로컬 HS256 helper 또는 레거시 테스트 경로를 유지할 때만 필요하다.

### 3.1 Supabase 값 찾기

Supabase 공식 문서 기준으로 API 키는 프로젝트의 `Connect` 또는 `Project Settings > API Keys` 영역에서 확인할 수 있다.

1. Supabase Dashboard에서 대상 프로젝트를 연다.
2. `SUPABASE_URL`을 확인한다.
3. `SUPABASE_ANON_KEY`를 확인한다.
4. `SUPABASE_SERVICE_ROLE_KEY`를 확인한다.
5. `SUPABASE_JWT_SECRET`는 HS256 helper를 계속 쓸 경우에만 확인한다.

주의:

- 최근 UI에서는 JWT 관련 값이 `Project Settings > JWT Keys`에서 보일 수 있다.
- 문서/프로젝트 상태에 따라 `API` 또는 `Legacy API Keys` 표기로 보일 수 있으므로, `service_role`, `anon`, `JWT` 항목을 기준으로 찾는 편이 안전하다.

## 4. 사용자 직접 해야 하는 Polar 작업

### 4.1 Organization Access Token

1. `https://sandbox.polar.sh`에 로그인한다.
2. Organization 기준 `Settings` 화면으로 이동한다.
3. 공식 문서 기준 `General` 영역의 `Access Tokens`에서 Organization Access Token을 생성한다.
4. 값을 `02_main/.env`의 `POLAR_ACCESS_TOKEN`에 넣는다.

### 4.2 상품 3개 생성

각 상품은 `one-time`, `USD`로 만든다.

- Single
  - 가격: `$1.00`
  - metadata
    - `plan_id=single`
    - `credits=1`
- Starter
  - 가격: `$19.00`
  - metadata
    - `plan_id=starter`
    - `credits=100`
- Pro
  - 가격: `$29.00`
  - metadata
    - `plan_id=pro`
    - `credits=200`

상품 생성 후 Product ID를 각각 아래에 넣는다.

- `POLAR_PRODUCT_SINGLE_ID`
- `POLAR_PRODUCT_STARTER_ID`
- `POLAR_PRODUCT_PRO_ID`

실무 팁:

- 가격을 나중에 바꾸고 싶으면 앱 코드보다 Polar Product 가격부터 수정한다.
- metadata 키 이름은 정확히 `plan_id`, `credits`를 유지해야 한다.

### 4.3 Stripe Connect Express 연결

1. sandbox Polar Dashboard의 Finance 영역으로 이동한다.
2. payout account 연결을 시작한다.
3. Stripe Connect Express onboarding을 진행한다.
4. 사업자/정산 정보 승인을 끝낸다.

## 5. webhook URL 만들기

- 결제 성공 복귀 URL은 로컬 프런트 주소여도 된다.
- webhook는 Polar 서버가 호출하므로 외부 HTTPS 주소가 필요하다.

권장 절차:

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
ngrok http 8000
```

예시 URL:

- `https://abc123.ngrok-free.app/billing/webhooks/polar`

대안:

- Polar 공식 CLI를 쓸 수 있으면 `polar listen http://localhost:8000/` 방식으로도 webhook 테스트가 가능하다.
- 이미 `cloudflared`를 쓰고 있으면 해당 터널을 사용해도 된다.

Polar webhook 생성 시:

- URL: 위 주소
- 이벤트: `order.paid`
- 생성 후 받은 secret을 `.env`의 `POLAR_WEBHOOK_SECRET`에 넣는다.

## 6. 로컬 사전 점검

### 6.1 환경/도구 점검

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
py scripts/polar_sandbox_preflight.py
```

이 스크립트는 아래를 먼저 검사한다.

- 필수 `.env` 값 존재 여부
- `POLAR_SERVER=sandbox` 여부
- ngrok, polar CLI, cloudflared 설치 여부
- Supabase `payment_events`의 Polar 전환 컬럼 존재 여부

### 6.2 백엔드까지 같이 점검

```bash
cd D:\03_PROJECT\05_mathOCR\02_main
py scripts/polar_sandbox_preflight.py --api-base-url http://localhost:8000
```

이 단계까지 통과해야 실제 checkout 테스트를 시작하는 편이 낫다.

## 7. sandbox 결제 검증 순서

1. 백엔드 실행
2. ngrok 실행
3. webhook 생성 후 secret 반영
4. 프런트 실행

```bash
cd D:\03_PROJECT\05_mathOCR\04_design_renewal
npm run dev -- --host 0.0.0.0 --port 5173
```

5. 로그인 후 결제 페이지에서 sandbox 결제 1회 수행
6. 아래를 확인
  - `payment_events`에 `provider='polar'` 1건 생성
  - `credit_ledger`에 `reason='purchase'` 1건 생성
  - `profiles.credits_balance` 증가
7. Polar Dashboard에서 webhook redelivery 1회 수행
8. 중복 적립이 없는지 다시 확인
9. OCR job 1건 성공시켜 크레딧 1 차감 확인
10. 결제 완료 후 portal 버튼 또는 `GET /billing/portal`로 customer portal 확인

## 8. 막히는 지점별 해석

- `POLAR_WEBHOOK_SECRET` 없음
  - webhook 생성은 했지만 secret 저장 전인 상태다.
- `POLAR_ACCESS_TOKEN`을 넣었는데도 401
  - production Polar token을 넣은 경우가 많다. `https://sandbox.polar.sh`에서 새로 만든 sandbox token인지 다시 확인해야 한다.
- `SUPABASE_SERVICE_ROLE_KEY` 없음
  - `payment_events` 컬럼 점검과 webhook 적립 검증이 불가능하다.
- `SUPABASE_JWT_SECRET` 없음
  - 실제 로그인 세션의 JWKS 검증은 계속 동작한다.
  - 다만 HS256 helper 기반 로컬 테스트 경로는 fallback을 사용할 수 없다.
- `POLAR_SERVER`가 `sandbox`가 아님
  - 지금 단계는 sandbox 검증이므로 `.env`를 `POLAR_SERVER=sandbox`로 되돌려야 한다.
- `payment_events` 컬럼 확인 실패
  - `2026-03-16_polar_billing_upgrade.sql`를 Supabase에 반영해야 한다.
- `billing/catalog` 실패
  - Product ID가 비었거나 Polar access token이 잘못되었을 가능성이 크다.
- checkout는 열리는데 크레딧 적립이 안 됨
  - webhook URL, webhook secret, redelivery 로그를 먼저 확인한다.
