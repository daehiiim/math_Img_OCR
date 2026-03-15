# MVP-1 빠른 시작

## 0) 코어 데모(백엔드 의존성 최소)
FastAPI 없이 파이프라인 코어만 확인할 수 있습니다.

```bash
python -m app.demo_flow
```

## 1) 백엔드 API 실행
### A. Docker 실행(권장)
```bash
docker compose up --build
```

- Swagger: `http://localhost:8000/docs`
- API base: `http://localhost:8000`
- 중지: `docker compose down`

### B. 로컬 Python 실행
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2) 프론트 데모 웹 실행 (`mathOCR_design`)
`D:/project/mathOCR/mathOCR_design` 기준:

```bash
cp .env.example .env
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

- 프론트 URL: `http://localhost:5173`
- 기본 API base: `VITE_API_BASE_URL=http://localhost:8000`

## 3) CORS 설정(필요 시)
백엔드는 기본적으로 아래 origin을 허용합니다.

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:4173`
- `http://127.0.0.1:4173`

추가 origin이 필요하면 백엔드 실행 전에 환경변수를 지정하세요.

```bash
# Windows PowerShell
$env:CORS_ALLOW_ORIGINS = "http://localhost:5173,http://localhost:3000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4) E2E API 흐름
1. `POST /jobs` 이미지 업로드
2. `PUT /jobs/{job_id}/regions` 영역 저장
3. `POST /jobs/{job_id}/run` 실행
4. `GET /jobs/{job_id}` 상태/결과 조회
5. `POST /jobs/{job_id}/export/hwpx` 내보내기

## 5) 테스트
### 코어 테스트
```bash
pytest -q tests/test_mvp1_core.py
```

### API 테스트
```bash
pytest -q tests/test_mvp1_api.py
```
