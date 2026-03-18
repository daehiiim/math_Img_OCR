이 디렉터리는 `hwpxskill-math` 런타임 subset을 백엔드 배포 번들에 포함하기 위한 vendored 복사본이다.

- 출처: `C:\Users\user\.codex\skills\hwpxskill-math`
- 포함 범위:
  - `scripts/xml_primitives.py`
  - `scripts/exam_helpers.py`
  - `scripts/hwpx_utils.py`
  - `templates/base/**`
- 갱신 절차:
  - upstream 변경사항을 확인한다.
  - 위 포함 범위만 다시 복사한다.
  - `02_main/tests/test_exporter.py`와 관련 export 테스트를 다시 실행한다.
