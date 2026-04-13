Done
- OpenAI 자동 문항 분할 + 페이지당 1토큰 과금 구현 완료: `POST /jobs/{job_id}/regions/auto-detect`, `selection_mode=auto_detected`, `auto_detect_confidence`, job 1회 과금 플래그, 모바일 UX, 관련 테스트/빌드까지 통과했다.

In Progress
- 최우선 과제: 운영 DB 마이그레이션 적용 후 자동 문항 분할 실서버 QA
- 진행 상태: 로컬 백엔드/프런트 테스트와 빌드는 모두 통과했고, 운영에는 `2026-04-13_auto_detect_regions.sql` 적용이 아직 남아 있다.
- 다음 단계: Supabase에 `2026-04-13_auto_detect_regions.sql` 적용 후 iPhone 14 기준으로 `업로드 → AI가 문항 찾기 → 박스 검토/수정 → 파이프라인 실행` 실브라우저 QA

Next
- 자동 분할 저신뢰 페이지에서 재탐지/수동 수정 UX 확인
- 필요 시 OpenAI 비용 절감을 위한 OpenCV 1차 후보 검출 하이브리드 검토

Related Files
- /D:/03_PROJECT/05_mathOCR/02_main/app/main.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/billing.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/orchestrator.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/region_detector.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/repository.py
- /D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-04-13_auto_detect_regions.sql
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/RegionEditor.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ResultsViewer.tsx
- /D:/03_PROJECT/05_mathOCR/error_patterns.md

Last State
- 2026-04-13 18:56 KST 기준 이번 단계는 백엔드/프런트/DB 스키마가 함께 변경됐다.
- 검증 완료: `py -3 -m pytest 02_main/tests/test_pipeline_storage.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_billing.py`, `npm.cmd run test:run -- NewJobPage.test.tsx JobDetailPage.test.tsx ResultsViewer.test.tsx jobApi.test.ts jobStore.test.tsx jobMappers.test.ts`, `npm.cmd run build`
