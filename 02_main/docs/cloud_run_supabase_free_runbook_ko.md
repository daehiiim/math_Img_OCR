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
- `POST /jobs/{job_id}/run`, `POST /jobs/{job_id}/regions/auto-detect` 는 공개 API에서 동기 처리하지 않고 Cloud Tasks enqueue 후 `202 Accepted` 만 반환한다.
- 장시간 OCR/자동 분할은 Cloud Tasks가 `POST /internal/jobs/run-task` 를 OIDC 서비스 계정으로 호출하는 구조로 고정한다.
- Vercel production 환경에서는 `VITE_API_BASE_URL`을 비워 두고 same-origin 프록시 계약을 유지한다.
- Cloud Run 환경에서는 `APP_URL=https://mathtohwp.vercel.app`를 반드시 설정한다.
- Cloud Run에서 `CORS_ALLOW_ORIGINS`를 비우면 백엔드는 `APP_URL` 1개만 허용한다.
- Cloud Run 이미지 기본값은 `HWPX_EXPORT_ENGINE=auto`이며, direct HwpForge writer 실패 시 roundtrip/legacy fallback으로 내려간다.
- 작업 history 자동 삭제는 Cloud Scheduler가 Cloud Run 내부 maintenance endpoint를 직접 호출하는 방식으로 고정한다.
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
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `PIPELINE_TASK_QUEUE`
- `PIPELINE_TASK_CALLER_SERVICE_ACCOUNT`
- `CLOUD_RUN_SERVICE_URL`
- `HWPX_EXPORT_ENGINE=auto`
- `MAINTENANCE_JOB_TOKEN=<Cloud Scheduler shared secret>`
- 필요 시 `CORS_ALLOW_ORIGINS=https://mathtohwp.vercel.app`
- 일반적인 Cloud Run 배포에서는 `HWPFORGE_MCP_PATH`를 따로 넣지 않는다. 루트 `Dockerfile`이 `/app/vendor/hwpforge-mcp` 번들을 함께 포함한다.

### Cloud Tasks

- Queue 이름: `<PIPELINE_TASK_QUEUE>`
- Queue 리전: `<GCP_REGION>`
- 대상 URL: `https://<cloud-run-service>.run.app/internal/jobs/run-task`
- 인증: OIDC `serviceAccountEmail=<PIPELINE_TASK_CALLER_SERVICE_ACCOUNT>`, `audience=<CLOUD_RUN_SERVICE_URL>/internal/jobs/run-task`
- 공개 API를 실행하는 Cloud Run 런타임 서비스 계정에는 Cloud Tasks enqueue 권한이 필요하다.
- `PIPELINE_TASK_CALLER_SERVICE_ACCOUNT` 에는 Cloud Run 서비스 호출 권한이 필요하다.

### Cloud Scheduler

