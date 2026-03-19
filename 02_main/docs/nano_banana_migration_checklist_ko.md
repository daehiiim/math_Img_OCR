# Nano Banana Prompt / Supabase 적용 체크리스트

## 1. 목적

- Nano Banana 프롬프트 버전 설정과 액션별 과금 스키마를 staging, production에 안전하게 반영하기 위한 체크리스트다.
- 대상 범위는 backend 환경변수, Supabase 마이그레이션, 이미지 생성 과금, HWPX export 반영 여부다.

## 2. 사전 준비

- backend 배포 이미지가 최신 커밋 기준인지 확인한다.
- `2026-03-19_nano_banana_action_billing_upgrade.sql` 파일이 배포 대상 브랜치에 포함되어 있는지 확인한다.
- Cloud Run 또는 backend 실행 환경에 아래 값이 준비되어 있는지 확인한다.
  - `NANO_BANANA_MODEL`
  - `NANO_BANANA_PROJECT_ID`
  - `NANO_BANANA_LOCATION`
  - `NANO_BANANA_PROMPT_VERSION`

## 3. Staging 적용 순서

1. staging Supabase에 `2026-03-19_nano_banana_action_billing_upgrade.sql`을 적용한다.
2. `public.ocr_jobs`에 `ocr_charged`, `image_charged`, `explanation_charged` 컬럼이 생성됐는지 확인한다.
3. `public.ocr_job_regions`에 `image_crop_path`, `styled_image_path`, `styled_image_model` 컬럼이 생성됐는지 확인한다.
4. `public.credit_ledger`의 `credit_ledger_reason_check` 제약에 `ocr_charge`, `image_stylize_charge`, `explanation_charge`가 포함됐는지 확인한다.
5. 기존 `was_charged=true` 행이 `ocr_charged=true`로 백필됐는지 확인한다.
6. staging backend 환경변수에 Nano Banana 4개 값을 넣고 재배포한다.

## 4. Staging 검증 시나리오

- `이미지 생성만 선택` 실행 후 `image_charged=true`와 `credit_ledger.reason='image_stylize_charge'`를 확인한다.
- `OCR만 선택` 실행 후 OpenAI 미연결 계정은 1크레딧 차감, OpenAI 연결 계정은 무료인지 확인한다.
- `세 항목 모두 선택` 실행 후 선택한 액션별 차감과 결과 생성이 모두 반영되는지 확인한다.
- `openAiConnected=true` 계정은 OCR/해설 무료, 이미지 생성만 1크레딧 차감되는지 확인한다.
- HWPX export 결과에서 `styled_image_path`가 있으면 원본 crop보다 우선 삽입되는지 확인한다.

## 5. Production 적용 순서

1. 저트래픽 시간에 production Supabase에 동일 마이그레이션을 적용한다.
2. backend 환경변수 4개가 production revision에 반영됐는지 확인한다.
3. backend를 재배포한 뒤 `GET /jobs/{id}` 응답에 `styled_image_url`, `styled_image_model`이 내려오는지 확인한다.
4. 실제 데이터 1건으로 `credit_ledger`, `ocr_jobs`, `ocr_job_regions`를 각각 조회해 저장값을 점검한다.

## 6. 장애 대응

- 프롬프트 품질 이슈가 발생하면 코드 롤백보다 먼저 `NANO_BANANA_PROMPT_VERSION`을 이전 값으로 되돌린다.
- 모델 품질 또는 비용 문제가 발생하면 `NANO_BANANA_MODEL`을 이전 모델로 되돌린다.
- 과금 이상이 발생하면 `credit_ledger`와 `ocr_jobs`의 액션별 플래그를 먼저 확인한다.
