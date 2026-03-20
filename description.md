# MathOCR 운영 인수인계 설명서

이 문서는 다음 AI agent가 현재 서비스의 구조, 운영 상태, 최근 변경 사항, 남은 과제를 빠르게 파악하도록 돕는 단일 진입 문서다.

- 기준 시점: 2026-03-20
- 문서 목적: 운영 인수인계
- 비밀값 정책: 이 문서에는 실제 secret 값을 적지 않고 env var 이름과 주입 위치만 적는다.

## 1. 문서 목적과 읽기 순서

새 세션을 시작한 agent는 아래 순서로 읽는다.

1. 현재 한 줄 요약은 [handoff.md](/D:/03_PROJECT/05_mathOCR/handoff.md)에서 확인한다.
2. 전체 구조와 최근 맥락은 [description.md](/D:/03_PROJECT/05_mathOCR/description.md)에서 확인한다.
3. 실행 명령과 운영 계약은 [README.md](/D:/03_PROJECT/05_mathOCR/README.md), [02_main/README.md](/D:/03_PROJECT/05_mathOCR/02_main/README.md)에서 확인한다.
4. 운영 반영 또는 장애 대응이 목적이면 [cloud_run_supabase_free_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/cloud_run_supabase_free_runbook_ko.md), [polar_production_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/polar_production_runbook_ko.md), [production_nano_banana_web_rollout_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/production_nano_banana_web_rollout_ko.md)를 읽는다.
5. 실제 코드 진입은 [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py), [billing.py](/D:/03_PROJECT/05_mathOCR/02_main/app/billing.py), [repository.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/repository.py), [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx)부터 시작한다.

## 2. 2026-03-20 기준 현재 상태

### 운영 기준 디렉터리

- 백엔드 API: [02_main](/D:/03_PROJECT/05_mathOCR/02_main)
- 프런트엔드: [04_design_renewal](/D:/03_PROJECT/05_mathOCR/04_design_renewal)

### 현재까지 확정된 상태

- 백엔드는 FastAPI 기반으로 Supabase Auth, Supabase DB, Supabase Storage, Polar billing을 운영 기준으로 사용한다.
- 프런트는 Vite + React 기반 단일 페이지 앱이고, Vercel에서 same-origin rewrite로 Cloud Run 백엔드와 연결된다.
- OCR job의 영구 저장소는 로컬 `runtime/jobs`가 아니라 Supabase DB + Storage다.
- 과금은 job 전체 1회 차감이 아니라 region/action 단위 차감으로 바뀌었다.
- 사용자 OpenAI key를 연결하면 `ocr`, `explanation`은 사용자 key 기준으로 무료 처리되고, `image_stylize`는 여전히 서비스 크레딧 과금 대상이다.
- Nano Banana 이미지 생성 provider는 `vertex`와 `gemini_api`를 토글 가능하게 구현돼 있다.

### 최근 검증 상태

- 백엔드 검증: `cd D:\03_PROJECT\05_mathOCR\02_main && pytest -q tests`
- 최신 결과: `104 passed`

### 현재 최우선 과제

- Cloud Run/Secret Manager에 `NANO_BANANA_PROVIDER=gemini_api`와 `GEMINI_API_KEY`를 반영한다.
- 실데이터 1건으로 `styled_image_url`, `styled_image_model`, 로그의 `provider=gemini_api`를 검증한다.

### 아직 남아 있는 운영 이슈

- Polar production preflight에서 `POLAR_ACCESS_TOKEN does not match POLAR_SERVER` 이슈가 남아 있다.
- 이 이슈는 Nano Banana provider 토글 작업과 별개의 운영 점검 항목이다.

### 런타임이 아닌 보조 디렉터리

- [00_private](/D:/03_PROJECT/05_mathOCR/00_private): 내부 템플릿, 개인 환경 조각, 보조 스크립트 보관용이다.
- [docs](/D:/03_PROJECT/05_mathOCR/docs): 설계와 구현 계획 문서 보관용이다.
- [templates](/D:/03_PROJECT/05_mathOCR/templates): HWPX 템플릿 조각 보관용이다.
- [schemas](/D:/03_PROJECT/05_mathOCR/schemas): 루트 기준 참고용이며, 실제 백엔드 적용 스키마는 주로 [02_main/schemas](/D:/03_PROJECT/05_mathOCR/02_main/schemas)를 본다.

