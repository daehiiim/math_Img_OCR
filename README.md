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

## 주요 문서

- 백엔드 가이드: `02_main/README.md`
- 백엔드 빠른 시작: `02_main/docs/mvp1_quickstart_ko.md`
- Polar sandbox 런북: `02_main/docs/polar_sandbox_runbook_ko.md`
- 구현 계획 문서: `docs/plans/*`
