Done
- 영역 미지정 시 backend가 full-image fallback region(`auto_full`)을 생성해 OCR/해설/export 흐름을 그대로 태우도록 구현했다.
- region metadata(`selection_mode`, `input_device`, `warning_level`)를 backend/frontend에 반영하고, 결과 화면에서 자동 전체 인식 배지와 저신뢰 안내를 표시하도록 정리했다.
- `RegionEditor`를 Pointer Events 기반으로 교체해 모바일/태블릿에서 손가락/펜으로 영역 생성, 모서리 resize, 삭제가 가능하게 했다.
- backend `pytest 174 passed`, frontend `npm run test:run 148 passed`, `npm run build` 성공까지 확인했다.

In Progress
- 최우선 과제: 운영 DB migration 적용 후 실제 모바일 브라우저 smoke QA
- 진행 상태: 코드와 로컬 검증은 끝났고, 아직 [2026-04-02_region_selection_metadata.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-04-02_region_selection_metadata.sql) 운영 반영과 iOS Safari/iPad Safari/Android Chrome 실기기 확인은 남아 있다.
- 다음 단계: migration 적용 -> backend/frontend 재배포 -> 모바일에서 무영역 실행, 드래그 선택, resize, delete, 결과 배지까지 순서대로 확인

Next
- auto_full 저신뢰 판정 threshold를 실데이터 기준으로 미세 조정
- auto_full 전처리(trim/contrast/downscale)가 실제 문제지 샘플에서 과보정되지 않는지 점검

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\orchestrator.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\figure.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\repository.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\schema.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\schema_compat.py`
- `D:\03_PROJECT\05_mathOCR\02_main\schemas\2026-04-02_region_selection_metadata.sql`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\RegionEditor.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\NewJobPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\JobDetailPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.tsx`
- `D:\03_PROJECT\05_mathOCR\error_patterns.md`

Last State
- `2026-04-02 14:55 KST` 기준 auto_full fallback, mobile pointer selection, metadata compat 구현과 로컬 테스트/빌드 검증까지 완료됐다.
- 신규 환경 변수는 없고, 운영 반영에는 backend DB migration + backend/frontend 재배포가 필요하다.
