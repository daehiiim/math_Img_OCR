Done
- Nano Banana provider 토글(`vertex|gemini_api`) 구현 완료
- `GEMINI_API_KEY`/`NANO_BANANA_PROVIDER` 설정 로딩, provider별 `genai.Client(...)` 분기, API 에러 매핑 반영 완료
- `.env.example` 및 운영 전환 문서 갱신 완료

In Progress
- 최우선 과제: 운영 Cloud Run/Secret Manager 반영과 실데이터 검증
- 진행 상태: 코드와 백엔드 테스트는 완료됐고 운영 반영은 아직 미실행
- 다음 단계: `NANO_BANANA_PROVIDER=gemini_api` 적용 후 실데이터 1건으로 로그와 저장 결과 확인

Next
- Cloud Run에 새 `GEMINI_API_KEY`를 Secret Manager로 주입
- Cloud Run에 `NANO_BANANA_PROVIDER=gemini_api` 설정
- 실데이터 1건에서 `styled_image_url`, `styled_image_model`, 로그 `provider=gemini_api` 확인
- 필요 시 `NANO_BANANA_PROVIDER=vertex`로 되돌려 즉시 롤백 검증
- 기존 Polar production preflight 실패 원인(`POLAR_ACCESS_TOKEN does not match POLAR_SERVER`)은 별도 운영 점검 필요

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\config.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\extractor.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- `D:\03_PROJECT\05_mathOCR\02_main\.env.example`
- `D:\03_PROJECT\05_mathOCR\02_main\docs\production_nano_banana_web_rollout_ko.md`

Last State
- 백엔드 검증: `cd D:\03_PROJECT\05_mathOCR\02_main && pytest -q tests` -> `104 passed`
- 프런트 변경 없음
