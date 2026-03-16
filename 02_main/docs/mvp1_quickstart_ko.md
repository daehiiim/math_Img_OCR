# mathOCR 빠른 시작

## 1) 백엔드 API 실행

### A. Docker 실행
```bash
docker compose up --build
```

- Swagger: `http://localhost:8000/docs`
- API base: `http://localhost:8000`

### B. 로컬 Python 실행
```bash
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2) 프론트 실행

`D:\03_PROJECT\05_mathOCR\04_design_renewal` 기준:

```bash
copy .env.example .env.local
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

- 프런트 URL: `http://localhost:5173`
- 기본 API base: `VITE_API_BASE_URL=http://localhost:8000`

## 3) Polar 결제 준비

- Polar Dashboard에 USD one-time product 3개 생성
- 각 상품 metadata에 `plan_id`, `credits` 설정
- `POLAR_PRODUCT_SINGLE_ID`, `POLAR_PRODUCT_STARTER_ID`, `POLAR_PRODUCT_PRO_ID` 환경변수 설정
- Stripe Connect Express payout account를 Polar Finance에서 연결
- webhook endpoint를 `POST /billing/webhooks/polar`로 등록
- 사전 점검은 `py scripts/polar_sandbox_preflight.py`로 먼저 확인
- catalog 생성/확인은 `py scripts/bootstrap_polar_sandbox_catalog.py`로 처리 가능

## 4) 기본 API 흐름

1. `POST /jobs` 이미지 업로드
2. `PUT /jobs/{job_id}/regions` 영역 저장
3. `POST /jobs/{job_id}/run` 실행
4. `GET /jobs/{job_id}` 상태/결과 조회
5. `POST /billing/checkout` 결제 세션 생성
6. `POST /billing/webhooks/polar` 크레딧 적립
7. `POST /jobs/{job_id}/export/hwpx` 내보내기

## 5) 테스트

### 결제/설정 테스트
```bash
pytest -q tests/test_config.py tests/test_billing.py
```

### 응답 구조 테스트
```bash
pytest -q tests/test_job_response_fields.py
```

운영 연동은 `polar_sandbox_runbook_ko.md`를 기준으로 진행한다.
