Done
- auto-detect 스키마 드리프트 진단 및 재발 방지 추가: auto-detect 전용 500 안내 문구, `py scripts/schema_preflight.py`, README/Cloud Run 런북/에러 패턴 갱신, 관련 테스트 통과.

In Progress
- 최우선 과제: 운영 Supabase 런타임 스키마 누락분 반영 후 auto-detect 실서버 QA
- 진행 상태: `py scripts/schema_preflight.py` 기준 현재 환경에서 `ocr_jobs.auto_detect_charged`, `ocr_job_regions.problem_markdown` 누락이 확인됐고, `AI가 문항 찾기`는 이 드리프트로 500이 난다.
- 다음 단계: Supabase SQL Editor에서 `2026-03-19_region_action_credit_flags.sql`, `2026-04-13_markdown_first_hwpx_v2.sql`, `2026-04-13_auto_detect_regions.sql` 적용 여부 확인 및 누락분 반영 -> `py scripts/schema_preflight.py` 재실행 -> iPhone 14 기준 `업로드 → AI가 문항 찾기 → 박스 검토/수정 → 파이프라인 실행` QA

Next
- auto-detect 성공 후 `credit_ledger.reason=auto_detect_charge`, `ocr_jobs.auto_detect_charged` 반영 확인
- 저신뢰 페이지 재탐지/수동 수정 UX 확인

Related Files
- /D:/03_PROJECT/05_mathOCR/02_main/app/main.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/schema_preflight.py
- /D:/03_PROJECT/05_mathOCR/02_main/scripts/schema_preflight.py
- /D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-04-13_auto_detect_regions.sql
- /D:/03_PROJECT/05_mathOCR/02_main/README.md
- /D:/03_PROJECT/05_mathOCR/02_main/docs/cloud_run_supabase_free_runbook_ko.md
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx
- /D:/03_PROJECT/05_mathOCR/error_patterns.md

Last State
- 2026-04-14 10:35 KST 기준 운영 500 원인은 auto-detect 관련 migration 미적용으로 확정했다.
- 검증 완료: `D:\03_PROJECT\05_mathOCR\.tmp\pydeps-latest\bin\pytest.exe 02_main/tests/test_billing.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_polar_preflight.py 02_main/tests/test_schema_preflight.py -q`
- 프런트는 `AI가 문항 찾기` CTA/토스트/도크에서 `1토큰` 문구를 제거했고, 차감은 기존 서버 흐름대로 자동 처리한다.
