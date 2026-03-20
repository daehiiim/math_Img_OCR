# Production 웹 환경 Nano Banana provider 전환 체크리스트

## 1. 목적

- production 웹 환경에서 SVG 편집 흐름을 제거한 현재 구조를 유지하면서 Nano Banana 이미지 생성 provider를 `vertex`와 `gemini_api` 중 선택할 수 있게 운영하는 체크리스트다.
- 대상 범위는 Vercel 프런트, Cloud Run 백엔드, Supabase Auth, Secret Manager, Vertex AI 권한, production 검증 순서다.

## 2. 프런트 배포 확인

1. [vercel.json](/D:/03_PROJECT/05_mathOCR/04_design_renewal/vercel.json)의 `/jobs`, `/billing` rewrite 대상이 production Cloud Run URL인지 확인한다.
2. Vercel production 환경변수에 아래 값을 반영한다.
   - `APP_URL=https://mathtohwp.vercel.app`
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
3. `VITE_API_BASE_URL`는 비워 두고 same-origin rewrite를 유지한다.
4. production 배포 후 `https://mathtohwp.vercel.app/login`이 정상 응답하는지 확인한다.

## 3. 백엔드 배포 확인

1. Cloud Run production 서비스 환경변수에 아래 값을 반영한다.
   - `APP_URL=https://mathtohwp.vercel.app`
   - `CORS_ALLOW_ORIGINS=https://mathtohwp.vercel.app`
   - `NANO_BANANA_PROVIDER=vertex` 또는 `NANO_BANANA_PROVIDER=gemini_api`
   - `NANO_BANANA_MODEL=gemini-3.1-flash-image-preview`
   - `NANO_BANANA_PROMPT_VERSION=csat_v1`
2. `NANO_BANANA_PROVIDER=gemini_api`를 사용할 때는 새로 발급한 `GEMINI_API_KEY`를 Secret Manager로 연결한다.
3. `NANO_BANANA_PROVIDER=vertex`를 사용할 때는 아래 값도 함께 유지한다.
   - `NANO_BANANA_PROJECT_ID=sapient-stacker-468504-r6`
   - `NANO_BANANA_LOCATION=global`
4. Cloud Run 서비스 계정은 attached service account 방식으로 유지한다.
5. `vertex` 롤백을 위해 해당 서비스 계정의 `roles/aiplatform.user` 권한을 유지한다.
6. backend 재배포 후 `/jobs/{id}` 응답에 `image_crop_url`, `styled_image_url`, `styled_image_model`이 내려오는지 확인한다.

## 4. Supabase / Google 로그인 설정

1. Supabase Auth의 `Site URL`을 `https://mathtohwp.vercel.app`로 설정한다.
2. Supabase Auth의 `Redirect URLs`에 `https://mathtohwp.vercel.app/login`을 추가한다.
3. Supabase의 Google provider가 활성화되어 있는지 확인한다.
4. Google OAuth client의 callback URI에 `https://zbkyqtkeiraxnfunkomp.supabase.co/auth/v1/callback`가 등록되어 있는지 확인한다.

## 5. Production 수용 테스트

1. production 도메인에서 Google 로그인 후 `/login`으로 정상 복귀하는지 확인한다.
2. 이미지가 있는 문제에서 `이미지 생성`만 선택해 실행하고 `styled_image_url`, `styled_image_model`이 저장되는지 확인한다.
3. Cloud Run 로그에 `provider`, `model`, `prompt_version`, `prompt_kind`가 함께 남는지 확인한다.
4. 이미지가 없는 문제에서 Nano Banana 호출 없이 이미지 미리보기에 빈 상태 메시지가 보이는지 확인한다.
5. 결과 화면에 SVG 탭, SVG 편집 버튼, SVG 저장 버튼이 더 이상 노출되지 않는지 확인한다.
6. `이미지 생성만 선택` 시 1크레딧 차감되는지 확인한다.
7. `OCR만 선택` 시 OpenAI 미연결 계정은 1크레딧, 연결 계정은 무료인지 확인한다.
8. `세 항목 모두 선택` 시 선택한 액션 기준으로 합산 차감되는지 확인한다.
9. HWPX export 결과에서 생성 이미지가 있으면 원본 crop보다 우선 삽입되는지 확인한다.

## 6. 운영 점검 및 롤백

1. production 배포 직후 `credit_ledger`, `ocr_jobs`, `ocr_job_regions`를 1건 이상 실데이터로 조회한다.
2. `gemini_api` 운영 중 품질/비용/장애 이슈가 있으면 코드 롤백 대신 `NANO_BANANA_PROVIDER=vertex`로 되돌리고 새 revision으로 전환한다.
3. `vertex` 복귀를 위해 `NANO_BANANA_PROJECT_ID`, `NANO_BANANA_LOCATION`, 서비스 계정 권한은 삭제하지 않는다.
4. 프롬프트 품질 이슈가 있으면 코드 롤백보다 먼저 `NANO_BANANA_PROMPT_VERSION` 값을 되돌린다.
5. 모델 비용 또는 품질 이슈가 있으면 `NANO_BANANA_MODEL` 값을 이전 모델로 되돌린다.
