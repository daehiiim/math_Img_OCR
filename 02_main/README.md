# mathOCR Backend

`02_main`은 현재 운영 중인 FastAPI 백엔드입니다.

## 실행

### 로컬 개발
```bash
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 백엔드 런타임 설정의 단일 소스는 `02_main/.env` 이다. 저장소 루트 `.env` 는 백엔드 설정 파일로 사용하지 않는다.
- 레거시 `apiKey.env` fallback은 더 이상 사용하지 않는다. 런타임 설정은 `02_main/.env` 또는 OS 환경변수에서만 읽는다.
- 브라우저 인증이나 결제 복귀 흐름까지 확인하려면 `.env`에 `APP_URL=https://mathtohwp.vercel.app` 또는 허용할 프런트 도메인을 함께 설정해야 한다.
- HWPX export는 기본적으로 `02_main/vendor/hwpxskill-math` 번들을 사용한다. 다른 로컬 경로를 써야 하면 `HWPX_SKILL_DIR`로 override 한다.
- 로컬에서 `uvicorn`만 직접 띄우는 경우 HwpForge 런타임이 없으면 export가 실패할 수 있다. 이때는 `HWPX_EXPORT_ENGINE=legacy`로 내리거나 `docker compose` 경로를 사용한다.

### Docker
```bash
docker compose up --build
```

- Swagger: `http://localhost:8000/docs`
- CORS 기본 허용은 더 이상 localhost가 아니다. `CORS_ALLOW_ORIGINS`가 없으면 `APP_URL` 1개만 허용한다.
- 두 개의 compose 파일은 모두 `HWPX_EXPORT_ENGINE=auto`를 다시 주입하므로, `.env` 값이 `legacy`여도 컨테이너 안에서는 HwpForge direct writer를 우선 검증한다.

## 필수 환경변수

- `OPENAI_KEY_ENCRYPTION_SECRET`
- `APP_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `POLAR_ACCESS_TOKEN`
- `POLAR_WEBHOOK_SECRET`
- `POLAR_SERVER` (`production` 기본, sandbox 테스트는 별도 런북 참고)
- `POLAR_PRODUCT_SINGLE_ID`
- `POLAR_PRODUCT_STARTER_ID`
- `POLAR_PRODUCT_PRO_ID`

## 선택 환경변수

- `OPENAI_BASE_URL` (기본값 `https://api.openai.com/v1`)
- `NANO_BANANA_PROMPT_VERSION` (기본값 `csat_v1`, 현재 지원값도 `csat_v1` 하나다)
- `CORS_ALLOW_ORIGINS` (`https://a.example.com,https://b.example.com` 형식)
- `HWPX_SKILL_DIR` (기본값 비움. 특수한 로컬 skill 경로를 강제로 우선 사용해야 할 때만 설정)
- `HWPX_EXPORT_ENGINE` (기본값 `auto`, 지원값 `legacy | auto | hwpforge`)
- `HWPFORGE_MCP_PATH` (기본값 비움. HwpForge MCP 실행 파일 또는 `.js` wrapper 절대 경로)

## 배포 전 스키마 점검

- 액션별 과금과 region 플래그를 쓰는 현재 백엔드는 Supabase에 아래 SQL 두 개가 모두 반영돼 있어야 한다.
- `02_main/schemas/2026-03-19_nano_banana_action_billing_upgrade.sql`
- `02_main/schemas/2026-03-19_region_action_credit_flags.sql`
- 둘 중 하나라도 누락되면 `POST /jobs/{id}/run` 또는 `GET /jobs/{id}`에서 스키마 불일치 오류가 날 수 있다.
- 적용 뒤에는 backend 환경변수를 다시 확인하고 재배포해야 한다.

## HWPX export runtime

