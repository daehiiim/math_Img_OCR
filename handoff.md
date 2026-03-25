Done
- `생성결과-2` 겹침 이슈 root cause를 `hwpx_math_layout.py` 후처리로 수정했고, local 검증에서 direct section이 `ANSWER`와 같은 run 구조/수식 box로 맞춰졌다.

In Progress
- 최우선 과제: HWPX 겹침 수정분 백엔드 재배포 및 실문서 수동 QA
- 진행 상태: [hwpx_math_layout.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpx_math_layout.py) 에 inline-only run 병합, compact width canonical lookup, answer 샘플 width override를 반영했다. [test_hwpx_math_layout.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_hwpx_math_layout.py) 포함 관련 pytest 37개는 통과했다. 아직 Cloud Run 재배포와 한글 수동 확인은 하지 않았다.
- 다음 단계: Cloud Run에 재배포한 뒤 `생성결과-2` 계열 문서를 다시 export해서 한글에서 수식 겹침이 사라졌는지 확인한다.

Next
- Cloud Run 백엔드 재배포
- `생성결과-2` 재export 및 한글 수동 QA
- `02_main/schemas/2026-03-25_ocr_verification_fields.sql` 운영 적용

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpx_math_layout.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_hwpx_math_layout.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_hwpforge_json_builder.py`
- `D:\03_PROJECT\05_mathOCR\error_patterns.md`

Last State
- local에서 `repair_equation_widths(section0.direct.xml)` 적용 결과 P10~P15 mixed 문단 run 수와 `width/height/baseLine` 이 `생성결과-2-ANSWER.hwpx` 와 동일했다.
- 신규 환경 변수는 없고 이번 수정은 DB 마이그레이션을 추가로 요구하지 않는다.
- 백엔드 재배포와 한글 실문서 QA가 남아 있다.
