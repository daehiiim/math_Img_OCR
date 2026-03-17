# mathOCR

현재 운영 기준 디렉터리는 아래 두 곳입니다.

- 백엔드 API: `02_main`
- 프런트엔드: `04_design_renewal`

## 빠른 시작

### 1) 백엔드 실행
```bash
cd 02_main
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 백엔드 런타임 설정은 `02_main/.env` 만 사용합니다. 저장소 루트 `.env` 는 백엔드 설정 파일이 아닙니다.
- Swagger: `http://localhost:8000/docs`
- Polar webhook 엔드포인트: `POST /billing/webhooks/polar`
- Polar 사전 점검: `py scripts/polar_sandbox_preflight.py`

### 2) 프런트 실행
```bash
cd 04_design_renewal
copy .env.example .env.local
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

- 프런트 URL: `http://localhost:5173`
- 기본 API base: `VITE_API_BASE_URL=http://localhost:8000`

### 3) 루트 Docker 실행
```bash
docker compose up --build
```

루트 Docker는 내부적으로 `02_main` 백엔드를 실행합니다.

## 운영 배포 계약

- Vercel 프런트 프로젝트의 Root Directory 는 `04_design_renewal` 로 고정합니다.
- Vercel production 환경에는 `APP_URL=https://mathtohwp.vercel.app` 를 반드시 설정하고, Google/Supabase 로그인 복귀 URL과 결제 복귀 URL은 이 값을 기준으로 생성합니다.
- Vercel 운영 프런트는 `/jobs`, `/billing` same-origin 경로를 호출하고 `04_design_renewal/vercel.json` 이 Cloud Run 으로 프록시합니다.
- Vercel production 환경에서는 `VITE_API_BASE_URL` 을 기본값으로 두지 않습니다. 로컬 개발에서만 `http://localhost:8000` 를 사용합니다.
- 백엔드 CORS는 `CORS_ALLOW_ORIGINS`가 없으면 `APP_URL` 1개만 허용합니다. 운영 경로에서는 localhost OAuth/CORS 기본 허용을 사용하지 않습니다.
- Cloud Run 배포는 루트 `Dockerfile` 기준으로 수행하고, 컨테이너는 `${PORT:-8000}` 규칙을 따라야 합니다.
- 비밀값 회전 순서는 `새 비밀값 등록 -> Cloud Run 재배포 -> 운영 검증 -> 구 비밀값 폐기` 순서를 유지합니다.

## 주요 문서

- 백엔드 가이드: `02_main/README.md`
- 백엔드 빠른 시작: `02_main/docs/mvp1_quickstart_ko.md`
- Polar sandbox 런북: `02_main/docs/polar_sandbox_runbook_ko.md`
- 구현 계획 문서: `docs/plans/*`
