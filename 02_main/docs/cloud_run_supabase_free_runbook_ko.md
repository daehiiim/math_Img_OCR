# Cloud Run + Supabase Free 운영 런북

## 1. 목표 아키텍처

- 프런트: `Vercel`
- 백엔드: `Google Cloud Run`
- 인증 / DB / Storage: `Supabase`
- 결제: `Polar hosted checkout + webhook`
- 운영 프런트 도메인: `https://mathtohwp.vercel.app`

## 2. 배포 원칙

- 백엔드는 루트 `Dockerfile` 이미지를 그대로 사용한다.
- Cloud Run은 `min instances=0`을 유지한다.
- 백엔드 커스텀 도메인은 v1에서 도입하지 않는다.
- 운영 API base URL은 Cloud Run 기본 `run.app` 도메인을 사용한다.
- Supabase Free pause 와 Cloud Run cold start 는 운영 제약으로 수용한다.

## 3. 설정 매핑

### Vercel

- `VITE_SUPABASE_URL=<supabase project url>`
- `VITE_SUPABASE_ANON_KEY=<supabase anon key>`
- `VITE_API_BASE_URL=https://<service>-<hash>-an.a.run.app`

### Cloud Run

- `APP_ENV=production`
- `CORS_ALLOW_ORIGINS=https://mathtohwp.vercel.app`
- `CORS_ALLOW_ORIGIN_REGEX`는 비워 두거나 제거
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `POLAR_ACCESS_TOKEN`
- `POLAR_WEBHOOK_SECRET`
- `POLAR_SERVER=production`
- `POLAR_PRODUCT_SINGLE_ID`
- `POLAR_PRODUCT_STARTER_ID`
- `POLAR_PRODUCT_PRO_ID`

### Supabase

- `SITE_URL=https://mathtohwp.vercel.app`
- OAuth redirect allowlist에 `https://mathtohwp.vercel.app/**` 추가
- preview 배포를 유지하면 preview 도메인 패턴도 allowlist 에 추가

### Polar

- success URL: `https://mathtohwp.vercel.app/payment/{plan_id}?checkout=success&checkout_id={CHECKOUT_ID}`
- cancel URL: `https://mathtohwp.vercel.app/payment/{plan_id}?checkout=cancel`
- webhook URL: `https://<service>-<hash>-an.a.run.app/billing/webhooks/polar`
- 운영 상품 3개와 운영 `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`을 사용

## 4. 배포 순서

1. Supabase 운영값과 OAuth allowlist 를 먼저 맞춘다.
2. Polar 운영 상품 3개와 webhook endpoint 를 만든다.
3. Cloud Run 서비스에 운영 환경변수를 반영한다.
4. Vercel `VITE_API_BASE_URL`을 Cloud Run `run.app` 주소로 반영한다.
5. Vercel 재배포 후 `/pricing`, `/payment/starter` 직접 진입을 확인한다.

## 5. 검증 체크리스트

- `docker build -t mathocr-api .`
- `docker run --rm -p 8000:8000 --env-file 02_main/.env mathocr-api`
- `GET /billing/catalog` 이 운영 상품과 통화를 반환하는지 확인
- Supabase OAuth 로그인 후 프런트 세션과 백엔드 `Authorization` 헤더 전달 확인
- Polar checkout 성공 후 `payment_events`, `credit_ledger`, `profiles.credits_balance` 반영 확인
- OCR 1건 실행 후 크레딧 1회 차감과 HWPX 다운로드 확인
- signed URL 로 원본 이미지 / crop / svg / hwpx 접근 확인

## 6. 무료 구간 운영 메모

- Cloud Run 첫 요청 지연은 cold start 기준으로 허용 범위를 미리 확인한다.
- Supabase Free pause 발생 시 dashboard 에서 재개 후 OAuth / DB / Storage 를 순서대로 점검한다.
- 이미지 원본, crop, svg, hwpx 누적량을 주 단위로 확인해 Storage 증가 속도를 본다.
- OCR 요청량이 늘면 Cloud Run 요청 수와 실행 시간 지표를 먼저 확인한 뒤 worker 분리를 검토한다.

## 7. 참고 링크

- [Google Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Google Cloud Run Free Tier](https://cloud.google.com/free/docs/free-cloud-features#cloud-run)
- [Supabase Pricing](https://supabase.com/pricing)
