## 2026-03-20

- Nano Banana 이미지 생성 경로에 `NANO_BANANA_PROVIDER=vertex|gemini_api` 명시 토글을 추가했다.
- `AppSettings`에 `nano_banana_provider`, `gemini_api_key`를 추가하고 `.env.example`에 운영 예시를 반영했다.
- `extractor.py`에서 provider별 필수 설정 검증과 `genai.Client(...)` 초기화를 분리했다.
- `main.py`에서 `GEMINI_API_KEY is not configured`, `Unsupported NANO_BANANA_PROVIDER`를 이미지 생성 설정 오류로 매핑했다.
- `production_nano_banana_web_rollout_ko.md`를 Vertex 대체 문서가 아니라 선택 가능한 provider 운영 문서로 갱신했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\02_main && pytest -q tests` 기준 `104 passed`.