## 3. 서비스 아키텍처

### 3.1 제품 관점 구조

서비스의 핵심 흐름은 아래와 같다.

1. 사용자가 로그인한다.
2. 이미지 파일을 업로드해서 OCR job을 만든다.
3. 사용자가 region을 직접 지정한다.
4. 선택한 액션(`ocr`, `image_stylize`, `explanation`)만 실행한다.
5. 결과를 확인하고 필요하면 SVG를 수동 수정한다.
6. 최종 결과를 HWPX로 내보낸다.
7. 유료 기능은 Polar checkout과 Supabase credit ledger로 정산한다.

### 3.2 프런트엔드 구조

- 위치: [04_design_renewal](/D:/03_PROJECT/05_mathOCR/04_design_renewal)
- 기술: Vite, React 18, React Router, Vitest
- 핵심 라우트 정의: [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx)

현재 라우트는 아래처럼 나뉜다.

- `/`: 공개 랜딩 페이지
- `/new`: 새 OCR job 생성 화면
- `/login`: Google 로그인 진입
- `/pricing`: 요금제 페이지
- `/payment/:planId`: 결제 진행 페이지
- `/connect-openai`: 사용자 OpenAI key 연결 페이지
- `/workspace`: 작업 목록과 상세 화면
- `/workspace/job/:jobId`: job 상세 화면

상태와 인증 책임은 아래처럼 나뉜다.

- [AuthContext.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/context/AuthContext.tsx)
  - Supabase 세션 복원
  - 로컬 mock 로그인 분기
  - billing profile 동기화
  - OpenAI key 연결/해제
- [jobStore.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/store/jobStore.ts)
  - 업로드, region 저장, 실행, 다운로드 흐름 상태 관리
- [jobApi.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/api/jobApi.ts)
  - 백엔드 `/jobs` 계열 호출
  - Supabase access token을 `Authorization` 헤더에 부착
- [billingApi.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/api/billingApi.ts)
  - billing profile, catalog, checkout, portal 흐름 담당

### 3.3 백엔드 구조

- 위치: [02_main](/D:/03_PROJECT/05_mathOCR/02_main)
- 기술: FastAPI, requests, Supabase REST/Storage, Polar SDK, pytest
- 엔트리포인트: [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py)

백엔드는 크게 네 층으로 나뉜다.

- API 레이어
  - [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py)
  - 요청/응답 모델 정의
  - HTTP 상태 코드와 사용자용 에러 메시지 정규화
- 인증 레이어
  - [auth.py](/D:/03_PROJECT/05_mathOCR/02_main/app/auth.py)
  - Supabase JWT 검증과 현재 사용자 식별
- 파이프라인 레이어
  - [orchestrator.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/orchestrator.py)
  - job 생성, region 저장, OCR 실행, SVG 수정, HWPX export 오케스트레이션
- 영속화 레이어
  - [repository.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/repository.py)
  - Supabase DB + Storage를 job 저장소로 사용
- 과금 레이어
  - [billing.py](/D:/03_PROJECT/05_mathOCR/02_main/app/billing.py)
  - credits profile, OpenAI key 저장, Polar checkout, webhook 적립, action 단위 차감

현재 FastAPI 주요 엔드포인트는 아래와 같다.

