Done
- `POST /jobs/{job_id}/run`, `POST /jobs/{job_id}/regions/auto-detect` 를 Cloud Tasks enqueue `202` 응답 + internal worker 구조로 전환 완료.
- service-role pipeline/billing 경로, worker OIDC 검증, 프런트 `running` polling, 관련 테스트/문서 반영 완료.

In Progress
- 최우선 과제: 운영 Cloud Tasks/IAM/Cloud Run/Vercel 반영 및 실서버 QA
- 진행 상태: 코드, 백엔드 테스트, 프런트 테스트, 프런트 빌드는 통과했고 운영에는 아직 Cloud Tasks queue/환경변수/IAM 이 반영되지 않았다.
- 다음 단계: Cloud Tasks queue 생성 -> Cloud Run 환경변수 5개 추가 및 재배포 -> enqueue 권한/invoke 권한 부여 -> Vercel same-origin `/jobs` 실행 QA

Next
- `POST /jobs/{job_id}/run`, `POST /jobs/{job_id}/regions/auto-detect` 실운영 `202` 응답 확인
- `GET /jobs/{job_id}` polling 으로 `completed|failed|queued|exported` 전이 확인
- Cloud Tasks queue depth, worker 호출 로그, Vercel `ROUTER_EXTERNAL_TARGET_ERROR` 미재현 확인

Related Files
- /D:/03_PROJECT/05_mathOCR/02_main/app/main.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/job_tasks.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/billing.py
- /D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/repository.py
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/store/jobStore.ts
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx
- /D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx
- /D:/03_PROJECT/05_mathOCR/02_main/docs/cloud_run_supabase_free_runbook_ko.md

Last State
- 2026-04-14 18:04 KST 기준 검증 완료: `py -3 -m pytest 02_main/tests/test_config.py 02_main/tests/test_job_task_queue_api.py -q`, `py -3 -m pytest 02_main/tests/test_billing.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_pipeline_storage.py -q`, `npm.cmd run test:run -- src/app/api/jobApi.test.ts src/app/store/jobStore.test.tsx src/app/components/JobDetailPage.test.tsx src/app/components/NewJobPage.test.tsx`, `npm.cmd run build`
- 이번 변경은 Cloud Tasks queue 생성, IAM, Cloud Run 환경변수 반영, 재배포, Vercel/모바일 실서버 QA가 반드시 함께 필요하다.
