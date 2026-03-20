Done
- `result_answer` subtree 복제형 HWPX renderer에서 choice/explanation inline 수식 구조를 reference subtree 기준으로 교정 완료
- choice `<math>` wrapper 제거, explanation mixed anchor 오탐 수정, choice 미파싱 시 gap 생략 처리 완료
- `py -3 -m pytest 02_main\tests\test_exporter.py 02_main\tests\test_pipeline_storage.py -q` 기준 `25 passed`
- 샘플 문서 `templates/generated-example.hwpx` 재생성 완료

In Progress
- 최우선 과제: 한글에서 `generated-example.hwpx` 와 `result_answer.hwpx` 를 나란히 열어 최종 시각 검증
- 진행 상태: XML 구조/회귀 테스트는 통과했고 샘플 산출물도 재생성됨
- 다음 단계: 보기 간격, inline 수식 baseline, 이미지 위치, footer current-page-only를 한글에서 육안 확인

Next
- 시각 검증 결과에 따라 paragraph template 세부 조정 여부 결정
- 필요 시 실제 OCR job 데이터 1건으로 추가 샘플 생성

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpx_reference_renderer.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_exporter.py`
- `D:\03_PROJECT\05_mathOCR\templates\result_answer.hwpx`
- `D:\03_PROJECT\05_mathOCR\templates\generated-example.hwpx`

Last State
- `cd D:\03_PROJECT\05_mathOCR && py -3 -m pytest 02_main\tests\test_exporter.py` -> `14 passed`
- `cd D:\03_PROJECT\05_mathOCR && py -3 -m pytest 02_main\tests\test_exporter.py 02_main\tests\test_pipeline_storage.py -q` -> `25 passed`
- `cd D:\03_PROJECT\05_mathOCR\02_main && [inline python] export_hwpx(...)` -> `D:\03_PROJECT\05_mathOCR\templates\generated-example.hwpx` 생성
