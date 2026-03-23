Done
- `hwpx_math_layout.py`를 추가해 `<math>` 분해, 수식 스크립트 정규화, script 길이 측정, equation width 샘플 보간을 공통화했다.
- `hwpforge_json_builder.py`에서 문제 본문을 mixed Text/Equation run으로 재조립하고, problem/choice/explanation equation width를 공통 보간 규칙으로 계산하도록 수정했다.
- `hwpx_reference_renderer.py`도 같은 공통 수식 레이아웃 계층을 사용하도록 정리했다.
- `test_hwpforge_json_builder.py`, `test_exporter.py`, `error_patterns.md`를 갱신했고 `py -3 -m pytest 02_main/tests/test_hwpforge_json_builder.py 02_main/tests/test_exporter.py -q`에서 `32 passed`를 확인했다.

In Progress
- 최우선 과제: 실제 HwpForge 런타임 기준 direct writer 강제 E2E 및 한글 수동 QA
- 진행 상태: 코드 수정과 unit/integration 회귀는 끝났지만, 현재 저장소에 HwpForge MCP 런타임이 없어 `HWPX_EXPORT_ENGINE=hwpforge` 강제 export 실동작 검증은 아직 못 했다.
- 다음 단계: 런타임 경로를 준비한 뒤 강제 hwpforge export를 생성하고 `Contents/section0.xml` 및 한글 열람으로 본문 수식 렌더링과 짧은 수식 여백을 확인한다.

Next
- HwpForge MCP 런타임 설치 또는 경로 연결
- `HWPX_EXPORT_ENGINE=hwpforge` 기준 export smoke 및 `section0.xml` 확인
- 백엔드 재배포 후 실제 export 경로 수동 QA

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpx_math_layout.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpforge_json_builder.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpx_reference_renderer.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_hwpforge_json_builder.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_exporter.py`
- `D:\03_PROJECT\05_mathOCR\error_patterns.md`

Last State
- direct writer는 더 이상 problem `stem`의 `<math>` markup을 literal Text run으로 내보내지 않는다.
- equation width는 템플릿 폭 순환 재사용이 아니라 script 길이 샘플 보간으로 계산한다.
- 배포 환경 변수 변경은 없고 백엔드 코드 재배포만 필요하다.
- 실제 hwpforge 강제 경로 E2E는 런타임 부재 때문에 다음 세션에서 이어서 확인해야 한다.
