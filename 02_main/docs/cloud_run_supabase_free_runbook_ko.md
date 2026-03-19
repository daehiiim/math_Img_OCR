# Cloud Run + Supabase Free 운영 런북

## 1. 목표 아키텍처

- 프런트: `Vercel`
- 백엔드 API: `Google Cloud Run`
- 인증 / DB / Storage: `Supabase`
- 결제: `Polar hosted checkout + webhook`
- 운영 프런트 도메인: `https://mathtohwp.vercel.app`

## 2. 운영 계약

- 백엔드는 저장소 루트 `Dockerfile` 이미지를 그대로 사용한다.
- Cloud Run은 `${PORT:-8000}` 규칙으로 기동해야 한다.
- 프런트 운영 요청은 `04_design_renewal/vercel.json` rewrite를 통해 `/jobs`, `/billing` same-origin 경로를 Cloud Run `run.app` 도메인으로 프록시한다.
- Vercel production 환경에서는 `VITE_API_BASE_URL`을 비워 두고 same-origin 프록시 계약을 유지한다.
- Cloud Run 환경에서는 `APP_URL=https://mathtohwp.vercel.app`를 반드시 설정한다.
- Cloud Run에서 `CORS_ALLOW_ORIGINS`를 비우면 백엔드는 `APP_URL` 1개만 허용한다.
- 백엔드 커스텀 도메인은 v1 범위에서 도입하지 않는다.
- Supabase Free pause와 Cloud Run cold start는 현재 운영 제약으로 수용한다.

## 3. 설정 매핑

### Vercel

- `APP_URL=https://mathtohwp.vercel.app`
- `VITE_SUPABASE_URL=<supabase project url>`
- `VITE_SUPABASE_ANON_KEY=<supabase anon key>`
- `VITE_API_BASE_URL=` 비움
- `04_design_renewal/vercel.json`의 `/jobs`, `/billing` rewrite 대상은 현재 Cloud Run `run.app` 주소와 일치해야 한다.

### Cloud Run

- `APP_URL=https://mathtohwp.vercel.app`
- `OPENAI_KEY_ENCRYPTION_SECRET`
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
- 필요 시 `CORS_ALLOW_ORIGINS=https://mathtohwp.vercel.app`

### Supabase

- `SITE_URL=https://mathtohwp.vercel.app`
- OAuth redirect allowlist에 `https://mathtohwp.vercel.app/**` 추가
- preview 배포를 유지하면 preview 도메인 패턴도 allowlist에 추가

### Polar

- success URL: `https://mathtohwp.vercel.app/payment/{plan_id}?checkout=success&checkout_id={CHECKOUT_ID}`
- cancel URL: `https://mathtohwp.vercel.app/payment/{plan_id}?checkout=cancel`
- webhook URL: `https://<service>-<hash>-an.a.run.app/billing/webhooks/polar`
- 운영 상품 3개와 live `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`을 사용한다.

## 4. 배포 순서

1. Supabase 운영값과 OAuth allowlist를 먼저 맞춘다.
2. Polar 운영 상품 3개와 webhook endpoint를 만든다.
3. Cloud Run 서비스에 운영 환경변수를 반영한다.
4. Cloud Run 새 배포 후 `run.app` 주소가 바뀌었으면 `04_design_renewal/vercel.json` rewrite 대상을 갱신한다.
5. Vercel production 환경에 `APP_URL`을 반영하고 재배포한다.
6. `/pricing`, `/payment/starter`, `/jobs` 흐름을 same-origin 경로 기준으로 검증한다.

## 5. 검증 체크리스트

- `docker build -t mathocr-api .`
- `docker run --rm -p 8000:8000 --env-file 02_main/.env mathocr-api`
- `GET /billing/catalog`이 운영 상품과 통화를 반환하는지 확인
- Supabase OAuth 로그인 후 프런트 세션과 백엔드 `Authorization` 헤더 전달 확인
- Polar checkout 성공 후 `payment_events`, `credit_ledger`, `profiles.credits_balance` 반영 확인
- OCR 실행 후 액션별 크레딧 차감과 HWPX 다운로드 확인
- same-origin `/jobs`, `/billing` 요청이 Vercel rewrite를 통해 Cloud Run으로 전달되는지 확인
- signed URL로 원본 이미지, crop, svg, hwpx 접근 확인

## 6. 무료 구간 운영 메모

- Cloud Run 첫 요청 지연은 cold start 기준으로 허용 범위를 미리 확인한다.
- Supabase Free pause 발생 시 dashboard에서 재개 후 OAuth, DB, Storage를 순서대로 점검한다.
- 이미지 원본, crop, svg, hwpx 누적량을 주 단위로 확인해 Storage 증가 속도를 본다.
- 요청량이 늘면 Cloud Run 요청 수와 실행 시간 지표를 먼저 확인한 뒤 worker 분리를 검토한다.

## 7. 참고 링크

- [Google Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Google Cloud Run Free Tier](https://cloud.google.com/free/docs/free-cloud-features#cloud-run)
- [Supabase Pricing](https://supabase.com/pricing)
