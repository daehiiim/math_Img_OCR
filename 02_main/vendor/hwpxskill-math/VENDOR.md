## 출처

- upstream source: `C:\Users\user\.codex\skills\hwpxskill-math`
- vendored date: `2026-03-18`

## 포함 범위

- `scripts/xml_primitives.py`
- `scripts/exam_helpers.py`
- `scripts/hwpx_utils.py`
- `templates/base/**`

## 갱신 절차

1. upstream `hwpxskill-math`에서 위 파일만 다시 복사한다.
2. `py -m pytest 02_main/tests/test_exporter.py 02_main/tests/test_pipeline_storage.py -q`를 실행한다.
3. 실제 HWPX export가 성공하는지 추가 검증한다.
