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
- 브라우저 인증이나 결제 복귀 흐름까지 확인하려면 `.env`에 `APP_URL=https://mathtohwp.vercel.app` 또는 허용할 프런트 도메인을 함께 설정해야 합니다.

### Docker
```bash
docker compose up --build
```

- Swagger: `http://localhost:8000/docs`
- CORS 기본 허용은 더 이상 localhost가 아니다. `CORS_ALLOW_ORIGINS`가 없으면 `APP_URL` 1개만 허용한다.

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

- `CORS_ALLOW_ORIGINS` (`https://a.example.com,https://b.example.com` 형식)

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

## Polar sandbox 사전 점검

```bash
py scripts/polar_sandbox_preflight.py
```

로컬 백엔드까지 함께 점검하려면 아래처럼 실행합니다.

```bash
py scripts/polar_sandbox_preflight.py --api-base-url http://localhost:8000
```

sandbox 상품 3개를 코드로 맞추려면 아래 스크립트를 사용합니다.

```bash
py scripts/bootstrap_polar_sandbox_catalog.py
```

## 테스트

```bash
pytest -q tests/test_auth.py tests/test_billing.py tests/test_job_response_fields.py
```

운영 연동 체크리스트는 `docs/polar_sandbox_runbook_ko.md`를 참고하면 됩니다.
