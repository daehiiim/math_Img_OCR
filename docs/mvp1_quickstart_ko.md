# MVP-1 빠른 시작

## 0) 의존성 없이 코어 데모 먼저 확인
아래 명령은 FastAPI 설치 없이도 동작합니다.

```bash
python -m app.demo_flow
```

## 1) Docker로 API 서버 실행 (권장)
```bash
docker compose up --build
```

- 접속: `http://localhost:8000/docs`
- 중지: `docker compose down`

## 2) 로컬 Python으로 API 서버 실행
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 3) 테스트
- 코어 테스트(의존성 최소):
```bash
pytest -q tests/test_mvp1_core.py
```

- API 테스트(FastAPI 설치 필요):
```bash
pytest -q tests/test_mvp1_api.py
```

## 처리 흐름
1. `/jobs` 에 이미지 업로드
2. `/jobs/{jobId}/regions` 에 영역 저장
3. `/jobs/{jobId}/run` 실행
4. `/jobs/{jobId}` 조회
5. `/jobs/{jobId}/export/hwpx` 내보내기