- 대상 URL: `https://<cloud-run-service>.run.app/internal/maintenance/purge-stale-jobs`
- 메서드: `POST`
- 스케줄: 매일 `04:10`, 타임존 `Asia/Seoul`
- 헤더: `X-Maintenance-Token: <MAINTENANCE_JOB_TOKEN>`
- 현재 서비스는 public 이므로 OIDC 대신 shared secret header를 사용한다.

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
3. Cloud Tasks queue를 `<GCP_REGION>` 에 생성하고, Cloud Run 런타임 서비스 계정에 enqueue 권한을 부여한다.
4. `PIPELINE_TASK_CALLER_SERVICE_ACCOUNT` 를 만들거나 선택하고, Cloud Run 서비스 호출 권한을 부여한다.
5. Cloud Run 서비스에 운영 환경변수를 반영한다.
6. `py scripts/schema_preflight.py` 를 실행해 `schema.ocr_jobs_runtime`, `schema.ocr_job_regions_runtime` 이 모두 `OK` 인지 확인한다.
7. Cloud Run 새 배포 후 `run.app` 주소가 바뀌었으면 `CLOUD_RUN_SERVICE_URL` 과 `04_design_renewal/vercel.json` rewrite 대상을 함께 갱신한다.
8. `MAINTENANCE_JOB_TOKEN`을 Cloud Run에 반영한 뒤 Cloud Scheduler job을 신규 생성하거나 토큰을 동기화한다.
9. Vercel production 환경에 `APP_URL`을 반영하고 재배포한다.
10. `/pricing`, `/payment/starter`, `/jobs`, `AI가 문항 찾기` 흐름을 same-origin 경로 기준으로 검증한다.
11. `POST /jobs/{job_id}/run`, `POST /jobs/{job_id}/regions/auto-detect` 가 즉시 `202` 를 반환하고, 이후 `GET /jobs/{job_id}` polling 으로 `completed|failed|queued|exported` 전이가 보이는지 확인한다.
12. `POST /jobs/{job_id}/export/hwpx` 와 다운로드까지 확인해 direct HwpForge writer가 웹 경로에서 500 없이 끝나는지 본다.
13. maintenance endpoint를 수동 호출해 `deleted_jobs`, `deleted_objects`, `cutoff_at` 응답 형식과 `401/200` 분기를 확인한다.

## 5. 검증 체크리스트

- `docker build -t mathocr-api .`
- `docker run --rm -p 8000:8000 --env-file 02_main/.env mathocr-api`
- `docker run --rm mathocr-api python -c "from app.pipeline.hwpforge_roundtrip import resolve_hwpforge_runtime; print(resolve_hwpforge_runtime())"` 로 vendored HwpForge runtime 인식 확인
- `GET /billing/catalog`이 운영 상품과 통화를 반환하는지 확인
- Supabase OAuth 로그인 후 프런트 세션과 백엔드 `Authorization` 헤더 전달 확인
- Polar checkout 성공 후 `payment_events`, `credit_ledger`, `profiles.credits_balance` 반영 확인
- OCR 실행 후 `/jobs/{job_id}/run` 이 즉시 `202` 를 반환하고, 완료 뒤 액션별 크레딧 차감과 HWPX 다운로드가 반영되는지 확인
- 자동 분할 실행 후 `/jobs/{job_id}/regions/auto-detect` 가 즉시 `202` 를 반환하고, 완료 뒤 job 상태가 `queued` 로 돌아와 모바일 영역 검토를 계속할 수 있는지 확인
- `/workspace` 에서 서버 history 목록이 보이고 `running` 작업 삭제 버튼이 비활성화되는지 확인
- same-origin `/jobs`, `/billing` 요청이 Vercel rewrite를 통해 Cloud Run으로 전달되는지 확인
- signed URL로 원본 이미지, crop, svg, hwpx 접근 확인
- Cloud Tasks queue depth, 실패 task, worker 호출 로그를 함께 확인해 `ROUTER_EXTERNAL_TARGET_ERROR` 재현 없이 끝나는지 확인
- Cloud Scheduler 첫 실행 로그에서 maintenance endpoint가 `200`과 purge 통계를 남기는지 확인

## 6. 무료 구간 운영 메모

- Cloud Run 첫 요청 지연은 cold start 기준으로 허용 범위를 미리 확인한다.
- Supabase Free pause 발생 시 dashboard에서 재개 후 OAuth, DB, Storage를 순서대로 점검한다.
- 이미지 원본, crop, svg, hwpx 누적량을 주 단위로 확인해 Storage 증가 속도를 본다.
- 자동 정리 기준은 `updated_at` 14일이며 종료 상태(`completed|failed|exported`)만 삭제한다. 예외 보존은 현재 없다.
- 요청량이 늘면 Cloud Run 요청 수와 실행 시간 지표, Cloud Tasks queue depth, worker 실패율을 먼저 확인한다.

## 7. 참고 링크

- [Google Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Google Cloud Run Free Tier](https://cloud.google.com/free/docs/free-cloud-features#cloud-run)
- [Supabase Pricing](https://supabase.com/pricing)
