Done
- `ordered_segments`, `raw_transcript`, 객관식 정답 검증 필드를 OCR 파이프라인, 저장소, API 응답까지 연결했다.
- 객관식 정답 번호/값이 선택지와 충돌하면 해설을 안전 경고 문구로 치환하도록 수정했다.
- direct HwpForge `section0.xml` 수식 폭 재보정과 프런트 검증 경고 표시까지 반영했다.
- 문제/정상 HWPX 비교 결과를 반영해 해설 mixed 수식의 compact box profile(`height=975`, `baseLine=86`) 보정까지 넣었다.
- `02_main` 전체 pytest `165 passed`, 프런트 검증 경고 관련 vitest `24 passed`를 확인했다.

In Progress
- 최우선 과제: 운영 반영용 DB 마이그레이션 적용 및 실문서 수동 QA
- 진행 상태: 코드와 자동 회귀는 끝났고 [2026-03-25_ocr_verification_fields.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-25_ocr_verification_fields.sql) 까지 준비됐다. bad 파일을 현재 보정 로직으로 직접 후처리한 [생성결과 (1)_repaired_by_codex.hwpx](/D:/03_PROJECT/05_mathOCR/error/생성결과%20(1)_repaired_by_codex.hwpx) 에서 answer 파일과 동일한 equation box metrics도 확인했다. 아직 운영 DB 적용, 백엔드/프런트 재배포, 실제 HWPX 산출물 수동 확인은 남아 있다.
- 다음 단계: 운영 DB에 신규 컬럼 마이그레이션을 적용하고 백엔드/프런트를 재배포한 뒤 실제 OCR 이미지로 HWPX 결과를 열어 문제 원문, 수식 여백, 해설 경고 표시를 확인한다.

Next
- `02_main/schemas/2026-03-25_ocr_verification_fields.sql` 운영 적용
- 백엔드 재배포 후 `/jobs` 응답에 신규 검증 필드가 내려오는지 확인
- 실제 한글 문서 열람으로 짧은 수식 폭과 해설 경고 치환 수동 QA

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\extractor.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\orchestrator.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\repository.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpx_math_layout.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\schemas\2026-03-25_ocr_verification_fields.sql`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\JobDetailPage.tsx`
- `D:\03_PROJECT\05_mathOCR\error\생성결과 (1).hwpx`
- `D:\03_PROJECT\05_mathOCR\error\생성결과 (1)_answer.hwpx`
- `D:\03_PROJECT\05_mathOCR\error\생성결과 (1)_repaired_by_codex.hwpx`
- `D:\03_PROJECT\05_mathOCR\error_patterns.md`

Last State
- OCR 원문은 `ordered_segments` 기반으로 조립되고 `raw_transcript`를 별도로 저장한다.
- 객관식 해설은 구조화 응답을 받아 선택지와 대조하고, 불일치 시 안전 경고 문구로만 출력한다.
- final HWPX는 legacy/direct 공통으로 해설 inline equation의 `width/height/baseLine` compact profile까지 다시 맞춘다.
- 신규 환경 변수는 없지만 DB 마이그레이션과 백엔드 재배포가 필요하다.
