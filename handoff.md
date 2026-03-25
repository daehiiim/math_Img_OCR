Done
- Cloud Run startup blocker resolved. `typing.TypedDict` -> `typing_extensions.TypedDict` fix deployed as revision `mathocr-00024-2rj`, and `GET /billing/catalog` now returns `200`.

In Progress
- 최우선 과제: 운영 DB 마이그레이션 적용 및 실문서 수동 QA
- 진행 상태: 백엔드 최신 코드는 운영 Cloud Run에 반영됐고 startup failure는 해소됐다. 아직 [2026-03-25_ocr_verification_fields.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-25_ocr_verification_fields.sql) 운영 적용과 실제 OCR/HWPX 수동 확인은 남아 있다.
- 다음 단계: 운영 DB 마이그레이션을 적용하고 실제 OCR 이미지로 `/jobs` 신규 검증 필드와 HWPX 산출물을 수동 QA한다.

Next
- `02_main/schemas/2026-03-25_ocr_verification_fields.sql` 운영 적용
- 실제 OCR job 생성 후 `/jobs/{id}` 응답에 검증 필드 확인
- 한글에서 HWPX를 열어 문제 원문, 수식 폭, 해설 경고 문구 수동 QA

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\schema.py`
- `D:\03_PROJECT\05_mathOCR\02_main\requirements.txt`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_pipeline_schema.py`
- `D:\03_PROJECT\05_mathOCR\02_main\schemas\2026-03-25_ocr_verification_fields.sql`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\extractor.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\orchestrator.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\repository.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- `D:\03_PROJECT\05_mathOCR\error_patterns.md`

Last State
- Cloud Run latest ready revision is `mathocr-00024-2rj` and serves 100% traffic.
- Root cause was Pydantic TypedDict compatibility on Python 3.10 during app import.
- 신규 환경 변수는 없고, 남은 운영 작업은 DB 마이그레이션과 실제 HWPX 수동 QA다.
