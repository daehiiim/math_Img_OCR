# MVP-1 빠른 시작

## 설치
```bash
pip install -r requirements.txt
```

## 서버 실행
```bash
uvicorn app.main:app --reload
```

## 테스트
```bash
pytest -q
```

## 처리 흐름
1. `/jobs` 에 이미지 업로드
2. `/jobs/{jobId}/regions` 에 영역 저장
3. `/jobs/{jobId}/run` 실행
4. `/jobs/{jobId}` 조회
5. `/jobs/{jobId}/export/hwpx` 내보내기