- 기본값은 `02_main/vendor/hwpxskill-math` 이다.
- override가 필요하면 `.env` 또는 OS 환경변수에 `HWPX_SKILL_DIR` 을 설정한다.
- fallback 순서는 `HWPX_SKILL_DIR` -> `02_main/vendor/hwpxskill-math` -> `CODEX_HOME/skills/hwpxskill-math` -> `~/.codex/skills/hwpxskill-math` 이다.
- canonical template 탐색 순서는 로컬 저장소 기준 `../templates/style_guide.hwpx` -> 컨테이너 번들 기준 `02_main/templates/style_guide.hwpx` 이다.
- Docker/Cloud Run 이미지에는 `style_guide.hwpx` 가 반드시 포함돼야 하며, 현재 Dockerfile은 이를 `/app/templates/style_guide.hwpx` 로 함께 복사한다.
- direct writer용 template JSON은 `02_main/templates/hwpx/hwpforge_generated_canonical_sample.json` 자산을 사용한다.
- runtime 탐색이 모두 실패하면 에러 메시지에 `checked:` 와 `missing:` 이 함께 포함되어 어떤 경로를 확인했고 어떤 파일이 없었는지 그대로 노출한다.
- 애플리케이션 코드 fallback 기본값은 `legacy`지만, 현재 Docker/Cloud Run 이미지와 `.env.example`은 `HWPX_EXPORT_ENGINE=auto`를 기본으로 사용한다.
- `HWPX_EXPORT_ENGINE=auto` 또는 `hwpforge`를 켜면 direct export IR -> HwpForge writer로 `section0.xml` 생성을 먼저 시도한다.
- direct writer가 실패하면 `auto`에서는 legacy renderer와 roundtrip/legacy fallback으로 계속 내보내고, `hwpforge`에서는 HwpForge roundtrip fallback까지 시도한다.
- HwpForge engine은 최종 패키지에도 `inspect + validate`를 다시 수행한다.
- HwpForge runtime 탐색 순서는 `HWPFORGE_MCP_PATH` -> `02_main/vendor/hwpforge-mcp/node_modules/@hwpforge/...` -> 로컬 `.tmp/hwpforge-poc/*/node_modules/@hwpforge/...` 이다.
- 현재 Docker/Cloud Run 이미지와 `02_main/Dockerfile`은 Node 런타임과 HwpForge MCP 번들을 함께 포함하도록 맞춰져 있다. 컨테이너 기본값에서는 별도 `HWPFORGE_MCP_PATH` 없이도 동작해야 한다.

## 인증 규칙

- 기본 검증 경로는 `SUPABASE_URL/auth/v1/.well-known/jwks.json` 기반 JWKS 로컬 검증이다.
- 현재 Supabase 비대칭 JWT(`ES256`, `RS256`)는 백엔드가 JWKS 캐시를 사용해 검증한다.
- `SUPABASE_JWT_SECRET`는 로컬 테스트 유틸과 레거시 HS256 helper 호환용 fallback일 때만 사용한다.
- 운영 경로에서는 `SUPABASE_URL`이 기준 값이며, `SUPABASE_JWT_SECRET`는 필수값이 아니다.

## 결제 엔드포인트

- `GET /billing/catalog`
- `POST /billing/checkout`
- `GET /billing/checkout/{checkout_id}`
- `GET /billing/portal`
- `POST /billing/webhooks/polar`

## Polar 운영 계약

- 운영 결제의 단일 진실 원천은 Polar production 상품과 가격 설정이다.
- 운영 상품 3개는 모두 `one-time`, `KRW` 고정 가격이어야 한다.
- 각 상품 metadata 키는 정확히 `plan_id`, `credits`를 사용해야 한다.
- `plan_id` 값은 각각 `single`, `starter`, `pro`와 일치해야 한다.
- Cloud Run 환경변수 `POLAR_PRODUCT_*`는 Polar Dashboard의 실제 Product ID와 동일해야 한다.
- Cloud Run 배포 절차와 same-origin rewrite 계약은 `docs/cloud_run_supabase_free_runbook_ko.md`를 기준으로 관리한다.

## Polar production 사전 점검

운영 배포 전에는 production 사전 점검을 먼저 실행한다.

```bash
py scripts/polar_production_preflight.py
```

로컬 백엔드까지 함께 점검하려면 아래처럼 실행한다.

```bash
py scripts/polar_production_preflight.py --api-base-url http://localhost:8000
```

이 스크립트는 아래를 검증한다.

- `POLAR_SERVER=production` 여부
- live `POLAR_ACCESS_TOKEN`과 `POLAR_WEBHOOK_SECRET` 존재 여부
- `POLAR_PRODUCT_SINGLE_ID`, `POLAR_PRODUCT_STARTER_ID`, `POLAR_PRODUCT_PRO_ID` 존재 여부
- Polar production 상품 3개의 `plan_id`, `credits`, `KRW` 가격 정합성
- 선택적으로 `/billing/catalog` 응답 정합성

## Polar sandbox 사전 점검

로컬 리허설에는 sandbox 사전 점검을 사용한다.

```bash
py scripts/polar_sandbox_preflight.py
```

로컬 백엔드까지 함께 점검하려면 아래처럼 실행한다.

```bash
py scripts/polar_sandbox_preflight.py --api-base-url http://localhost:8000
```

sandbox 상품 3개를 코드로 맞추려면 아래 스크립트를 사용한다.

```bash
py scripts/bootstrap_polar_sandbox_catalog.py
```

## 테스트

```bash
pytest -q tests/test_auth.py tests/test_billing.py tests/test_job_response_fields.py
```

운영 연동 체크리스트는 `docs/polar_production_runbook_ko.md`를 참고한다.
Cloud Run 운영 런북은 `docs/cloud_run_supabase_free_runbook_ko.md`를 참고한다.
로컬 sandbox 리허설은 `docs/polar_sandbox_runbook_ko.md`를 참고한다.
