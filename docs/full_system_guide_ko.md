# Math Img OCR MVP-1 전체 기능/작동 방법 상세 가이드

이 문서는 지금까지 구현된 기능과 실제 작동 방법을 한 번에 이해할 수 있도록 정리한 통합 설명서입니다.

---

## 1) 우리가 만든 것 (한 줄 요약)

현재 저장소는 아래를 포함합니다.

- **코어 파이프라인(MVP-1)**: 이미지 업로드 유사 처리 → 영역 저장 → mock OCR/벡터 결과 생성 → HWPX export
- **API 서버(FastAPI)**: Swagger(`/docs`)에서 단계별 실행 가능
- **Docker 실행 환경**: `docker compose up --build`로 API 실행
- **의존성 최소 데모**: `python -m app.demo_flow`로 서버 없이도 전체 흐름 검증
- **테스트 코드**: 코어 테스트 + API 테스트(환경 따라 skip)

---

## 2) 파일 구조와 역할

### 핵심 애플리케이션
- `app/core.py`
  - 실제 MVP 동작 로직의 중심
  - Job 저장/읽기, 영역 검증, mock OCR/SVG 생성, HWPX 내보내기 수행
- `app/main.py`
  - FastAPI 라우터
  - HTTP 요청을 `core.py` 함수로 연결
- `app/demo_flow.py`
  - FastAPI 없이 코어만으로 end-to-end 동작 확인하는 스크립트

### API/스키마/템플릿
- `specs/mvp1_openapi.yaml`: API 초안 명세(OpenAPI)
- `schemas/region_set.example.json`: 영역 입력 JSON 샘플
- `templates/hwpx/problem_block_template.xml`: 문제 단위 HWPX 블록 템플릿

### 실행/운영
- `requirements.txt`: FastAPI 런타임 의존성
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`: 컨테이너 실행 구성
- `.gitignore`: `runtime/`, 캐시 파일 제외

### 문서
- `docs/mvp1_quickstart_ko.md`: 빠른 시작
- `docs/mvp1_execution_pack_ko.md`: MVP-1 실행 패키지 개요
- `docs/multi_problem_ocr_vector_hwp_plan_ko.md`: 확장 설계안

---

## 3) 동작 원리 (내부 흐름)

### 3-1. Job 생성
- 입력 이미지 바이트를 `runtime/jobs/{job_id}/input/`에 저장
- `job.json` 생성 (`status=regions_pending`)

### 3-2. 영역 저장
- 사용자 지정 `regions` 배열 저장
- 각 region은 `id`, `polygon`, `type(text|diagram|mixed)`, `order`를 가짐
- polygon 최소 점 개수(4)와 각 점 좌표 형태([x,y]) 검증

### 3-3. 파이프라인 실행(run)
- 각 영역별로 아래 산출물 생성
  - `outputs/{region_id}.txt` : mock OCR 텍스트
  - `outputs/{region_id}.svg` : polygon 기반 mock SVG
  - `outputs/{region_id}_crop.txt` : crop placeholder
- job 및 region 상태를 `running` -> `completed`로 갱신

### 3-4. 결과 조회(get)
- `job.json`을 읽어 상태 및 region 산출물 경로 반환

### 3-5. HWPX 내보내기(export)
- 템플릿 XML(`problem_block_template.xml`)에 region 값 치환
- `runtime/jobs/{job_id}/exports/{job_id}.hwpx` zip 생성
- zip 내부에 `mimetype` + `Contents/{region_id}.xml` 포함

---

## 4) API 엔드포인트 사용 순서 (실사용 기준)

1. `POST /jobs`
   - multipart/form-data로 `image` 업로드
   - 응답: `job_id`

2. `PUT /jobs/{job_id}/regions`
   - JSON body로 영역 목록 전송

3. `POST /jobs/{job_id}/run`
   - 영역별 처리 실행

4. `GET /jobs/{job_id}`
   - 상태/결과 확인

5. `POST /jobs/{job_id}/export/hwpx`
   - 최종 HWPX 경로 획득

---

## 5) 실행 방법

### A. Docker 실행 (권장)

```bash
docker compose up --build
```

- 접속: `http://localhost:8000/docs`
- 중지: `docker compose down`

