Done
- HwpForge direct writer를 메인 경로로 올렸다. exporter는 이제 `direct export IR -> HwpForge writer -> section0.xml`을 먼저 시도한다.
- bridge 구조는 메인 경로에서 제거됐다. 기존 `legacy baseline -> HwpForge roundtrip section 교체`는 fallback 전용으로만 남아 있다.
- direct writer 구현은 `02_main/app/pipeline/hwpforge_roundtrip.py`의 `build_section_via_hwpforge()`와 `02_main/app/pipeline/hwpforge_json_builder.py`를 사용한다.
- direct writer 템플릿 자산 `02_main/templates/hwpx/hwpforge_generated_canonical_sample.json`을 추가했고, 루트 `Dockerfile`도 이를 `/app/templates/hwpx`로 함께 복사한다.
- 컨테이너 smoke 완료:
- `build_section_via_hwpforge()` 직접 실행 성공
- `export_hwpx()` end-to-end 성공
- 루트 배포 이미지와 `02_main/Dockerfile` 이미지 둘 다 성공
- 검증 완료:
- `py -3 -m pytest 02_main/tests/test_hwpforge_roundtrip.py 02_main/tests/test_hwpforge_json_builder.py 02_main/tests/test_exporter.py 02_main/tests/test_pipeline_storage.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_billing.py -q` -> `98 passed`
- `cd 04_design_renewal && npm run test:run -- src/app/store/jobStore.test.tsx src/app/api/jobApi.test.ts src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts` -> `21 passed`
- `docker build -t mathocr-api-hwpforge-web .` 성공
- `docker build -f 02_main/Dockerfile -t mathocr-api-local-hwpforge 02_main` 성공
- root/local 컨테이너에서 direct writer 및 exporter smoke 모두 성공

In Progress
- 최우선 과제: direct writer 결과 품질을 Markdown 중심 입력과 multi-region 실데이터 기준으로 넓힌다.
- 진행 상태: 현재 direct writer는 main path에서 정상 동작하고, 실패 시만 roundtrip/legacy fallback을 탄다.
- 다음 단계: Markdown 필드 우선 사용, HwpForge 전용 에러 코드 노출, 실서비스 Cloud Run smoke.

Next
- direct writer 입력을 `problem_markdown` / `explanation_markdown` 우선으로 확장
- HwpForge 전용 에러 코드를 API와 프런트 사용자 메시지에 반영
- multi-region / 이미지 우선순위 / 빈 해설 / 보기 없는 문항 회귀 테스트 확대
- Cloud Run 실제 서비스에 새 루트 이미지 재배포 후 `/jobs/{id}/export/hwpx` 실서비스 smoke

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpforge_roundtrip.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpforge_json_builder.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\templates\hwpx\hwpforge_generated_canonical_sample.json`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_hwpforge_roundtrip.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_hwpforge_json_builder.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_exporter.py`
- `D:\03_PROJECT\05_mathOCR\Dockerfile`
- `D:\03_PROJECT\05_mathOCR\.dockerignore`

Last State
- 웹사이트가 쓰는 same-origin `/jobs/{id}/export/hwpx` 경로는 그대로 유지된다.
- 컨테이너 기본값 `HWPX_EXPORT_ENGINE=auto`에서는 direct writer를 우선 시도하고, direct 실패 시 roundtrip/legacy fallback으로 정상 파일 출력을 유지한다.
- 배포 환경 영향이 있다. Cloud Run은 새 루트 `Dockerfile` 이미지로 재배포해야 direct writer 자산과 런타임 번들이 운영에 반영된다.