- `POST /jobs`
- `PUT /jobs/{job_id}/regions`
- `POST /jobs/{job_id}/run`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/regions/{region_id}/svg`
- `PUT /jobs/{job_id}/regions/{region_id}/svg/edited`
- `POST /jobs/{job_id}/export/hwpx`
- `GET /jobs/{job_id}/export/hwpx/download`
- `GET /billing/profile`
- `PUT /billing/openai-key`
- `DELETE /billing/openai-key`
- `GET /billing/catalog`
- `POST /billing/checkout`
- `GET /billing/checkout/{checkout_id}`
- `GET /billing/portal`
- `POST /billing/webhooks/polar`

### 3.4 인프라 구조

- 프런트 배포: Vercel
- 백엔드 배포: Cloud Run
- 인증/DB/Storage: Supabase
- 결제: Polar
- 문서 출력: HWPX skill runtime

인프라 연결 방식은 아래와 같다.

- [vercel.json](/D:/03_PROJECT/05_mathOCR/04_design_renewal/vercel.json)이 `/jobs`, `/billing` 경로를 Cloud Run으로 rewrite한다.
- 브라우저는 Vercel 도메인 기준 same-origin으로 `/jobs`, `/billing`을 호출한다.
- Cloud Run 컨테이너는 루트 [Dockerfile](/D:/03_PROJECT/05_mathOCR/Dockerfile) 기준으로 배포한다.
- 백엔드는 Supabase DB table과 `ocr-assets` Storage bucket을 사용한다.
- HWPX export runtime은 기본적으로 [02_main/vendor/hwpxskill-math](/D:/03_PROJECT/05_mathOCR/02_main/vendor/hwpxskill-math)를 우선 사용한다.

## 4. 핵심 비즈니스 로직

### 4.1 인증과 세션 복원

- 프런트는 Supabase 브라우저 세션을 기준으로 로그인 상태를 복원한다.
- 로컬 개발에서는 `VITE_LOCAL_UI_MOCK=true`로 mock 로그인/결제 UI를 대체할 수 있다.
- 백엔드는 `Authorization: Bearer <supabase access token>`을 받아 사용자별 데이터 접근 권한을 판단한다.

### 4.2 OCR job 생성과 region 저장

- `POST /jobs`는 업로드 이미지를 Storage에 저장하고 `ocr_jobs` row를 만든다.
- 이후 `PUT /jobs/{job_id}/regions`에서 polygon, type, order를 저장한다.
- region 타입은 `text`, `diagram`, `mixed` 세 가지다.

### 4.3 선택형 실행 파이프라인

- `POST /jobs/{job_id}/run`은 세 액션을 조합 실행한다.
- 액션 종류
  - `ocr`
  - `image_stylize`
  - `explanation`
- 백엔드는 각 region마다 실제 성공 산출물이 있는지 보고 action별 과금 여부를 결정한다.
- 성공 여부와 산출물 경로는 `ocr_job_regions` row에 누적 저장된다.

### 4.4 SVG 수정과 HWPX export

- 사용자는 region별 SVG 원문을 불러와 수정할 수 있다.
- 수정 SVG는 version이 증가하며 별도 경로로 저장된다.
- HWPX export는 job 전체 상태를 materialize한 뒤 번들된 HWPX runtime을 이용해 파일을 생성한다.
- 다운로드는 `GET /jobs/{job_id}/export/hwpx/download`로 제공된다.

### 4.5 크레딧 과금과 사용자 OpenAI key 우선 처리

- billing profile은 `credits_balance`, `used_credits`, `openai_connected`를 기준으로 관리된다.
- 사용자가 OpenAI key를 연결하지 않으면 서비스 OpenAI key를 사용하고 크레딧이 차감된다.
- 사용자가 OpenAI key를 연결하면 `ocr`, `explanation`은 사용자 key 기준으로 무료 처리된다.
- `image_stylize`는 현재 사용자 OpenAI key 여부와 무관하게 action 과금 대상이다.
- 중복 과금을 막기 위해 region/action별 플래그(`ocr_charged`, `image_charged`, `explanation_charged`)를 저장한다.

### 4.6 Polar checkout과 webhook 적립

- 결제 가능한 플랜은 `single`, `starter`, `pro` 세 가지다.
- 실제 금액과 크레딧 수는 Polar product metadata의 `plan_id`, `credits`를 기준으로 검증한다.
- webhook은 `order.paid`만 적립 대상으로 처리한다.
- `payment_events`와 주문 중복 체크로 idempotent 하게 적립한다.

### 4.7 Nano Banana provider 토글

- 설정 파일에서 `NANO_BANANA_PROVIDER=vertex|gemini_api`를 읽는다.
- `gemini_api`를 사용할 때는 `GEMINI_API_KEY`가 필요하다.
- 이미지 생성 설정 문제가 생기면 프런트에는 내부 예외 문자열 대신 고정 메시지 `이미지 생성 서버 설정이 완료되지 않았습니다.`가 노출되도록 매핑돼 있다.

## 5. 코드베이스 맵

다음 파일 4개가 현재 서비스 이해의 최소 진입점이다.

- [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py)
  - API 계약, 응답 구조, 에러 매핑, billing/job 엔드포인트 전체를 본다.
- [billing.py](/D:/03_PROJECT/05_mathOCR/02_main/app/billing.py)
  - 크레딧, OpenAI key 암호화 저장, Polar product 검증, webhook 적립 로직을 본다.
- [repository.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/repository.py)
  - `ocr_jobs`, `ocr_job_regions`, Storage path 규칙, signed URL 생성 방식을 본다.
- [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx)
  - 프런트 라우트 구조와 화면 진입점을 본다.

보조로 같이 보면 좋은 파일은 아래와 같다.

- [orchestrator.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/orchestrator.py)
- [config.py](/D:/03_PROJECT/05_mathOCR/02_main/app/config.py)
- [AuthContext.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/context/AuthContext.tsx)
- [jobApi.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/api/jobApi.ts)

## 6. 배포/운영 계약

### 6.1 환경변수 소스

- 백엔드 런타임은 [02_main/.env](/D:/03_PROJECT/05_mathOCR/02_main/.env) 또는 OS 환경변수만 읽는다.
- 저장소 루트 `.env`는 백엔드 런타임의 단일 소스가 아니다.
- 프런트 로컬 개발은 [04_design_renewal/.env.local](/D:/03_PROJECT/05_mathOCR/04_design_renewal/.env.local)을 사용한다.

### 6.2 백엔드 필수 env 그룹

- 인증/스토리지
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_STORAGE_BUCKET`
- 결제
  - `POLAR_ACCESS_TOKEN`
  - `POLAR_WEBHOOK_SECRET`
  - `POLAR_SERVER`
  - `POLAR_PRODUCT_SINGLE_ID`
  - `POLAR_PRODUCT_STARTER_ID`
  - `POLAR_PRODUCT_PRO_ID`