> 중요: 반드시 `docker-compose.yml`이 있는 프로젝트 루트에서 실행해야 함.

### B. 로컬 Python 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### C. 의존성 최소 데모 실행 (API 없이)

```bash
python -m app.demo_flow
```

- 콘솔 출력 JSON의 `download_url` 경로에 `.hwpx` 생성

---

## 6) Swagger UI에서 직접 실행하는 법

1. `/docs` 접속
2. `POST /jobs`에서 이미지 업로드 후 Execute
3. 응답 `job_id` 복사
4. `PUT /jobs/{job_id}/regions`에 `job_id`와 body 입력 후 Execute
5. `POST /jobs/{job_id}/run`
6. `GET /jobs/{job_id}`
7. `POST /jobs/{job_id}/export/hwpx`

예시 body:

```json
{
  "regions": [
    {
      "id": "q1",
      "polygon": [[120, 80], [980, 80], [980, 430], [120, 430]],
      "type": "mixed",
      "order": 1
    }
  ]
}
```

---

## 7) 테스트 전략

### 코어 테스트
```bash
pytest -q tests/test_mvp1_core.py
```
- FastAPI 없이 코어 플로우 검증

### API 테스트
```bash
pytest -q tests/test_mvp1_api.py
```
- FastAPI 설치 시 TestClient 기반 API 플로우 검증
- FastAPI 미설치 환경에서는 skip 처리

### 정적/문법 확인
```bash
python -m py_compile app/main.py app/core.py app/demo_flow.py tests/test_mvp1_core.py tests/test_mvp1_api.py tests/conftest.py
```

---

## 8) 현재 MVP 한계 (중요)

- OCR은 **실 인식이 아니라 mock 문자열**
- crop도 실제 이미지가 아닌 placeholder 파일
- SVG도 실제 벡터화 알고리즘이 아닌 polygon 기반 mock
- HWPX는 실사용 가능한 구조의 최소 zip/템플릿 방식이지만, 고급 서식/완전 호환 튜닝은 향후 과제

즉, 현재는 **아키텍처/흐름 검증용 MVP-1**입니다.

---

## 9) 다음 단계 권장

1. 실OCR 엔진(PaddleOCR/Tesseract) 연결
2. 실제 crop 이미지 저장
3. 도형 벡터화(OpenCV contour + 단순화)
4. 작업 큐(비동기 처리) 도입
5. HWPX 레이아웃 템플릿 고도화
6. 프론트 UI(영역 드로잉/결과 미리보기) 본격 구현

---

## 10) 자주 발생한 문제와 해결

### Q1. `docker compose up --build` 했는데 no configuration file
- 원인: 현재 폴더에 `docker-compose.yml` 없음
- 해결: 프로젝트 루트로 이동 후 실행하거나 `-f`로 파일 경로 지정

### Q2. `/docs`는 보이는데 뭘 눌러야 할지 모르겠음
- 해결: `POST /jobs`부터 순서대로 수행 (본 문서 4, 6번 참고)

### Q3. 테스트가 fastapi 없다고 실패
- 코어 테스트 먼저 실행 (`tests/test_mvp1_core.py`)
- API 테스트는 fastapi 설치 후 실행

---

## 11) 최종 정리

지금까지 구축한 시스템은 다음을 이미 만족합니다.

- 실행 가능한 API 골격
- Docker 기반 실행 루트
- 코어 단독 실행 루트
- 테스트 가능한 최소 파이프라인
- HWPX export까지 이어지는 end-to-end 흐름

따라서 데모/검증/기능 확장 출발점으로는 충분히 사용 가능하며,
다음 단계는 mock을 실엔진으로 치환하는 작업입니다.
