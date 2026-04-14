Done
- 작업 history 서버 연동 완료: `GET /jobs`, `DELETE /jobs/{job_id}`, `POST /internal/maintenance/purge-stale-jobs` 구현 및 테스트 반영.
- `/workspace` 작업 목록을 서버 history 기준으로 교체 완료: 상태, 생성일, 영역 수, HWPX 준비 여부, running 삭제 비활성화 반영.
- 14일 자동 정리 준비 완료: `MAINTENANCE_JOB_TOKEN`, Supabase 인덱스 migration, Cloud Run/Cloud Scheduler 운영 문서 갱신.

In Progress
- 최우선 과제: 운영 Supabase/Cloud Run/Cloud Scheduler 반영 및 실서버 purge QA
- 진행 상태: 코드·테스트·프런트 빌드는 모두 통과했지만 운영 환경에는 아직 `2026-04-14_job_history_retention_indexes.sql`, `MAINTENANCE_JOB_TOKEN`, Cloud Scheduler job 이 적용되지 않았다.
- 다음 단계: Supabase SQL Editor에 새 migration 적용 -> Cloud Run에 `MAINTENANCE_JOB_TOKEN` 추가 후 재배포 -> Cloud Scheduler `04:10 Asia/Seoul` POST job 생성 -> `/workspace` history 및 maintenance endpoint 수동 호출 QA

Next
- 운영 계정으로 `/workspace` history 렌더링, HWPX badge, running 삭제 비활성화 확인
- 14일 지난 종료 job 테스트 데이터 1건으로 storage prefix + row 동시 삭제 확인
- 첫 Cloud Scheduler 실행 로그에서 `deleted_jobs`, `deleted_objects`, `cutoff_at` 확인

Related Files
- /D:/03_PROJECT/05_mathOCR/02_main/app/main.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/job_history.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/supabase.py
- /D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-04-14_job_history_retention_indexes.sql
- /D:/03_PROJECT/05_mathOCR/02_main/docs/cloud_run_supabase_free_runbook_ko.md
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/DashboardPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/store/jobStore.ts
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/api/jobApi.ts

Last State
- 2026-04-14 14:18 KST 기준 검증 완료: `py -3 -m pytest 02_main/tests/test_config.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_job_history_api.py 02_main/tests/test_supabase_storage_client.py 02_main/tests/test_schema_migration_sql.py 02_main/tests/test_admin_mode.py 02_main/tests/test_pipeline_storage.py -q`, `npm run test:run -- src/app/api/jobApi.test.ts src/app/store/jobMappers.test.ts src/app/store/jobStore.test.tsx src/app/components/DashboardPage.test.tsx src/app/components/JobDetailPage.test.tsx src/app/components/NewJobPage.test.tsx`, `npm run build`
- 이번 변경은 백엔드 API, Supabase migration, Cloud Run 환경변수, Cloud Scheduler 설정이 함께 필요하다.