- OpenAI/이미지
  - `OPENAI_KEY_ENCRYPTION_SECRET`
  - `OPENAI_API_KEY`
  - `NANO_BANANA_PROVIDER`
  - `NANO_BANANA_MODEL`
  - `NANO_BANANA_PROMPT_VERSION`
  - `GEMINI_API_KEY` 또는 Vertex 관련 설정(`NANO_BANANA_PROJECT_ID`, `NANO_BANANA_LOCATION`)
- 앱 계약
  - `APP_URL`
  - `CORS_ALLOW_ORIGINS`

### 6.3 프런트 필수 env 그룹

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_BASE_URL`
- 선택 mock용
  - `VITE_LOCAL_UI_MOCK`
  - `VITE_LOCAL_UI_MOCK_PAYMENT_OUTCOME`

### 6.4 Secret Manager와 운영 주입 포인트

- `GEMINI_API_KEY`, `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_KEY_ENCRYPTION_SECRET`는 Cloud Run에서 Secret Manager 주입 대상으로 보는 것이 맞다.
- `NANO_BANANA_PROVIDER=gemini_api`로 전환할 때는 `GEMINI_API_KEY` 누락 여부를 먼저 확인한다.

### 6.5 Vercel/Cloud Run 계약

- Vercel 프로젝트 Root Directory는 [04_design_renewal](/D:/03_PROJECT/05_mathOCR/04_design_renewal)로 고정한다.
- Vercel production에는 `APP_URL=https://mathtohwp.vercel.app`를 맞춰야 한다.
- Vercel production은 `VITE_API_BASE_URL`을 비워 두고 same-origin rewrite를 사용한다.
- Cloud Run은 루트 [Dockerfile](/D:/03_PROJECT/05_mathOCR/Dockerfile) 기준으로 배포한다.
- 컨테이너는 `${PORT:-8000}` 규칙을 따라야 한다.
- CORS는 `CORS_ALLOW_ORIGINS`가 비어 있으면 `APP_URL` 하나만 허용한다.

