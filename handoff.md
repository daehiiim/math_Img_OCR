Done
- 공개 홈 히어로에 조건부 그레이스케일 타임랩스 배경을 추가했고 실서비스용 파생 자산 `hero-timelapse.webm`, `hero-timelapse.mp4`, `hero-timelapse-poster.jpg`를 `04_design_renewal/src/assets/home/`에 반영했다.
- `/new` 작업 생성 화면에서 업로드 미리보기 카드를 제거하고 큰 영역 지정 캔버스 중심 레이아웃으로 재배치했다.
- 배포 DB에 `problem_markdown`, `explanation_markdown`, `markdown_version` 컬럼이 없어도 파이프라인 실행과 과금 점검이 구스키마 fallback으로 계속 동작하도록 백엔드 호환 로직을 추가했다.
- 백엔드 회귀 검증 `py -3 -m pytest 02_main/tests/test_pipeline_storage.py 02_main/tests/test_billing.py 02_main/tests/test_job_response_fields.py -q`에서 `67 passed`를 확인했다.

In Progress
- 최우선 과제: 공개 홈 히어로 타임랩스의 실서비스 QA 및 농도 미세조정
- 진행 상태: 데스크톱 `min-width: 768px` + `prefers-reduced-motion: no-preference`에서만 비디오가 재생되고, `screen` blend 기반 가시성 조정을 반영했다. 모바일에서는 poster만 유지된다.
- 다음 단계: 운영 브라우저에서 실제 첫 인상과 CTA 가독성을 다시 확인하고 필요 시 opacity/filter만 미세조정한다.

Next
- 실서비스 배포본에서 히어로 배경 존재감과 헤드라인 대비를 재확인
- `prefers-reduced-motion` 환경의 실기기 QA
- 백엔드 API를 재배포한 뒤 `/jobs/{job_id}/run` 실서비스 smoke로 구스키마 fallback 동작을 확인

Related Files
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\styles\theme.css`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\NewJobPage.tsx`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\repository.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\billing.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\schema_compat.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_storage.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_billing.py`

Last State
- 프런트 히어로 배경은 장식 전용이며 비디오 실패/자동재생 차단 시 사용자 메시지 없이 poster + 기존 블랙 배경으로 폴백한다.
- 2026-03-23 15:05 KST 기준 비디오는 정상 재생되며, visibility 이슈는 CSS 톤 조정으로 완화했다.
- `/new` 화면은 업로드 미리보기 대신 큰 영역 지정 캔버스와 파일 교체 버튼을 노출한다.
- 백엔드 API 계약과 DB migration 파일 자체는 바꾸지 않았고, 미배포 migration 상태에서도 새 Markdown 컬럼을 생략해 구스키마로 동작한다.
- 배포 환경 변수 변경은 없지만, 이번 수정 반영에는 백엔드 서비스 재배포가 필요하다.
