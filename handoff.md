Done
- `style_guide.hwpx` 기준 base 템플릿으로 HWPX export를 교체하고 metadata title/다운로드 파일명을 `생성결과.hwpx`로 고정했다.
- EXIF 정규화, 2차 crop padding, 이미지 bbox 프롬프트 보수화, OCR/해설 수식 정규화, 문제 번호 재부여, 프런트 결과 미리보기 문구 정리를 반영했다.
- 자동 검증 완료: `py -3 -m pytest 02_main/tests -q` -> `134 passed`, `npm run test:run` -> `102 passed`, `npm run build` 성공

In Progress
- 최우선 과제: 한글에서 새 `생성결과.hwpx` 산출물을 육안 검증
- 진행 상태: 백엔드/프런트 전체 테스트와 빌드는 모두 통과했고 style_guide 기준 paragraph anchor 호환성도 자동 검증했다
- 다음 단계: 실제 OCR job 1건으로 export 후 보기 간격, inline 수식 baseline, 이미지 위치, 다운로드 파일명 표시를 한글과 브라우저에서 확인

Next
- 필요 시 style_guide 기준 세부 문단 간격과 이미지 anchor offset을 미세 조정
- 필요 시 실서비스 샘플 1건으로 `cropUrl`/`imageCropUrl`/`styledImageUrl` 미리보기 의미를 재검증

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\figure.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\extractor.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpx_reference_renderer.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\main.py`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\ResultsViewer.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\api\jobApi.ts`

Last State
- `py -3 -m pytest 02_main/tests/test_pipeline_storage.py 02_main/tests/test_exporter.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_nano_banana_prompt.py 02_main/tests/test_extractor_normalization.py -q` -> `51 passed`
- `py -3 -m pytest 02_main/tests -q` -> `134 passed`
- `cd D:\03_PROJECT\05_mathOCR\04_design_renewal && npm run test:run` -> `25 files / 102 passed`
- `cd D:\03_PROJECT\05_mathOCR\04_design_renewal && npm run build` -> 성공 (기존 chunk size warning 유지)