### 6.6 Supabase 스키마 계약

신규 환경이라면 [supabase_saas_init.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/supabase_saas_init.sql) 이후 날짜순 upgrade를 모두 적용하는 것이 안전하다.

- [2026-03-15_supabase_ocr_storage_upgrade.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-15_supabase_ocr_storage_upgrade.sql)
- [2026-03-16_polar_billing_upgrade.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-16_polar_billing_upgrade.sql)
- [2026-03-17_openai_key_account_upgrade.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-17_openai_key_account_upgrade.sql)
- [2026-03-19_nano_banana_action_billing_upgrade.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-19_nano_banana_action_billing_upgrade.sql)
- [2026-03-19_region_action_credit_flags.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-19_region_action_credit_flags.sql)
- [2026-03-19_region_charge_tracking.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-19_region_charge_tracking.sql)

현재 배포 코드 기준으로 특히 누락 시 바로 문제를 일으키기 쉬운 파일은 아래 두 개다.

- [2026-03-19_nano_banana_action_billing_upgrade.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-19_nano_banana_action_billing_upgrade.sql)
- [2026-03-19_region_action_credit_flags.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-19_region_action_credit_flags.sql)

### 6.7 Polar 운영 계약

- production 결제는 `one-time`, `KRW` 고정 가격이어야 한다.
- 상품 metadata는 `plan_id`, `credits` 키를 유지해야 한다.
- `plan_id` 값은 `single`, `starter`, `pro`와 일치해야 한다.

## 7. 최근 작업 히스토리

### 2026-03-15

- Math OCR 기능 명세와 Supabase OCR storage 전환 설계/계획 문서를 정리했다.
- 로컬 파일 저장 중심 구조를 Supabase DB + Storage 중심 구조로 바꾸는 방향을 확정했다.

### 2026-03-16

- 웹 배포와 결제 흐름 구성을 본격화했다.
- Vercel과 Cloud Run 연결을 복구하고 운영 경로 정리를 시작했다.

### 2026-03-17

- `APP_URL` 기반 OAuth/결제 복귀 경로를 고정했다.
- hosted frontend same-origin 경로 계약을 강화했다.
- 사용자 OpenAI key 암호화 저장과 계정 연동 UI를 추가했다.

### 2026-03-18

- HWPX export runtime을 vendored bundle 기준으로 안정화했다.
- local UI mock 로그인/결제 흐름과 관련 테스트를 추가했다.
- 결과 미리보기와 마크업 표시를 정리하고 프런트 빌드 이슈를 수정했다.
- Polar production billing guard와 사용자 친화적 에러 메시지를 강화했다.

### 2026-03-19

- region 기반 과금과 unified HWPX export를 정리했다.
- 액션 단위 크레딧 차감 구조로 전환했다.
- action charge guard, region billing tracking, Cloud Run 운영 문서를 정리했다.
- 중복 프런트 임시 스냅샷을 제거하고 Docker packaging/Nano Banana prompt 설정을 정리했다.

### 2026-03-20

- Nano Banana provider 토글(`vertex|gemini_api`)을 추가했다.
- `GEMINI_API_KEY`, `NANO_BANANA_PROVIDER` 설정 로딩과 provider별 `genai.Client(...)` 분기를 반영했다.
- 이미지 생성 설정 오류를 사용자용 고정 메시지로 매핑했다.
- public draft upload와 billing flow hardening 변경이 함께 반영됐다.
- 백엔드 테스트 `104 passed`를 다시 확인했다.

## 8. 주요 에러와 운영 리스크

### 8.1 예상 가능한 에러 목록과 사용자 메시지

