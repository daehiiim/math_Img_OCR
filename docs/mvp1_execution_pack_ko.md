# MVP-1 실행 패키지

이 문서는 바로 개발에 들어가기 위한 최소 산출물 묶음입니다.

## 포함 파일
- API 명세: `specs/mvp1_openapi.yaml`
- 영역 요청 예시: `schemas/region_set.example.json`
- HWPX 블록 템플릿(초안): `templates/hwpx/problem_block_template.xml`

## 엔드포인트 요약
1. `POST /jobs`
   - 이미지 업로드
   - `job_id` 발급
2. `PUT /jobs/{jobId}/regions`
   - 사용자가 그린 문제 영역 저장
3. `POST /jobs/{jobId}/run`
   - 영역별 OCR/벡터화 작업 시작
4. `GET /jobs/{jobId}`
   - 진행상태/결과 조회
5. `POST /jobs/{jobId}/export/hwpx`
   - HWPX 산출물 생성

## 구현 체크리스트
- [ ] 이미지 저장소 연결 (로컬/S3)
- [ ] region polygon 검증 (최소 점 개수, 좌표 범위)
- [ ] OCR 모듈 어댑터
- [ ] SVG 생성기 어댑터
- [ ] HWPX 조립기(문제 블록 반복 삽입)
- [ ] 실패 region 재처리 API

## 권장 순서
1) API 스켈레톤 생성
2) `PUT /regions` 입력 검증 완성
3) `POST /run`에서 mock 결과 생성
4) `GET /jobs/{id}`로 UI 연동
5) 템플릿 기반 HWPX export