| 분류 | 내부 원인 예시 | 사용자/클라이언트에 보이는 메시지 |
| --- | --- | --- |
| DB 스키마 드리프트 | migration 누락, column/constraint 불일치 | `배포 DB 스키마가 최신이 아닙니다.` |
| Supabase 저장소 연결 실패 | Supabase 설정 누락, Storage/API 장애 | `서버 저장소 연결에 실패했습니다. 잠시 후 다시 시도하세요.` |
| 사용자 OpenAI key 미설정 | 서비스 key 없음 + 사용자 key 미연결 | `사용자 OpenAI 키 설정이 완료되지 않았습니다.` |
| 이미지 생성 설정 오류 | `GEMINI_API_KEY` 누락, provider 오설정, 패키지 미설치 | `이미지 생성 서버 설정이 완료되지 않았습니다.` |
| 크레딧 부족 | `insufficient credits` | 현재는 400 에러 텍스트로 내려간다. 프런트에서 사용자 친화 문구로 추가 래핑할 여지가 있다. |
| 결제 설정 불일치 | Polar product metadata 불일치, access token/server mismatch | 주로 운영 점검 단계에서 스크립트와 API 에러로 드러난다. |

### 8.2 현재 운영 리스크

- Nano Banana `gemini_api` 전환은 코드 완료, 운영 반영 미완료 상태다.
- Polar production token/server mismatch는 아직 해소되지 않았다.
- Supabase migration 누락 시 job 조회나 run 시점에 바로 500 성격 오류가 날 수 있다.
- HWPX export는 vendor runtime에 의존하므로 번들 경로가 손상되면 내보내기가 실패한다.

## 9. 다음 AI agent 시작 순서

1. [handoff.md](/D:/03_PROJECT/05_mathOCR/handoff.md)에서 최우선 작업과 다음 단계만 먼저 읽는다.
2. 이 문서에서 현재 구조와 남은 운영 이슈를 읽는다.
3. Nano Banana 운영 전환이 목적이면 [production_nano_banana_web_rollout_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/production_nano_banana_web_rollout_ko.md)와 [cloud_run_supabase_free_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/cloud_run_supabase_free_runbook_ko.md)를 먼저 읽는다.
4. 결제 이슈가 목적이면 [polar_production_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/polar_production_runbook_ko.md)와 [billing.py](/D:/03_PROJECT/05_mathOCR/02_main/app/billing.py)를 먼저 읽는다.
5. 코드 수정이 필요하면 [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py) -> [orchestrator.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/orchestrator.py) -> [repository.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/repository.py) 순으로 백엔드를 따라간다.
6. 프런트 수정이 필요하면 [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx) -> [AuthContext.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/context/AuthContext.tsx) -> [jobApi.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/api/jobApi.ts) 순으로 따라간다.
7. 운영 반영 후에는 실데이터 1건으로 이미지 생성 결과와 저장 결과를 검증하고, 필요하면 `vertex`로 롤백 가능한지까지 확인한다.

## 10. 참고 문서

- 루트 개요: [README.md](/D:/03_PROJECT/05_mathOCR/README.md)
- 백엔드 가이드: [02_main/README.md](/D:/03_PROJECT/05_mathOCR/02_main/README.md)
- 백엔드 빠른 시작: [mvp1_quickstart_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/mvp1_quickstart_ko.md)
- Cloud Run 운영 런북: [cloud_run_supabase_free_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/cloud_run_supabase_free_runbook_ko.md)
- Polar production 런북: [polar_production_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/polar_production_runbook_ko.md)
- Polar sandbox 런북: [polar_sandbox_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/polar_sandbox_runbook_ko.md)
- Nano Banana 운영 전환: [production_nano_banana_web_rollout_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/production_nano_banana_web_rollout_ko.md)
- 설계 문서: [2026-03-15-supabase-ocr-storage-design.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-15-supabase-ocr-storage-design.md)
- 구현 계획: [2026-03-15-supabase-ocr-storage-plan.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-15-supabase-ocr-storage-plan.md)
- 검증 계획: [2026-03-16-polar-sandbox-e2e-plan.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-16-polar-sandbox-e2e-plan.md)
