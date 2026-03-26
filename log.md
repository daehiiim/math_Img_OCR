## 2026-03-20

- `result_answer` 정합형 HWPX subtree renderer의 direct paragraph anchor 판별을 보강했다. 해설 mixed 문단 탐색이 choice 문단을 잘못 잡던 문제를 `paraPrIDRef=4`, `styleIDRef=0`, equation 존재 조건으로 교정했다.
- choice parser가 `① <math>...</math>` 형태의 OCR 선택지를 그대로 `hp:script`에 넣던 문제를 수정했다. 이제 단일 `<math>` wrapper는 제거하고 내부 script만 주입한다.
- choice 파싱이 실패한 경우 reference blank paragraph까지 강제로 붙이던 흐름을 정리했다. 선택지가 없으면 choice 문단과 choice gap을 모두 생략한다.
- 새 renderer 기준 회귀를 검증했다: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_exporter.py` 기준 `14 passed`.
- exporter/storage 연동까지 포함해 재검증했다: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_exporter.py 02_main\\tests\\test_pipeline_storage.py -q` 기준 `25 passed`.
- 새 renderer 코드로 샘플 문서를 다시 생성했다: `templates/generated-example.hwpx`.

- Nano Banana 이미지 생성 경로에 `NANO_BANANA_PROVIDER=vertex|gemini_api` 명시 토글을 추가했다.
- `AppSettings`에 `nano_banana_provider`, `gemini_api_key`를 추가하고 `.env.example`에 운영 예시를 반영했다.
- `extractor.py`에서 provider별 필수 설정 검증과 `genai.Client(...)` 초기화를 분리했다.
- `main.py`에서 `GEMINI_API_KEY is not configured`, `Unsupported NANO_BANANA_PROVIDER`를 이미지 생성 설정 오류로 매핑했다.
- `production_nano_banana_web_rollout_ko.md`를 Vertex 대체 문서가 아니라 선택 가능한 provider 운영 문서로 갱신했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\02_main && pytest -q tests` 기준 `104 passed`.
- 다음 AI agent가 이어서 작업할 수 있도록 루트 `description.md`를 작성하고 `handoff.md`의 관련 파일 목록에 연결했다.
- Billing RLS 장애 복구를 위해 `SupabaseBillingStore`의 과금 write 경로를 user JWT client에서 service role admin client로 옮겼다.
- `main.py`에 billing persistence/config 전용 에러 매핑을 추가해 `credit_ledger` RLS 실패를 storage 503이 아니라 billing 500으로 분리했다.
- 회귀 테스트를 추가했다: `tests/test_billing.py`에서 admin client write 경로와 billing 전용 HTTP detail을 검증했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\02_main && pytest -q tests/test_billing.py tests/test_job_response_fields.py` 기준 `45 passed`.
- 운영 배포를 수행했다: `cd D:\\03_PROJECT\\05_mathOCR\\02_main && gcloud run deploy mathocr --source . --region us-central1 --project sapient-stacker-468504-r6 --quiet`.
- 운영 실데이터 검증 결과, 기존 실패 job `ec422fd2-a33c-4a3f-8e44-6a1f52025b87` 재실행이 `200`으로 복구됐고 `credit_ledger.reason=image_stylize_charge`, `ocr_job_regions.image_charged=true`, `ocr_jobs.was_charged=true`가 반영됐다.
- Cloud Run request 로그 기준 동일 job `/run` 요청이 `2026-03-20T04:04:11Z`에는 `503`, 배포 후 `2026-03-20T04:42:39Z`에는 `200`으로 기록됐다.
- 현재 작업트리에는 별도 선행 변경이 남아 있다: `tests/test_config.py`, `tests/test_nano_banana_prompt.py`. 이 변경 때문에 `pytest -q tests/test_billing.py tests/test_job_response_fields.py tests/test_config.py tests/test_nano_banana_prompt.py` 실행 시 `NANO_BANANA_PROMPTS_DIR` import 누락으로 `tests/test_nano_banana_prompt.py` 수집 에러가 난다.
- Polar 운영 결제 장애의 직접 원인을 확정했다. Cloud Run이 참조하는 production Product 3개는 활성 상태였지만 metadata가 모두 비어 있어 `/billing/catalog` 이 `400 {"detail":"missing plan_id metadata"}` 로 실패했다.
- Polar SDK로 production Product 3개 metadata를 운영 계약값으로 복구했다: `single/1`, `starter/100`, `pro/200`.
- 복구 후 `curl https://mathtohwp.vercel.app/billing/catalog` 기준 `200`과 3개 플랜 응답을 확인했고, 브라우저 `/pricing` 화면에서도 `결제 설정 점검 중` 문구 없이 구매 버튼 3개가 노출되는 것을 확인했다.
- HS256 Supabase JWT를 생성해 인증된 `POST /billing/checkout` 를 호출했고 live checkout 세션 생성 성공과 `GET /billing/checkout/{id}` 의 `status=open`, `credits_applied=false` 를 확인했다.
- 로컬 `02_main/.env` 의 Polar live token, webhook secret, product ID 3개를 Cloud Run 운영값으로 동기화했다.
- `cd D:\\03_PROJECT\\05_mathOCR\\02_main && py scripts/polar_production_preflight.py` 와 `py scripts/polar_production_preflight.py --api-base-url https://mathocr-146126176673.us-central1.run.app` 를 재실행해 전체 `OK` 를 확인했다.
- 현재 live 가격은 Polar production 기준 `single=100 KRW`, `starter=9900 KRW`, `pro=19000 KRW` 로 확인됐다. 프런트 fallback/test 상수의 `1000/19000/29000` 와는 다르지만, 이번 패스에서는 매출 복구만 우선해 metadata만 수정했고 가격 정책 변경은 보류했다.
- 사용자 결정에 따라 대안 1을 적용했다. Polar live 가격은 유지하고 프런트 fallback/local mock/test 상수를 `100/9900/19000 KRW` 로 정렬했다.
- 프런트 중복 카탈로그를 줄이기 위해 `04_design_renewal/src/app/lib/billingCatalog.ts` 를 추가하고 `PricingPage.tsx`, `PaymentPage.tsx`, `localUiMock.ts` 가 같은 기본 카탈로그를 재사용하도록 정리했다.
- 프런트 테스트 기대값도 live 가격 기준으로 갱신했다: `billingApi.test.ts`, `PricingPage.test.tsx`, `PaymentPage.test.tsx`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm test -- billingApi.test.ts PaymentPage.test.tsx PricingPage.test.tsx` 기준 `27 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공. Vite chunk size warning은 기존 번들 크기 이슈로 유지됐다.
- 선행 테스트 변경을 실제 구현으로 흡수했다. `extractor.py`에 `NANO_BANANA_PROMPTS_DIR` 기반 자산 로더를 추가하고 프롬프트를 코드 상수 대신 파일에서 조립하도록 바꿨다.
- Nano Banana 프롬프트 자산 디렉터리를 `app/pipeline/prompt_assets/nano_banana` 아래에 만들고 `csat_v1`, `math_general_v1` 각각에 `base`, `style`, `negative`, `kind별` 규칙 파일을 분리했다.
- 지원 프롬프트 버전에 `math_general_v1`를 추가해 범용 수학문제 스타일 실험이 가능하도록 했다.
- 자산 누락, 빈 파일, 읽기 실패를 `NANO_BANANA_PROMPT_ASSET_MISSING`, `NANO_BANANA_PROMPT_ASSET_EMPTY`, `NANO_BANANA_PROMPT_ASSET_READ_ERROR`로 로깅하고 `ValueError`로 올리도록 정리했다.
- `tests/test_nano_banana_prompt.py`, `tests/test_config.py`를 확장해 새 버전 지원, 자산 누락 실패, 자산 기반 프롬프트 조합을 검증했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\02_main && pytest -q tests` 기준 `112 passed`.
- Polar checkout 기본 청구지 국가 preset 요구를 반영했다. `app/billing.py`의 `PolarGateway.create_checkout`에서 `customer_billing_address.country=KR`, `require_billing_address=true`를 추가했다.
- 같은 파일에 checkout 진단 헬퍼를 추가해 `payment_processor`, `is_payment_required`, `is_payment_form_required`, `customer_billing_address`, `billing_address_fields`, `currency`, `amount`, `product_id`, `product_price_id`를 읽도록 정리했다.
- 운영 checkout 진단용 CLI `scripts/polar_checkout_inspect.py`를 추가했다. `--checkout-id` 하나로 JSON 진단값과 운영 메시지를 출력한다.
- `docs/polar_production_runbook_ko.md`에 `South Korea` preset 확인, checkout 생성 직후/`Pay now` 직후 재진단, processor 설정 우선 점검 절차를 추가했다.
- 회귀 테스트를 추가했다. `tests/test_billing.py`에서 gateway payload/진단 매핑을 검증하고 `tests/test_polar_checkout_inspect.py`에서 스크립트 메시지를 검증한다.
- optional checkout 필드가 `PydanticUndefined`일 때도 진단 dict가 `None`으로 정규화되도록 보강했고 회귀 테스트를 추가했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3.14 -m pytest 02_main\\tests\\test_billing.py 02_main\\tests\\test_polar_checkout_inspect.py` 기준 `44 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3.14 02_main\\scripts\\polar_checkout_inspect.py --help` 성공.
- OpenAI 연결 상태에서 남은 이미지 수를 `∞`가 아니라 실제 `credits` 값으로 보여주도록 `DashboardPage`, `AuthLayout`, `StudioLayout`을 수정했고, 대시보드에서 OpenAI 연결 여부와 무관하게 이미지 충전 CTA를 노출하도록 정리했다.
- `OpenAiConnectionPage`, `PublicHomePage`의 무료/무제한 뉘앙스 문구를 제거하고 `OCR·해설은 사용자 OpenAI key`, `이미지 생성은 크레딧 필요` 정책으로 안내 문구를 교정했다.
- 프런트 회귀 테스트를 추가했다: `DashboardPage.test.tsx`, `AuthLayout.test.tsx`, `StudioLayout.test.tsx`, `OpenAiConnectionPage.test.tsx`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/DashboardPage.test.tsx src/app/components/AuthLayout.test.tsx src/app/components/StudioLayout.test.tsx src/app/components/OpenAiConnectionPage.test.tsx src/app/components/PublicHomePage.test.tsx src/app/components/NewJobPage.test.tsx src/app/components/JobDetailPage.test.tsx src/app/components/Layout.test.tsx` 기준 `17 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공. Vite chunk size warning은 기존 번들 크기 경고로 유지됐다.
- EXIF 회전 정규화와 2차 crop 패딩 회귀를 `02_main/app/pipeline/figure.py`, `02_main/app/pipeline/orchestrator.py`, `02_main/tests/test_pipeline_storage.py`에 반영했다.
- `figure.py`에 EXIF orientation 공통 헬퍼, 정규화된 이미지 크기 판독, 보수적 bbox 확장 crop 로직을 추가했다.
- `orchestrator.py`는 업로드 이미지 크기 판독을 정규화 헬퍼로 재사용하도록 바꿨다.
- `test_pipeline_storage.py`에 EXIF orientation JPEG의 크기/문제 crop 정규화 테스트와 stylizable image bbox padding 테스트를 추가했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_pipeline_storage.py -q` 기준 `14 passed`.
- HWPX 생성 품질 보정 플랜을 반영했다. `style_guide.hwpx`의 `header.xml`, `section0.xml`, `content.hpf`를 새 base로 채택하고 export metadata title과 다운로드 파일명을 모두 `생성결과.hwpx`로 고정했다.
- `hwpx_reference_renderer.py`에 export 전용 정규화 계층을 추가해 OCR 선행 문제 번호를 제거하고 `\triangle`, `\angle`, `\frac`, `degree` 같은 LaTeX 잔재를 HWP 친화 스크립트로 변환했다.
- `extractor.py`에는 OCR/수식/해설 공통 정규화 계층을 추가했다. OCR 본문에서는 `1.`, `12)` 같은 번호 접두사를 제거하고, 해설과 수식 마크업은 HWP Equation Script에 맞게 후처리한다.
- Nano Banana 프롬프트 자산은 `problem numbers`, `multiple-choice numbers`, `general sentences`, `table layouts`를 이미지 대상에서 제외하도록 더 보수적으로 조정했다.
- `figure.py`, `orchestrator.py`는 EXIF 회전을 업로드 크기 판독과 실제 crop 양쪽에 동일하게 적용하고, stylizable image 2차 crop에는 안전 패딩을 추가했다.
- 프런트 `ResultsViewer`, `JobDetailPage`, `jobApi`, `jobStore`는 `cropUrl -> 문제 영역 크롭`, `imageCropUrl -> 이미지 추출 원본`, `styledImageUrl -> 이미지 생성 결과` 의미로 정리했고 `styledImageModel` 배지와 `Nano Banana` 문구를 제거했다.
- 백엔드 회귀 테스트를 확장했다: `test_exporter.py`, `test_job_response_fields.py`, `test_pipeline_storage.py`, `test_extractor_normalization.py`, `test_nano_banana_prompt.py`.
- 프런트 회귀 테스트를 확장했다: `ResultsViewer.test.tsx`, `JobDetailPage.test.tsx`, `jobApi.test.ts`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_pipeline_storage.py 02_main\\tests\\test_exporter.py 02_main\\tests\\test_job_response_fields.py 02_main\\tests\\test_nano_banana_prompt.py 02_main\\tests\\test_extractor_normalization.py -q` 기준 `51 passed`.
- 리뷰에서 지적된 번호 제거 과잉 적용을 수정했다. OCR/ export 정규화 모두 첫 비어 있지 않은 줄에만 문제 번호 제거를 적용하고, 이후 줄의 소문항/단계 번호는 유지한다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests -q` 기준 `134 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/ResultsViewer.test.tsx src/app/components/JobDetailPage.test.tsx src/app/api/jobApi.test.ts` 기준 `20 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run` 기준 `102 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공. Vite chunk size warning은 기존 번들 크기 경고로 유지됐다.
- 샘플 fixture 기준 실제 exporter를 호출해 검증용 [생성결과.hwpx](/D:/03_PROJECT/05_mathOCR/templates/생성결과.hwpx)를 생성했다.
- 생성 확인: `Contents/content.hpf`의 title이 `생성결과`이고 파일 크기는 `100308 bytes`다.
- 한글 inline 수식 공백의 직접 원인을 `hwpx_reference_renderer.py`의 mixed equation 단일 템플릿 재사용으로 확정했다. 첫 번째 긴 각도식의 `width=8386`이 `ABC`, `ADE` 같은 짧은 수식에도 그대로 복제돼 과도한 공백이 생기고 있었다.
- mixed equation 템플릿을 하나만 쓰지 않도록 수정했다. 이제 mixed 문단의 equation 템플릿 전체를 수집하고, 수식 길이에 가장 가까운 템플릿을 고른 뒤 참조 샘플 폭으로 width를 선형 보간한다.
- 회귀 테스트 `test_export_hwpx_explanation_inline_equations_use_compact_width_for_short_scripts`를 추가했다. 짧은 inline 수식 width가 긴 각도식 width를 그대로 재사용하지 않는지 검증한다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_exporter.py -q` 기준 `17 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_pipeline_storage.py -k export -q` 기준 `2 passed`.
- 생성 XML 점검 결과, 같은 fixture에서 `ANGLE BAC= ANGLE DAE=8386`, `ANGLE ABC= ANGLE ADE=8386`, `ABC=1480`, `ADE=1480`으로 확인됐다.
- 기존 `templates\\생성결과.hwpx`는 다른 프로세스가 점유 중이라 현재 세션에서 덮어쓰지 못했다. 실제 한글 검증 전 파일을 닫고 다시 생성하면 된다.
- `style_guide.hwpx`를 다시 점검한 결과 실제 파일에는 `masterpage0.xml`, `masterpage1.xml`, `masterPage` ref가 없고 header style set도 기존 base보다 훨씬 작다는 점을 확인했다.
- 이 모순을 테스트로 먼저 고정했다. `test_exporter.py`를 style guide exact parity 기준으로 바꿔 `secPr`, `header ID set`, `masterpage`, `content manifest`, `section/masterpage style ref` 계약이 깨지면 바로 실패하도록 정리했다.
- canonical bundle 자산을 재구성했다. `style_guide.hwpx`에 `BinData/image1.bmp`, `Contents/masterpage0.xml`, `Contents/masterpage1.xml`를 추가하고 `content.hpf`, `section0.xml`의 manifest/masterPage ref를 보강한 뒤 vendored base에도 동일 내용을 동기화했다.
- canonical masterpage는 총 페이지 정적 숫자를 제거한 현재 페이지 전용 footer로 고정했고, paraPr/charPr/style ref를 모두 style guide header 안의 ID만 사용하도록 재매핑했다.
- `exporter.py`에서는 footer 후처리를 제거하고 `HWPX_TEMPLATE_RUNTIME_MISSING`, `HWPX_TEMPLATE_MANIFEST_MISSING`, `HWPX_TEMPLATE_MASTERPAGE_MISSING`, `HWPX_TEMPLATE_STYLE_REF_MISMATCH`, `HWPX_TEMPLATE_CANONICAL_CORRUPTED` 오류 코드를 구조화해 서버 로그에서 원인을 구분할 수 있게 했다.
- `hwpx_reference_renderer.py`는 해설 문단 판별의 `paraPrIDRef` 하드코딩을 제거해 style guide anchor와 호환되도록 바꿨고, `section0.xml` 저장 시 pretty print를 끄도록 조정해 canonical `secPr` 공백까지 보존하도록 했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_exporter.py -q` 기준 `19 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests -q` 기준 `137 passed`.
- canonical source를 exporter 코드 경로에서 실제로 고정했다. 이제 `exporter.py`는 vendored base를 복사하지 않고 `/D:/03_PROJECT/05_mathOCR/templates/style_guide.hwpx`를 작업 디렉터리로 직접 풀어 쓴다.
- `exporter.py`에 canonical bundle 추출 계층을 추가했다. `style_guide.hwpx` 누락 시 `HWPX_TEMPLATE_CANONICAL_MISSING`, archive 손상 시 `HWPX_TEMPLATE_CANONICAL_CORRUPTED`, manifest/masterpage/style drift 시 기존 세분화 코드로 서버 로그가 남는다.
- exporter 내부 계약 검증을 강화했다. generated `header.xml`의 style ID set, `section0.xml`의 `secPr`, `masterpage0/1.xml`, `content.hpf` manifest를 canonical 기준으로 다시 확인하고 drift면 즉시 실패시킨다.
- footer 후처리는 실제 정적 숫자가 남아 있을 때만 파일을 다시 쓰도록 바꿨다. canonical masterpage가 이미 정상인 경우 재직렬화를 피해서 bundle parity를 유지한다.
- `test_exporter.py`에 vendor base 훼손 회귀 테스트를 추가했다. 임시 runtime의 `templates/base/Contents/section0.xml`, `masterpage0.xml`를 깨뜨려도 export 결과가 `style_guide.hwpx` canonical을 유지하는지 검증한다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_exporter.py -q` 기준 `20 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main\\tests\\test_pipeline_storage.py -k export -q` 기준 `2 passed`.
- canonical exporter 경로로 샘플 HWPX를 새로 생성했다. 출력 파일은 `/D:/03_PROJECT/05_mathOCR/templates/generated-canonical-sample.hwpx` 이다.
- 샘플 생성은 reference-like fixture와 간단한 기하 도형 PNG를 사용했다. 내부 title은 `생성결과`로 유지되고 `Contents/masterpage0.xml`, `Contents/masterpage1.xml` 존재를 확인했다.
- 생성 확인: 파일 크기 `101464 bytes`, `TITLE_OK=True`, `HAS_MASTERPAGE0=True`, `HAS_MASTERPAGE1=True`.
- 공개 홈 랜딩을 serif 중심 초안에서 Apple식 sans-first 방향으로 다시 정렬했다. 사용자 피드백에 따라 `PublicHomePage`의 hero, 섹션 타이틀, 오브제 타이포를 산세리프로 전환했다.
- `fonts.css`는 `Noto Sans KR`만 로드하도록 단순화했고, `theme.css`에는 `-apple-system` 중심의 landing heading/UI stack과 sans용 tracking 토큰을 추가했다.
- `PublicHomePage.test.tsx`에 메인 카피와 섹션 타이틀이 `landing-heading` 산세리프 클래스를 사용한다는 회귀 테스트를 추가했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` 기준 `4 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공. Vite chunk size warning은 기존 번들 크기 경고로 유지됐다.
- 수동 확인: 로컬 dev 서버에서 공개 홈을 데스크톱 `1440px`와 모바일 `390px` 폭으로 확인했고, 헤드라인 줄바꿈과 CTA 노출이 sans 방향에서 안정적으로 보였다.
- hwpforge 0.5.0 조사 보고서를 추가했다: 02_main/docs/hwpforge_analysis_report_ko.md. 결론은 전면 교체보다 inspect/validate/to-md/to-json 중심의 Rust sidecar 도입이 현실적이며, 현재 Python canonical-template exporter는 유지하는 방향이 적합하다는 것이다.
- `templates/generated-canonical-sample.hwpx` 기준으로 HwpForge preserving patch 1문항 PoC를 실행했다. 작업 산출물은 `D:\03_PROJECT\05_mathOCR\.tmp\hwpforge-poc\one-question` 아래에만 두었고, `@hwpforge/mcp@0.5.0` MCP 경로로 `inspect -> to_json(section 0) -> patch -> inspect -> to_json(section 0)`를 자동화했다.
- Windows에서는 `.cmd` 직접 spawn이 막혀 `npx` 호출 대신 로컬 npm 설치 후 `node node_modules/@hwpforge/mcp/bin/hwpforge-mcp.js`로 MCP 서버를 띄우는 우회가 필요했다. HwpForge 서버는 `Content-Length` 프레이밍이 아니라 줄 단위 JSON 스트림을 기대한다는 점도 확인했다.
- PoC 검증 결과는 PASS였다. `Contents/section0.xml`만 변경됐고 `Contents/header.xml`, `Contents/masterpage0.xml`, `Contents/masterpage1.xml`, `Contents/content.hpf`, `settings.xml`, `version.xml`은 byte-for-byte 동일했다. `binaryItemIDRef=image1`, equation count 9, `paraPrIDRef` 13, `charPrIDRef` 19, `styleIDRef` 13도 유지됐고 첫 문항 번호 scaffold `1.` 역시 보존됐다.
- 추가 실험으로 `text-variant-geo` 샘플을 생성했다. HwpForge preserving patch로 문제 본문과 해설 문구를 새 기하 문항으로 바꿨고, `verification-report.json` 기준 다시 PASS였다. 최종 검토 파일은 `templates/hwpforge-text-variant-geo.hwpx`다.
- 같은 조건에서 equation script까지 바꾸는 `equation-variant` 실험도 수행했지만, HwpForge는 `preserving patch currently supports text-only section edits; structural change detected` 오류로 거부했다. 현재 버전에서는 수식 변경이 text-only patch 범위를 넘어선다는 점을 확인했다.
- 원본 샘플과 HwpForge text variant의 이미지 크기를 비교한 결과 `width=25347`, `height=11746`으로 완전히 동일했고, 차이는 `0 HWP unit`, `0.0%`였다.
- 사용자가 즉시 열어볼 수 있도록 추가 검토 파일을 `templates/` 아래에 복사했다: `hwpforge-poc-one-question.hwpx`, `hwpforge-text-variant-geo.hwpx`.
- HwpForge 한계를 보완하기 위해 `section0.xml`만 직접 교체하는 template-preserved equation variant도 별도로 만들었다. 결과 파일은 `templates/template-preserved-equation-variant.hwpx`이며, 문제 문구와 equation script가 모두 바뀐 상태다.
- 별도 검증으로 HwpForge `from_json` 생성 경로를 사용해 equation script 생성 여부를 확인했다. 작업 폴더는 `D:\03_PROJECT\05_mathOCR\.tmp\hwpforge-poc\from-json-equation`이고, full-document JSON을 편집해 `hwpforge_from_json`으로 새 HWPX를 만들었다.
- 생성 결과 [hwpforge-generated-equation-example.hwpx](/D:/03_PROJECT/05_mathOCR/templates/hwpforge-generated-equation-example.hwpx)에서 `2`, `5 over 3`, `11 over 4`, `8 over 3`, `7 over 2`, `ANGLE QPR= ANGLE SRT`, `ANGLE PQR= ANGLE STR`, `PQR`, `SRT` script가 실제로 생성되었고, `hwpforge_to_json` 재export 결과도 동일했다.
- 즉 현재 결론은 `HwpForge = equation 생성 가능`, `HwpForge preserving patch = equation 변경 불가`로 구분된다. 사용 경로에 따라 capability가 다르다.
- 하이브리드 전환 1단계로 Markdown 병행 계약을 추가했다. 백엔드 `ExtractorContext`와 API 응답에 `problem_markdown`, `explanation_markdown`, `markdown_version`를 넣고 기존 `ocr_text`, `explanation`, `mathml`은 유지했다.
- `02_main/app/pipeline/markdown_contract.py`를 추가해 기존 `<math>...</math>` 기반 산출물을 제한 Markdown bridge 형식으로 변환하도록 했다. 현재 버전 문자열은 `mathocr_markdown_bridge_v1`이다.
- `run_pipeline`는 OCR/해설 완료 직후 Markdown bridge 값을 함께 저장하고, export 가능 판정은 Markdown 필드를 우선 사용하되 구필드로 fallback 하도록 바꿨다.
- 저장소/과금/API도 병행 필드를 이해하도록 갱신했다. `repository.py`, `main.py`, `billing.py`에서 새 필드를 select/upsert/response/output 판정에 반영했다.
- 프런트는 `jobApi.ts`, `jobStore.ts`, `jobMappers.ts`, `JobDetailPage.tsx`, `ResultsViewer.tsx`를 갱신해 Markdown 필드를 상태에 보관하고 뷰어에서 우선 렌더링하도록 바꿨다.
- 미리보기 파서 `mathMarkupPreview.ts`는 `<math>...</math>`, `$...$`, `$$...$$`를 모두 formula segment로 읽도록 확장했다. malformed delimiter는 delimiter 제거 후 일반 텍스트로 폴백한다.
- DB 마이그레이션 파일 `02_main/schemas/2026-03-23_markdown_output_fields.sql`를 추가했고, `supabase_saas_init.sql`과 과금 backfill SQL에도 새 필드를 반영했다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main/tests/test_pipeline_storage.py 02_main/tests/test_job_response_fields.py -q` 기준 `22 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR && py -3 -m pytest 02_main/tests/test_billing.py -q` 기준 `42 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts src/app/lib/mathMarkupPreview.test.ts src/app/api/jobApi.test.ts src/app/store/jobStore.test.tsx` 기준 `24 passed`.
- 이번 단계는 출력 안정성 우선 원칙을 지켰다. 기존 canonical exporter와 reference renderer는 유지했고, HwpForge helper 기반 section writer 교체는 다음 단계로 넘겼다.
- 공개 홈 랜딩을 `04_new_design` 기준의 다크 풀스크린 구조로 개편했다. `PublicHomePage.tsx`에서 히어로, 중앙 하이라이트, 3카드, 하단 CTA, 푸터 흐름을 새 시안 기준으로 다시 구성했다.
- CTA 라벨은 서비스 흐름에 맞춰 `사용해 보기`(`/new`), `가격 보기`(`/pricing`), `로그인`(`/login`)으로 고정했고, 공개 홈의 `useAuth` 의존은 제거했다.
- 카드 1/2용 로컬 자산을 `04_design_renewal/src/assets/home/home-source-problem.png`, `04_design_renewal/src/assets/home/home-ocr-result.png`로 추가했다. 카드 3과 중앙 하이라이트 이미지는 외부 자산을 유지하되 `ImageWithFallback`로 감싸 로드 실패 시 placeholder로 대체되게 했다.
- `theme.css`에 `.public-home-page` 범위의 다크 랜딩 토큰과 `hero-title`, `hero-word`, `reveal`, `cosmos-card`, `glow-bg`, `glass-nav` 유틸을 추가했다. 다른 화면 토큰과 충돌하지 않도록 홈 전용 스코프로 제한했다.
- `PublicHomePage.test.tsx`를 새 구조에 맞춰 갱신했다. 히어로 카피, CTA 라벨과 navigate 목적지, 카드 이미지 src, 외부 이미지 fallback placeholder를 검증하도록 바꿨다.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` 기준 `4 passed`.
- 검증 결과: `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공. 프런트 정적 자산 번들은 정상 생성됐고, 기존 Vite chunk size warning만 유지됐다.
- 이번 변경은 프런트 정적 자산 범위로 제한됐다. 백엔드 API, 환경변수, 라우트 계약 변경은 없다.
## 2026-03-23 14:25 KST

- HwpForge exporter 통합을 TDD로 시작했다.
- [test_exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_exporter.py)에 `auto helper 성공`, `auto fallback`, `hwpforge 강제 실패` 3개 케이스를 추가했다.
- 현재 `py -3 -m pytest 02_main/tests/test_exporter.py -q` 결과는 3 failed / 21 passed다.
- 실패 원인은 exporter에 `roundtrip_section_via_hwpforge` 통합 지점과 엔진 분기(`legacy/auto/hwpforge`)가 아직 없기 때문이다.
- 다음 구현은 HwpForge roundtrip helper 모듈 추가, baseline HWPX roundtrip 후 `section0.xml`만 canonical bundle에 재주입하는 경로다.
## 2026-03-23 15:05 KST

- HwpForge standalone helper MVP를 추가했다. Python 래퍼는 [hwpforge_helper.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpforge_helper.py), 실제 Node helper CLI는 [hwpforge_doc_helper.js](/D:/03_PROJECT/05_mathOCR/02_main/scripts/hwpforge_doc_helper.js)다.
- helper 계약은 `sample_hwpx_path + mcp_script_path + output_hwpx_path + stem + choices(5개) + explanation_paragraphs` 입력을 받아 `to_json -> full-document JSON 수정 -> from_json -> inspect -> validate` 순서로 새 HWPX를 만든다.
- 현재 helper는 exporter에 아직 연결되지 않았고, standalone smoke/통합 준비 단계다. 우선순위는 사용자 출력 안정성 유지이므로 legacy exporter를 건드리지 않은 채 경계와 회귀 테스트부터 고정했다.
- sample baseline은 `templates/generated-canonical-sample.hwpx`를 사용한다. helper는 `HWPFORGE_MCP_PATH` 환경변수를 우선 보고, 없으면 `.tmp/hwpforge-poc/from-json-equation`, `.tmp/hwpforge-poc/one-question`, `.tmp/hwpforge-poc/text-variant-geo` 아래의 로컬 `@hwpforge/mcp` 경로를 후보로 찾는다.
- 단위 테스트 [test_hwpforge_helper.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_hwpforge_helper.py)를 추가했다. 검증 범위는 요청 JSON 직렬화, 성공 응답 파싱, 구조화 실패 응답 매핑, MCP 런타임 누락 오류다.
- 검증 결과: `py -3 -m pytest 02_main/tests/test_hwpforge_helper.py -q` -> `3 passed`
- 회귀 확인: `py -3 -m pytest 02_main/tests/test_exporter.py 02_main/tests/test_hwpforge_helper.py -q` -> `27 passed`
- 실제 smoke도 성공했다. `HWPFORGE_MCP_PATH=D:\03_PROJECT\05_mathOCR\.tmp\hwpforge-poc\from-json-equation\node_modules\@hwpforge\mcp\bin\hwpforge-mcp.js` 기준으로 helper를 호출해 `D:\03_PROJECT\05_mathOCR\.tmp\hwpforge-helper-smoke\generated.hwpx`를 생성했고, helper 내부 `hwpforge_validate` 통과 후 summary는 `1 sections, 10 paragraphs, 1 tables, 1 images, 0 charts`였다.
- 이 상태에서 다음 핵심 작업은 exporter 통합이다. 방향은 `legacy base 유지 -> helper roundtrip -> helper가 만든 section0.xml만 canonical bundle에 삽입 -> 실패 시 legacy fallback`이다.
- 배포 영향은 아직 없다. 다만 exporter 본경로에 helper를 연결하는 시점부터 Docker/Cloud Run 이미지에 Node 런타임과 HwpForge MCP 번들이 필요하다.
## 2026-03-23 15:12 KST

- HwpForge roundtrip helper를 exporter 본경로에 연결했다.
- 새 파일 [hwpforge_roundtrip.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpforge_roundtrip.py)에서 MCP stdio 세션으로 `hwpforge_to_json`, `hwpforge_from_json`, `hwpforge_inspect`, `hwpforge_validate`를 호출한다.
- exporter는 baseline canonical bundle을 먼저 만든 뒤 HwpForge roundtrip으로 생성한 `section0.xml`만 다시 주입한다.
- helper 또는 roundtrip 후 canonical contract 검증이 실패하면 `auto` 모드에서는 즉시 legacy section으로 복구하고 export를 계속한다.
- 환경변수 [config.py](/D:/03_PROJECT/05_mathOCR/02_main/app/config.py)에 `HWPX_EXPORT_ENGINE`, `HWPFORGE_MCP_PATH`를 추가했다. 기본 엔진은 `legacy`다.
- 문서 [README.md](/D:/03_PROJECT/05_mathOCR/02_main/README.md), [.env.example](/D:/03_PROJECT/05_mathOCR/02_main/.env.example)에 새 엔진 설정과 배포 주의사항을 기록했다.
- 회귀 검증:
  - `py -3 -m pytest 02_main/tests/test_exporter.py 02_main/tests/test_pipeline_storage.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_billing.py -q` -> `91 passed`
  - `HWPX_EXPORT_ENGINE=hwpforge` 실제 smoke export 성공. 최종 산출물에 `Contents/section0.xml`, `Contents/header.xml`, `BinData/*`가 모두 포함됐다.
- 현재 구조는 안정성 우선용 bridge다. 다음 단계는 baseline HWPX roundtrip을 없애고 direct export IR -> HwpForge writer로 교체하는 것이다.
## 2026-03-23 14:10 KST

- 공개 홈에서 상단 헤더를 제거했다. 이에 따라 `Math OCR`, `Photo to HWPX`, `로그인` 버튼이 첫 화면 상단에서 더 이상 노출되지 않는다.
- 히어로 CTA 라벨을 `사용해보기`로 통일했고, 화살표 아이콘을 제거했다. 기존 `/new`, `/pricing` 이동 동작은 유지했다.
- 중앙 하이라이트 제목은 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)에서 줄바꿈이 강제되도록 수정해 `수학문제 직접 타이핑하느라` 다음 줄에 `힘들지 않았나요?`가 나오게 했다.
- 랜딩 카드에서 `무료로 이용하세요` 섹션을 삭제해 2카드 구조로 단순화했다.
- 중앙 하이라이트 이미지와 카드 이미지의 `object-fit`을 `contain` 기준으로 바꾸고 확대 효과를 제거해 이미지 잘림을 줄였다.
- 푸터 설명 문구 `사진에서 구조를 읽고, 최종 결과를 HWPX까지 연결하는 수학 OCR 워크플로우.`를 제거했다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `4 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공. 기존 chunk size warning만 유지됐다.
## 2026-03-23 14:15 KST

- 웹 배포 경로에서 HwpForge가 실제로 동작하도록 컨테이너 런타임 번들링을 마쳤다.
- [Dockerfile](/D:/03_PROJECT/05_mathOCR/Dockerfile)와 [02_main/Dockerfile](/D:/03_PROJECT/05_mathOCR/02_main/Dockerfile)에 `node:20-bookworm-slim` builder stage를 추가하고 `@hwpforge/mcp@0.5.0`를 이미지 안 `vendor/hwpforge-mcp`로 복사하도록 맞췄다.
- 두 컨테이너 경로 모두 `HWPX_EXPORT_ENGINE=auto`를 기본값으로 사용하게 맞췄다. HwpForge가 실패해도 기존 legacy exporter fallback이 유지된다.
- [hwpforge_roundtrip.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpforge_roundtrip.py)의 vendored runtime 탐색 테스트 [test_hwpforge_roundtrip.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_hwpforge_roundtrip.py)를 기준으로 컨테이너 번들 경로가 계속 보장되게 했다.
- 프런트 [jobStore.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/store/jobStore.ts)의 export 흐름도 보정했다. 이제 실제 다운로드 성공 후에만 `status=exported`로 바뀌고, 다운로드 실패 시 이전 상태를 유지한 채 `lastError`를 기록한다.
- 프런트 회귀 테스트 [jobStore.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/store/jobStore.test.tsx)에 `다운로드 전 상태 유지`, `다운로드 실패 rollback` 케이스를 추가했다.
- 문서 [README.md](/D:/03_PROJECT/05_mathOCR/02_main/README.md), [.env.example](/D:/03_PROJECT/05_mathOCR/02_main/.env.example), [cloud_run_supabase_free_runbook_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/cloud_run_supabase_free_runbook_ko.md)를 현재 배포 계약에 맞게 갱신했다.
- 실제 검증 결과:
  - `docker build -t mathocr-api-hwpforge-web .` 성공
  - `docker run --rm mathocr-api-hwpforge-web python -c "from app.pipeline.hwpforge_roundtrip import resolve_hwpforge_runtime; runtime = resolve_hwpforge_runtime(); print(runtime.executable_path); print(runtime.command)"` 성공
  - `docker run --rm mathocr-api-hwpforge-web python -c "from pathlib import Path; from app.pipeline.hwpforge_roundtrip import roundtrip_section_via_hwpforge; out = roundtrip_section_via_hwpforge(Path('/app/templates/style_guide.hwpx'), Path('/tmp/hwpforge-check')); print(out.exists()); print(out)"` 성공
  - `docker build -f 02_main/Dockerfile -t mathocr-api-local-hwpforge 02_main` 성공
  - `docker run --rm mathocr-api-local-hwpforge python -c "from pathlib import Path; from app.pipeline.hwpforge_roundtrip import roundtrip_section_via_hwpforge; out = roundtrip_section_via_hwpforge(Path('/app/templates/style_guide.hwpx'), Path('/tmp/hwpforge-check')); print(out.exists()); print(out)"` 성공
  - `py -3 -m pytest 02_main/tests/test_hwpforge_roundtrip.py 02_main/tests/test_exporter.py 02_main/tests/test_pipeline_storage.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_billing.py -q` -> `92 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/store/jobStore.test.tsx src/app/api/jobApi.test.ts src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts` -> `21 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
- 현재 남은 핵심 과제는 bridge 구조 제거다. 다음 구현은 `legacy baseline -> roundtrip section 교체` 대신 Markdown/export IR에서 direct HwpForge section writer를 만드는 것이다.
## 2026-03-23 14:32 KST

- HwpForge bridge 제거를 구현했다. main path는 이제 `direct export IR -> HwpForge writer -> section0.xml -> canonical bundle 삽입`이다.
- 기존 `legacy baseline -> HwpForge roundtrip section 교체` 경로는 exporter fallback 전용으로만 남겼다. direct writer 실패 시 `auto`에서는 roundtrip/legacy fallback으로 정상 파일 출력을 유지하고, `hwpforge`에서는 HwpForge roundtrip fallback까지 시도한다.
- 직접 writer는 [hwpforge_roundtrip.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpforge_roundtrip.py)에 `build_section_via_hwpforge()`로 추가했다. 이 함수는 [hwpforge_json_builder.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpforge_json_builder.py)의 export IR + template JSON을 사용해 `hwpforge_from_json`으로 새 HWPX를 만들고 `section0.xml`을 추출한다.
- exporter는 [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py)에서 direct bundle 준비 함수 `_prepare_direct_hwpforge_bundle()`을 먼저 타고, 실패했을 때만 legacy bundle + roundtrip fallback으로 내려가도록 재구성했다.
- direct writer template 자산 [hwpforge_generated_canonical_sample.json](/D:/03_PROJECT/05_mathOCR/02_main/templates/hwpx/hwpforge_generated_canonical_sample.json)을 `02_main/templates/hwpx/`에 추가했다.
- 루트 배포 이미지가 새 template 자산을 포함하도록 [Dockerfile](/D:/03_PROJECT/05_mathOCR/Dockerfile)과 [.dockerignore](/D:/03_PROJECT/05_mathOCR/.dockerignore)를 갱신했다.
- direct writer 제어 흐름 회귀 테스트를 [test_exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_exporter.py)에 추가했다.
  - direct writer 성공 시 roundtrip 미호출
  - direct writer 실패 시 roundtrip fallback
  - direct/roundtrip 모두 실패 시 legacy fallback
- direct writer 자체 단위 테스트를 [test_hwpforge_roundtrip.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_hwpforge_roundtrip.py)에 추가했다.
  - template JSON 자산 탐색
  - generated hwpx에서 section0.xml 추출
- 검증 결과:
  - `py -3 -m pytest 02_main/tests/test_hwpforge_roundtrip.py 02_main/tests/test_hwpforge_json_builder.py 02_main/tests/test_exporter.py 02_main/tests/test_pipeline_storage.py 02_main/tests/test_job_response_fields.py 02_main/tests/test_billing.py -q` -> `98 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/store/jobStore.test.tsx src/app/api/jobApi.test.ts src/app/components/ResultsViewer.test.tsx src/app/store/jobMappers.test.ts` -> `21 passed`
  - `docker build -t mathocr-api-hwpforge-web .` 성공
  - `docker build -f 02_main/Dockerfile -t mathocr-api-local-hwpforge 02_main` 성공
  - 루트 이미지에서 `build_section_via_hwpforge()` smoke 성공
  - 루트 이미지에서 `export_hwpx()` end-to-end smoke 성공
  - `02_main` 이미지에서도 `export_hwpx()` end-to-end smoke 성공
- 남은 핵심 작업은 품질 확대다. 다음 단계는 direct writer가 `problem_markdown`, `explanation_markdown`을 우선 사용하도록 넓히고, multi-region/빈 해설/보기 없는 문항 회귀를 늘리는 것이다.
## 2026-03-23 14:19 KST

- 공개 홈 중앙 하이라이트 이미지만 기존처럼 꽉 차게 보이도록 되돌렸다.
- [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)에서 중앙 이미지의 `object-fit`을 `contain`에서 `cover`로 변경하고, 내부 패딩을 제거해 카드 이미지는 그대로 둔 채 중앙 섹션만 영향받게 했다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx) 회귀 테스트도 `디지털 작업 공간` 이미지가 `object-cover`를 사용하도록 갱신했다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `4 passed`

## 2026-03-23 14:46 KST

- 공개 홈 히어로에 저존재감 타임랩스 배경을 추가했다. 구현 파일은 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx), [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css), [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx)다.
- 원본 [star-timelapse.mp4](/D:/03_PROJECT/05_mathOCR/04_new_design/star-timelapse.mp4)에서 실서비스용 파생 자산 3종을 생성했다.
  - [hero-timelapse.webm](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/assets/home/hero-timelapse.webm) `180745 bytes`
  - [hero-timelapse.mp4](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/assets/home/hero-timelapse.mp4) `206201 bytes`
  - [hero-timelapse-poster.jpg](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/assets/home/hero-timelapse-poster.jpg) `47451 bytes`
- 비디오는 `min-width: 768px`이며 `prefers-reduced-motion: no-preference`일 때만 클라이언트에서 마운트되도록 분리했다. SSR/초기 렌더에서는 poster + 기존 블랙 그라데이션만 보이게 유지했다.
- 예상 가능한 폴백 사유를 `viewport-blocked`, `reduced-motion`, `media-query-unsupported`, `video-unavailable`로 정의했고, 모든 케이스에서 사용자 메시지 없이 정적 poster 상태를 유지하도록 맞췄다.
- CSS는 비디오 존재감을 낮추기 위해 `grayscale`, `brightness`, `contrast`, dark overlay, noise, 하단 마스크를 조합했다. 모바일에서는 poster opacity만 더 낮춰 첫 화면 블랙 인상을 유지했다.
- 회귀 테스트를 먼저 추가해 실패를 확인한 뒤 구현했다. 새 테스트는 데스크톱 조건부 비디오 렌더, `muted/loop/playsInline/aria-hidden/poster/preload` 속성, 모바일/감속 모드 미노출을 검증한다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `npx vite preview --host 127.0.0.1 --port 5173` 기준 데스크톱 `1440px`에서 비디오 재생/낮은 opacity 확인, 모바일 `390px`에서 비디오 미마운트 확인
- 이번 변경은 프런트 정적 자산 범위다. 백엔드 API, Cloud Run, 타입 계약 변경은 없다.

## 2026-03-23 15:05 KST

- 사용자 피드백 기준으로 히어로 타임랩스가 체감상 거의 보이지 않는 문제를 재조사했다.
- root cause는 비디오 미마운트가 아니라 과도한 억제 조합이었다. 실제로 `video.currentTime`은 증가했고 `paused=false`, `readyState=4`였지만 `opacity=0.13`, `brightness=0.32`, 강한 dark overlay 때문에 검은 배경에 흡수되고 있었다.
- [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css)에서 히어로 미디어 톤을 재조정했다.
  - video: `opacity 0.36`, `mix-blend-mode: screen`, `brightness 0.78`, `contrast 1.18`
  - poster: `opacity 0.14`, `brightness 0.42`
  - overlay: 상단/중앙 dark gradient를 소폭 완화
  - mobile poster opacity도 `0.1`로 더 낮춰 모바일 정적 배경 인상은 유지
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `http://127.0.0.1:5173/` Playwright 확인 기준 데스크톱 히어로에서 별 타임랩스 흔적이 이전보다 명확히 드러나고, 헤드라인 대비는 유지됨

## 2026-03-23 15:44 KST

- 사용자 스크린샷 기준으로 “아예 안 보인다”는 피드백이 계속되어 root cause를 한 단계 더 파고들었다.
- 결론은 opacity 하나가 아니라 레이어 조합 문제였다.
  - 소스 비디오는 대부분 프레임이 매우 어둡다. 샘플 분석 기준 평균 밝기 약 `6/255` 구간이 길고, 밝은 픽셀 비율도 낮았다.
  - 히어로 위에 정적 점무늬가 2겹 있었다. [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css)의 `.public-home-page::before`와 `.public-home-hero-noise`가 실제 별보다 더 먼저 눈에 들어와 타임랩스를 배경 노이즈처럼 보이게 만들었다.
  - 하단 마스크와 중앙 대형 타이포 때문에 산 능선/은하대처럼 “영상이 있다”는 신호가 더 약해졌다.
- 수정 방향:
  - [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)에서 히어로 전용 정적 noise 레이어를 제거했다.
  - [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css)에서 전역 점무늬를 도트 패턴 대신 큰 haze gradient로 바꿨다.
  - poster/video의 구도를 `40% center`로 옮겨 은하대가 더 보이게 했고, 하단 마스크를 완화했다.
  - poster/video 밝기와 대비를 올리고 overlay는 소폭 약화했다.
- 회귀 테스트를 먼저 고정했다. [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx)에 히어로가 더 이상 `.public-home-hero-noise`를 렌더하지 않는다는 검증을 추가했고, 실패를 확인한 뒤 구현했다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `http://127.0.0.1:5173/` Playwright 확인 기준 히어로 상단에서 별/은하대와 산 능선이 이전보다 명확히 읽히고, CTA 가독성은 유지됨

## 2026-03-23 15:51 KST

- 사용자가 “이제 보이긴 하지만 엄청 희미하다”고 피드백해, 첫 인상 자체를 더 읽히게 하는 보강을 추가했다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx)에 회귀 테스트를 먼저 추가했다. `loadedmetadata` 이후 히어로 비디오가 `4.8초` 구간에서 시작하고 `playbackRate=1.35`를 갖는지 검증하도록 고정했다.
- 실패 확인 후 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)에 `primeHeroBackgroundVideo()`를 추가하고, `onLoadedMetadata`에서 시작 오프셋과 재생 속도를 세팅하도록 구현했다.
- 의도는 첫 1초 안에 더 밝은 별/산 능선 프레임을 보여주고, 느린 별 이동이 “정지 화면처럼 보이는” 문제를 줄이는 것이다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `http://127.0.0.1:5173/` Playwright 확인 기준 `playbackRate=1.35`, source는 `hero-timelapse.webm`, 1초 후 `currentTime`이 `1.69`로 확인되어 밝은 구간 시작 후 빠르게 loop 되는 동작을 확인했다.

## 2026-03-23 15:56 KST

- 사용자 피드백 `너무 희미해`에 맞춰 히어로 가시성 토큰을 한 단계 더 상향했다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx)에 히어로 미디어 컨테이너가 `--hero-media-position=36% center`, `--hero-poster-opacity=0.34`, `--hero-video-opacity=0.72` 토큰을 가진다는 회귀 테스트를 먼저 추가했고, 실패를 확인한 뒤 구현했다.
- [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)에 `heroMediaVisualTokens`를 추가해 히어로 미디어 톤 값을 컴포넌트에서 명시적으로 관리하도록 바꿨다.
- [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css)는 해당 CSS 변수를 사용하도록 바꿨고, 실제 값도 다음처럼 상향했다.
  - poster opacity `0.34`
  - video opacity `0.72`
  - position `36% center`
  - video filter `grayscale(1) brightness(1.2) contrast(1.32)`
  - overlay dark gradient 완화
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `http://127.0.0.1:5173/` Playwright 확인 기준 inline token과 runtime style이 모두 반영됐고, 히어로에서 산 능선과 별 질감이 이전보다 더 직접적으로 읽히는 상태를 확인했다.

## 2026-03-23 16:29 KST

- 사용자가 여전히 `너무 연하다`고 피드백해, 히어로 배경을 한 단계 더 공격적으로 올렸다. 이번에는 추정이 아니라 `localhost:5173` 실브라우저 렌더를 기준으로 값 조정을 마쳤다.
- 원인 중 하나로 확인된 점은 로컬 미리보기 서버가 `127.0.0.1`이 아니라 `::1/localhost`로만 바인딩된 상태였다는 것이다. 따라서 브라우저/Playwright가 서로 다른 주소를 보고 있으면 실제 인상이 다르게 느껴질 수 있었다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx)에 회귀 테스트를 먼저 수정해 히어로 미디어 토큰이 `--hero-media-position=32% center`, `--hero-poster-opacity=0.46`, `--hero-video-opacity=0.9`를 기대하도록 바꿨고, 실패를 확인한 뒤 구현했다.
- [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)에서는 `heroMediaVisualTokens`를 다음 값으로 재상향했다.
  - position `32% center`
  - poster opacity `0.46`
  - poster filter `grayscale(1) brightness(1.16) contrast(1.22)`
  - video opacity `0.9`
  - video filter `grayscale(1) brightness(1.42) contrast(1.46)`
  - overlay `rgba(1, 3, 4, 0.48) / 0.16 / 0.66` 기반으로 완화
- [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css)도 같은 기본값으로 올렸고, 추가로 다음을 반영했다.
  - video에 `mix-blend-mode: screen`
  - poster/video 마스크 하단 완화
  - 히어로 타이포 text-shadow를 검정 기반으로 바꿔 배경이 밝아져도 CTA/헤드라인 가독성이 무너지지 않게 조정
  - 모바일 poster도 `opacity 0.28`, `brightness 0.94`, `contrast 1.14`로 소폭 상향
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `http://localhost:5173/` Playwright 확인 기준 runtime style이 `poster 0.46`, `video 0.9`, `mix-blend-mode: screen`으로 반영됐고, 히어로에서 산 능선과 별 움직임이 이전보다 훨씬 직접적으로 읽히는 상태를 확인했다.

## 2026-03-23 16:33 KST

- 사용자가 `동영상이 멈춰있다`고 피드백해 `localhost:5173`에서 실제 비디오 상태를 다시 계측했다.
- 확인 결과 비디오는 멈춘 것이 아니었다. Playwright 기준 `paused=false`, `readyState=4`, `playbackRate=1.35`였고 `currentTime`도 증가했다.
- 실제 root cause는 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 의 `loadedmetadata`에서 `4.8초` 밝은 구간으로 시작시키는 설정과 기본 `loop`의 조합이었다.
  - 첫 루프는 `4.8s -> 6.0s` 구간만 재생돼 밝게 보인다.
  - 그 다음부터는 브라우저 기본 `loop` 때문에 `0초`로 돌아가고, `0s -> 4.8s` 구간은 원본이 너무 어두워 사용자가 정지처럼 느끼게 된다.
- 회귀 테스트를 먼저 추가했다. [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx)에 `currentTime=5.8`에서 `timeUpdate`가 오면 다시 `4.8`로 되돌아가는 검증을 넣고 실패를 확인한 뒤 구현했다.
- [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)에 `heroVideoLoopResetSeconds=5.7`과 `recycleHeroBackgroundVideo()`를 추가하고, `onTimeUpdate`에서 `5.7s` 이후에는 다시 `4.8s`로 되돌리도록 바꿨다. 이제 밝은 구간 안에서만 반복된다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `http://localhost:5173/` Playwright 확인 기준 3초 후에도 `paused=false` 상태를 유지했고, `currentTime`이 `0초`대로 떨어지지 않고 `5초대`에 머물며 밝은 구간 루프가 유지되는 것을 확인했다.

## 2026-03-23 14:52 KST

- `/new` 작업 생성 화면에서 업로드 미리보기 카드를 제거하고, 파일 정보와 교체 액션을 [NewJobPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx)의 영역 지정 헤더로 이동했다.
- 편집 레이아웃은 `max-w-4xl` 고정 폭 대신 넓은 작업 영역을 사용하도록 확장했고, 데스크톱에서는 큰 영역 지정 캔버스 + 우측 고정 실행 패널 구조로 재배치했다.
- 같은 파일도 다시 선택할 수 있도록 숨김 파일 입력 초기화 로직을 추가했고, `다른 파일 선택` 버튼으로 현재 draft를 비우고 업로드 단계로 되돌아가게 했다.
- 회귀 테스트를 먼저 추가해 실패를 확인한 뒤 구현했다. 새 테스트는 업로드 후 `업로드 미리보기` 섹션이 사라지고, 영역 지정 화면에서 파일 교체 버튼이 노출되는 흐름을 검증한다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/NewJobPage.test.tsx src/app/components/RegionEditor.test.tsx` -> `8 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` 성공
  - `npm run dev -- --host 127.0.0.1 --port 4173` + 브라우저 스냅샷 기준 `/new?resumeDraft=1`에서 별도 미리보기 카드 없이 큰 편집 캔버스가 노출되는 것을 확인
- 이번 변경은 프런트 레이아웃 범위다. 백엔드 API, Cloud Run, 배포 환경 변수 변경은 없다.

## 2026-03-23 14:53 KST

- 파이프라인 실행 버튼에서 `[500] 배포 DB 스키마가 최신이 아닙니다.`가 뜨는 원인을 `2026-03-23_markdown_output_fields.sql` 미적용 배포 DB와 새 Markdown 출력 컬럼 직접 조회/저장 로직의 충돌로 확인했다.
- `02_main/app/schema_compat.py`를 추가해 `problem_markdown`, `explanation_markdown`, `markdown_version` 컬럼 부재를 감지하고 현재 프로세스에서 구스키마 fallback 여부를 기억하도록 정리했다.
- `02_main/app/pipeline/repository.py`는 `ocr_job_regions` 조회와 upsert에서 새 Markdown 컬럼이 없으면 구버전 컬럼 집합으로 자동 재시도하도록 수정했다. 따라서 `/jobs/{job_id}/run`, `/jobs/{job_id}`, `/jobs/{job_id}/regions` 모두 구스키마에서도 계속 동작한다.
- `02_main/app/billing.py`도 과금 사전 점검/후차감에서 같은 fallback을 사용하도록 바꿨다. 배포 DB migration이 늦어도 파이프라인 실행 전 크레딧 점검에서 더 이상 500으로 막히지 않는다.
- 회귀 테스트를 먼저 추가해 실패를 확인한 뒤 구현했다. 새 테스트는 저장소 read/save fallback과 과금 점검 fallback을 각각 검증한다.
- 검증 결과:
  - `py -3 -m pytest 02_main/tests/test_pipeline_storage.py -k "falls_back_when_markdown_columns_are_missing" -q` -> `2 passed`
  - `py -3 -m pytest 02_main/tests/test_billing.py -k "falls_back_when_markdown_columns_are_missing" -q` -> `1 passed`
  - `py -3 -m pytest 02_main/tests/test_pipeline_storage.py 02_main/tests/test_billing.py 02_main/tests/test_job_response_fields.py -q` -> `67 passed`
- 이번 변경은 배포 환경 변수 변경이 없고 DB migration을 강제하지 않는다. 다만 실제 오류 해소를 위해서는 백엔드 서비스 재배포가 필요하다.

## 2026-03-23 18:10 KST

- HWPX direct writer 수식 출력 깨짐의 실제 원인을 두 갈래로 정리했다. [hwpforge_json_builder.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpforge_json_builder.py)는 문제 본문 `stem`을 Text run 하나로만 넣어 `<math>`가 literal로 남았고, direct writer equation run은 템플릿 샘플 폭을 그대로 재사용해 짧은 수식도 긴 수식 폭을 물려받고 있었다.
- 공통 수식 레이아웃 계층 [hwpx_math_layout.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpx_math_layout.py)를 추가해 `<math>` 분해, HWP 수식 스크립트 정규화, script 길이 측정, 폭 샘플 보간을 한곳으로 모았다.
- [hwpx_reference_renderer.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpx_reference_renderer.py)는 새 공통 모듈을 import하도록 정리했고, legacy renderer도 같은 정규화/폭 계산 규칙을 쓰게 바꿨다.
- [hwpforge_json_builder.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpforge_json_builder.py)는 문제 본문과 해설 mixed 문단을 segment 순서 기반 run 재조립으로 통일했고, choice/problem/explanation 모든 equation run이 공통 폭 샘플 보간을 사용하도록 수정했다.
- [test_hwpforge_json_builder.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_hwpforge_json_builder.py)에 문제 본문 literal `<math>` 회귀와 짧은/긴 수식 폭 회귀 테스트를 먼저 추가해 실패를 확인한 뒤 구현했다.
- [test_exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_exporter.py)는 현재 direct writer 기본 경로에 맞게 hwpforge helper 성공 테스트를 갱신했다.
- [error_patterns.md](/D:/03_PROJECT/05_mathOCR/error_patterns.md)에 direct writer mixed run 분해와 equation width 재계산 규칙을 추가했다.
- 검증 결과:
  - `py -3 -m pytest 02_main/tests/test_hwpforge_json_builder.py -q` -> `5 passed`
  - `py -3 -m pytest 02_main/tests/test_hwpforge_json_builder.py 02_main/tests/test_exporter.py -q` -> `32 passed`
- 실제 `HWPX_EXPORT_ENGINE=hwpforge` 강제 E2E는 저장소 안에 HwpForge MCP 런타임이 없어 이 세션에서 실행하지 못했다. 백엔드 코드 변경만 있으므로 배포 환경 변수 변경은 없지만, 실제 반영에는 백엔드 재배포가 필요하다.

## 2026-03-23 16:49 KST

- 공개 홈 히어로 비디오 재생 계약을 사용자 요청대로 뒤집었다. [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 에서 `matchMedia` 기반 `viewport-blocked`, `reduced-motion`, `media-query-unsupported` 분기를 제거해 `prefers-reduced-motion` 및 뷰포트와 무관하게 비디오가 항상 렌더되도록 바꿨다.
- 같은 파일의 루프 구간도 밝은 후반부 `4.8s -> 5.7s` 에서 어두운 초반부 `0.3s -> 4.3s` 로 옮겼다. `loadedmetadata` 시점과 `timeupdate` 재설정 모두 같은 다크 구간 계약을 사용한다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx) 는 TDD로 먼저 수정했다. 모바일 환경, 감속 모드 환경, 다크 루프 시작/재루프 시간을 새 계약으로 고정했고, 기존 구현에서 실패를 확인한 뒤 통과시켰다.
- 이번 변경의 설계와 실행 계획은 [2026-03-23-home-hero-video-dark-loop-design.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-23-home-hero-video-dark-loop-design.md), [2026-03-23-home-hero-video-dark-loop-plan.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-23-home-hero-video-dark-loop-plan.md) 에 기록했다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `7 passed`
- 이번 변경은 프런트 범위라 백엔드 API, Cloud Run, 환경 변수 변경은 없다.

## 2026-03-23 17:36 KST

- 공개 홈 중앙 하이라이트 헤드라인이 `타이핑하느라`를 중간에서 끊어 먹는 문제를 수정했다.
- root cause는 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 의 `h2`가 첫 줄을 일반 텍스트 노드로 렌더해, 한국어 기본 줄바꿈 규칙이 단어 내부까지 허용되던 구조였다.
- 같은 파일에 `mainFeatureHeadingLines` 상수를 추가하고, 헤드라인을 두 개의 block span으로 명시했다. 첫 줄은 `md:whitespace-nowrap`, 전체 헤드라인은 `break-keep` 계약을 적용해 데스크톱에서는 요청한 두 줄 구성을 유지하고 한국어 단어 중간 줄바꿈을 막도록 정리했다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx) 에 회귀 테스트를 먼저 추가해, 중앙 하이라이트 헤드라인이 두 개의 span으로 분리되고 첫 줄 계약이 유지되는지 실패로 고정한 뒤 통과시켰다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `8 passed`
- 이번 변경도 프런트 범위라 백엔드 API, Cloud Run, 환경 변수 변경은 없다.

## 2026-03-23 17:39 KST

- 공개 홈 히어로 비디오가 너무 빨리 반복된다는 피드백에 맞춰 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 의 루프 계약을 다시 조정했다.
- 원인은 기존 설정이 `0.3s -> 4.3s` 구간을 `1.35x`로 돌려 실제 반복 주기가 약 `3초` 수준까지 짧아진 점이었다.
- 같은 파일에서 `heroVideoPlaybackRate`를 `0.36`으로 낮추고 `heroVideoLoopResetSeconds`를 `5.7`로 늘려, 시작점 `0.3s` 기준 실제 체감 루프가 약 `15초`가 되도록 맞췄다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx) 는 TDD로 먼저 수정했다. `loadedmetadata` 이후 `playbackRate=0.36`, `timeupdate` 시점 `5.8s`에서 `0.3s`로 되돌아가는 계약을 실패로 고정한 뒤 통과시켰다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `8 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` -> `built in 3.54s`
- 이번 변경도 프런트 범위라 백엔드 API, Cloud Run, 환경 변수 변경은 없다.

## 2026-03-23 17:55 KST

- 사용자가 지적한 `뚝뚝 끊김` 과 `밝아지는 구간 튐` 을 근본적으로 없애기 위해, 단순 `playbackRate` 감속 접근을 버리고 새 15초 루프 자산 재생성 방식으로 전환했다.
- 새 설계와 구현 계획은 [2026-03-23-home-hero-video-15s-loop-design.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-23-home-hero-video-15s-loop-design.md), [2026-03-23-home-hero-video-15s-loop-plan.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-23-home-hero-video-15s-loop-plan.md) 에 기록했다.
- [build_hero_timelapse_loop.py](/D:/03_PROJECT/05_mathOCR/04_design_renewal/scripts/build_hero_timelapse_loop.py) 를 추가해 원본 [star-timelapse.mp4](/D:/03_PROJECT/05_mathOCR/04_new_design/star-timelapse.mp4) 를 읽고, 밝기 컷오프 탐지, 광류 기반 프레임 보간, 루프 tail 블렌드, `mp4/webm/poster` 재출력을 한 번에 처리하도록 만들었다.
- 스크립트는 원본 기준 `cutoff_index=120`, `safety_margin_frames=10`, `usable_end_index=110` 을 선택해 밝아지는 후반 구간을 잘라냈고, 서비스 자산을 `25fps / 15초` 루프로 다시 생성했다.
- [test_build_hero_timelapse_loop.py](/D:/03_PROJECT/05_mathOCR/04_design_renewal/tests/test_build_hero_timelapse_loop.py) 를 먼저 추가해 밝기 컷오프 감지와 출력 위치 샘플링 로직을 실패로 고정한 뒤 통과시켰다.
- [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 는 수동 `playbackRate` 조절과 `timeupdate` 리셋을 제거하고, 새 자산을 브라우저 기본 `loop` 로만 재생하도록 단순화했다.
- [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx) 도 새 계약에 맞춰 `loadedmetadata` 이후 `currentTime=0`, `playbackRate=1`, `timeupdate` 에서 강제 리셋 없음으로 기대값을 바꿔 실패를 확인한 뒤 통과시켰다.
- 출력 비디오 밝기 검증 기준 `min=29.56`, `max=33.55`, `mean=30.51` 이었고, 0초/3.7초/7.5초/11.2초/15초 시점 모두 어두운 톤을 유지했다.
- 브라우저 수동 QA 기준 `duration=15`, `paused=false`, `readyState=4`, `loop=true`, `currentTime` 이 `2.82 -> 5.83` 으로 증가해 정상 재생을 확인했다. 콘솔 오류는 `favicon.ico` 404 하나뿐이었고 기능 영향은 없었다.
- 검증 결과:
  - `py -3 -m pytest 04_design_renewal/tests/test_build_hero_timelapse_loop.py -q` -> `2 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `8 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` -> `built in 3.73s`
- 이번 변경도 프런트 정적 자산 범위라 백엔드 API, Cloud Run, 환경 변수 변경은 없다. 프런트 재배포만 필요하다.

## 2026-03-23 18:18 KST

- 사용자 피드백대로 첫 번째 15초 자산은 품질 실패였다. root cause는 [build_hero_timelapse_loop.py](/D:/03_PROJECT/05_mathOCR/04_design_renewal/scripts/build_hero_timelapse_loop.py) 가 `0 -> 110` 구간을 `375프레임`으로 늘리면서 프레임 대부분을 광류 보간으로 합성한 점이었다.
- 실제 계산 기준 출력 `375프레임` 중 `352프레임`, 약 `93.9%` 가 합성 프레임이었고, 이는 별 궤적과 산 윤곽에 잔상을 만들고 재생 cadence도 부자연스럽게 만들었다.
- 원본 프레임 기반 루프로 아키텍처를 다시 바꿨다. 같은 스크립트는 이제 밝기 컷오프 이후 `usable_end_index=110` 안에서 시작/끝 차이가 가장 작은 자연 루프 구간을 찾고, 그 구간 인덱스를 반복해 15초 자산을 만든다.
- 실제 선택 구간은 `loop_start_index=1`, `loop_end_index=98`, `loop_duration_frames=97` 이었고, 이후 출력은 더 이상 광류 보간을 사용하지 않는다.
- [test_build_hero_timelapse_loop.py](/D:/03_PROJECT/05_mathOCR/04_design_renewal/tests/test_build_hero_timelapse_loop.py) 도 `build_output_positions` 검증 대신 원본 루프 인덱스 반복 함수 검증으로 바꿔 실패를 확인한 뒤 통과시켰다.
- 재생성된 자산은 여전히 `25fps / 15초` 를 유지하고, 샘플 sharpness 도 중간 구간 기준 이전 보간 버전보다 유의미하게 회복됐다.
- 검증 결과:
  - `py -3 -m pytest 04_design_renewal/tests/test_build_hero_timelapse_loop.py -q` -> `2 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `8 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` -> `built in 3.82s`
- 브라우저 확인 기준 새 비디오는 `duration=15`, `loop=true`, `playbackRate=1`, `paused=false` 상태를 유지했고 `hero-timelapse-CFyWIYFJ.webm` 가 실제 재생 소스로 잡혔다.

## 2026-03-23 19:03 KST

- 사용자 스크린샷 기준으로 히어로 배경에 정지된 별 레이어가 남아 있다는 증상을 다시 분리했다. 자산 자체의 광류 보간 문제와 별개로 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 가 별도 `public-home-hero-poster` div를 재생 중에도 계속 유지하는 것이 직접 원인이었다.
- 회귀 테스트를 먼저 강화해 [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx) 에서 `loadeddata` 이전에는 poster가 보이고, 이후에는 제거되어야 한다는 계약을 추가했고, 현재 구현이 실패하는 것을 확인했다.
- 이후 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 에 `isVideoReady` 상태를 추가해 `loadeddata` 이후에는 별도 poster div를 unmount 하고, 비디오 오류일 때만 fallback poster가 남도록 수정했다.
- 검증 결과:
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/components/PublicHomePage.test.tsx` -> `8 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run build` -> `built in 3.79s`
  - Playwright 런타임 계측 기준 `video.readyState=4`, `paused=false`, `currentTime=5.78` 상태에서 `.public-home-hero-poster` 노드가 DOM 에 존재하지 않음을 확인했다.
- 배포 영향:
  - 프론트엔드 재배포만 필요하고, 백엔드 환경 변수나 서버 설정 변경은 없다.

## 2026-03-25 10:32 KST

- OCR/HWPX 정합성 강화 계획을 실제 코드에 반영했다. 핵심은 [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py), [orchestrator.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/orchestrator.py), [repository.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/repository.py), [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py) 경로에 `ordered_segments`, `raw_transcript`, 객관식 정답 검증 메타데이터를 끝까지 흘려보내는 것이다.
- OCR은 `text_blocks/formulas` 단일 경로에만 의존하지 않고 `ordered_segments`를 우선 사용하도록 바꿨다. plain text는 재작성하지 않고 math segment만 정규화하며, `raw_transcript`에는 모델이 본 원문 순서를 그대로 남긴다.
- 해설 생성은 자유문자열 대신 구조화 JSON 응답을 기본 계약으로 바꿨다. `explanation_lines`, `final_answer_index`, `final_answer_value`, `confidence`, `reason_summary`를 받고, orchestrator에서 선택지와 결정적으로 대조한다.
- 객관식에서 정답 번호/값이 선택지와 충돌하거나 답을 확정할 수 없으면 `verification_status=warning`, `verification_warnings`를 저장하고, 해설 본문은 `해설 검증이 필요합니다. 정답과 풀이의 일치 여부를 자동 확인하지 못했습니다.` 로 안전 치환하도록 만들었다.
- direct HwpForge 경로의 최종 `section0.xml` 폭 재보정 로직과 회귀 테스트도 현재 워크스페이스에 반영된 상태다. [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py), [hwpx_math_layout.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpx_math_layout.py), [test_exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_exporter.py) 기준으로 canonical 샘플을 이용해 짧은 수식 폭을 다시 맞춘다.
- 프런트도 검증 경고를 표시하도록 연결되어 있다. [jobApi.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/api/jobApi.ts), [jobMappers.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/store/jobMappers.ts), [ResultsViewer.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ResultsViewer.tsx), [JobDetailPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx) 에서 warning 상태를 노출한다.
- DB 스키마도 같이 확장했다. [2026-03-25_ocr_verification_fields.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/2026-03-25_ocr_verification_fields.sql) 을 추가했고, [supabase_saas_init.sql](/D:/03_PROJECT/05_mathOCR/02_main/schemas/supabase_saas_init.sql) 초기 스키마도 같은 컬럼 집합으로 맞췄다.
- 재발 방지 규칙은 [error_patterns.md](/D:/03_PROJECT/05_mathOCR/error_patterns.md) 에 `ordered_segments/raw_transcript 보존` 과 `객관식 해설 검증 후 경고 치환` 규칙으로 추가했다.
- 검증 결과:
  - `py -3 -m pytest D:\\03_PROJECT\\05_mathOCR\\02_main\\tests -q` -> `164 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/api/jobApi.test.ts src/app/components/ResultsViewer.test.tsx src/app/components/JobDetailPage.test.tsx` -> `24 passed`
- 배포 영향:
  - 신규 환경 변수는 없다.
  - 백엔드 DB 마이그레이션 적용과 백엔드 재배포가 필요하다.
  - 프런트 변경도 포함되어 있어 프런트 재배포를 같이 하는 편이 안전하다.

## 2026-03-25 10:47 KST

- 사용자 요청대로 [생성결과 (1).hwpx](/D:/03_PROJECT/05_mathOCR/error/생성결과%20(1).hwpx) 와 [생성결과 (1)_answer.hwpx](/D:/03_PROJECT/05_mathOCR/error/생성결과%20(1)_answer.hwpx) 의 `Contents/section0.xml` 을 직접 비교했다.
- 비교 결과, 문제의 본질은 문단 spacing이 아니라 explanation mixed paragraph의 `hp:equation` 박스 크기였다. 두 파일의 `paraPrIDRef`, `styleIDRef`, `charPrIDRef`, `textWrap`, `textFlow`, `lineMode`, font는 같았고, 실제 차이는 `hp:sz/@width`, `hp:sz/@height`, `hp:equation/@baseLine` 에 집중됐다.
- bad 파일과 answer 파일의 해설 수식 차이는 다음 패턴으로 고정됐다.
  - bad: `width=8386`, `height=1125`, `baseLine=85`
  - answer: script별 width + `height=975`, `baseLine=86`
- 이 분석을 바탕으로 [hwpx_math_layout.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpx_math_layout.py) 의 후처리를 확장했다. 이제 해설 mixed 문단(`paraPrIDRef=0`, `styleIDRef=0`)의 inline equation은 폭만이 아니라 compact box profile 전체를 보정한다.
- [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py) 도 legacy/direct 공통으로 같은 보정을 적용하도록 바꿨다. 따라서 HwpForge direct 경로만이 아니라 최종 export bundle 전체에서 같은 박스 프로파일이 적용된다.
- TDD로 [test_exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_exporter.py) 에 `test_export_hwpx_explanation_inline_equations_use_compact_box_metrics` 를 먼저 추가해, 해설 mixed 수식이 `height=975`, `baseLine=86` 을 가져야 한다는 계약을 실패로 고정한 뒤 통과시켰다.
- 추가 검증으로 현재 보정 함수를 bad 파일에 직접 적용한 [생성결과 (1)_repaired_by_codex.hwpx](/D:/03_PROJECT/05_mathOCR/error/생성결과%20(1)_repaired_by_codex.hwpx) 를 만들었고, 해설 수식의 `width/height/baseLine` 이 answer 파일과 동일하게 맞춰지는 것을 확인했다.
- 검증 결과:
  - `py -3 -m pytest D:\\03_PROJECT\\05_mathOCR\\02_main\\tests\\test_exporter.py -q` -> `29 passed`
  - `py -3 -m pytest D:\\03_PROJECT\\05_mathOCR\\02_main\\tests -q` -> `165 passed`
  - `cd D:\\03_PROJECT\\05_mathOCR\\04_design_renewal && npm run test:run -- src/app/api/jobApi.test.ts src/app/components/ResultsViewer.test.tsx src/app/components/JobDetailPage.test.tsx` -> `24 passed`
- 배포 영향:
  - 신규 환경 변수는 없다.
  - 백엔드 재배포는 필요하다.
  - DB 마이그레이션 필요 여부는 이전 세션의 검증 메타데이터 컬럼 추가와 동일하다. 이번 턴의 HWPX 박스 프로파일 수정 자체는 추가 마이그레이션이 없다.

## 2026-03-25 11:19 KST

- Cloud Run revision `mathocr-00023-s2d` startup 실패 root cause를 확정했다. stderr 기준 `pydantic.errors.PydanticUserError: Please use typing_extensions.TypedDict instead of typing.TypedDict on Python < 3.12.` 였고, 직접 원인은 [schema.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/schema.py) 의 `OrderedSegment` 가 `typing.TypedDict` 를 사용한 점이었다.
- TDD로 [test_pipeline_schema.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_pipeline_schema.py) 를 먼저 추가했다. `ExtractorContext.model_rebuild(force=True)` 를 Pydantic `_SUPPORTS_TYPEDDICT=False` 호환 분기에서 실행해 현재 구현이 실패하는 것을 RED로 고정했다.
- 이후 [schema.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/schema.py) 를 `typing_extensions.TypedDict` 로 교체하고, [requirements.txt](/D:/03_PROJECT/05_mathOCR/02_main/requirements.txt) 에 `typing-extensions==4.15.0` 을 직접 명시했다.
- 재발 방지 규칙을 [error_patterns.md](/D:/03_PROJECT/05_mathOCR/error_patterns.md) 에 추가했다.
- 검증 결과:
  - `py -3 -m pytest 02_main/tests/test_pipeline_schema.py -q` -> `1 passed`
  - `py -3 -m pytest 02_main/tests/test_job_response_fields.py -q` -> `7 passed`
  - `_SUPPORTS_TYPEDDICT=False` 조건에서 `ExtractorContext.model_rebuild(force=True)` -> `True`
- 로컬 Docker 데몬이 꺼져 있어 루트 Dockerfile 컨테이너 스모크는 이 세션에서 직접 실행하지 못했다.
- 운영 재배포를 수행했다: `gcloud run deploy mathocr --source . --region us-central1 --project sapient-stacker-468504-r6 --quiet`
- 운영 검증 결과:
  - 새 revision `mathocr-00024-2rj` 가 ready 상태로 100% traffic을 받고 있다.
  - Cloud Run system log에 `Default STARTUP TCP probe succeeded` 와 `Uvicorn running on http://0.0.0.0:8080` 가 기록됐다.
  - `curl https://mathocr-146126176673.us-central1.run.app/billing/catalog` 기준 `200` 과 plan payload를 확인했다.
- 배포 영향:
  - 신규 환경 변수는 없다.
  - 백엔드 재배포는 완료했다.
  - 검증 메타데이터 컬럼용 DB 마이그레이션과 실제 HWPX 수동 QA는 여전히 남아 있다.

## 2026-03-25 15:41 KST

- 사용자 제공 샘플 [생성결과-2.hwpx](/D:/03_PROJECT/05_mathOCR/error/생성결과-2.hwpx) 와 [생성결과-2-ANSWER.hwpx](/D:/03_PROJECT/05_mathOCR/error/생성결과-2-ANSWER.hwpx) 를 다시 비교해, 이번 겹침 문제의 원인이 `section0.xml` mixed inline paragraph 구조와 compact equation width lookup 둘 다라는 점을 확정했다.
- bad 파일은 해설 문단이 `hp:run` 여러 개로 쪼개져 있었고, `section0.direct.xml` 과 최종 `Contents/section0.xml` 모두 같은 과소 width를 유지했다. answer 파일은 같은 문단이 한 개 `hp:run` 으로 저장되고 script별 width가 더 크게 재계산돼 있었다.
- [hwpx_math_layout.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpx_math_layout.py) 에서 후처리를 확장했다.
  - direct HwpForge가 만든 inline-only 문단은 export 직후 한 run으로 병합한다.
  - compact width lookup은 `ANGLE`/`∠`, 공백 차이를 제거한 canonical key로 처리한다.
  - [생성결과-2-ANSWER.hwpx](/D:/03_PROJECT/05_mathOCR/error/생성결과-2-ANSWER.hwpx) 에서 확인한 compact inline width 샘플을 override/profile에 추가했다.
- TDD로 [test_hwpx_math_layout.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_hwpx_math_layout.py) 를 새로 추가했다.
  - `∠ABC=∠ADE` 가 answer 폭 `8070` 으로 보정되는지
  - `AB=14` 가 answer 폭 `3870` 으로 보정되는지
  - inline-only mixed paragraph가 최종적으로 한 개 run으로 합쳐지는지
  를 RED로 고정한 뒤 통과시켰다.
- 추가 검증으로 현재 코드의 `repair_equation_widths()` 를 문제 문서의 `section0.direct.xml` 에 직접 적용해 봤고, P10~P15 문단의 run 수와 각 수식의 `width/height/baseLine` 이 answer 파일과 1:1로 같아지는 것을 확인했다.
- 검증 결과:
  - `py -3 -m pytest D:\\03_PROJECT\\05_mathOCR\\02_main\\tests\\test_hwpx_math_layout.py` -> `3 passed`
  - `py -3 -m pytest D:\\03_PROJECT\\05_mathOCR\\02_main\\tests\\test_exporter.py D:\\03_PROJECT\\05_mathOCR\\02_main\\tests\\test_hwpforge_json_builder.py D:\\03_PROJECT\\05_mathOCR\\02_main\\tests\\test_hwpx_math_layout.py` -> `37 passed`
- 배포 영향:
  - 신규 환경 변수는 없다.
  - 백엔드 재배포가 필요하다.
  - DB 마이그레이션은 이번 수정과 직접 관련 없고, 이전 세션의 운영 작업으로 별도 진행 대상이다.

## 2026-03-26 09:26 KST

- 사용자 제공 GA4 측정 ID `G-SM6ETGCFGP` 를 [04_design_renewal App 루트](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx) 에 연결했다.
- 단순 `index.html` 직삽입 대신 SPA 라우트 변경을 안정적으로 잡기 위해 [GoogleAnalyticsTracker.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.tsx) 와 [googleAnalytics.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/googleAnalytics.ts) 를 추가했다.
  - 외부 `gtag.js` 스크립트는 한 번만 주입한다.
  - `gtag("config", ..., { send_page_view: false })` 로 자동 page_view를 끄고,
  - React Router location 변화마다 수동 `page_view` 를 보낸다.
- TDD로 [GoogleAnalyticsTracker.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.test.tsx) 를 먼저 추가해 초기 진입/라우트 변경 시 `page_view` 가 기록되는지 RED로 고정한 뒤 통과시켰다.
- 검증 결과:
  - `npm run test:run -- src/app/components/GoogleAnalyticsTracker.test.tsx src/app/components/Layout.test.tsx src/app/components/PublicHomePage.test.tsx` -> `11 passed`
  - `npm run build` -> production build 성공
- 배포 영향:
  - 신규 환경 변수는 없다.
  - 프런트엔드 정적 빌드를 다시 배포해야 실제 사이트에 Analytics가 반영된다.

## 2026-03-26 09:28 KST

- 사용자 제공 Microsoft Clarity 프로젝트 ID `w1jgubofnf` 를 운영 프런트 [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx) 전역 라우트 레이아웃에 연결했다.
- 단순 `index.html` 직삽입 대신 [ClarityTracker.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ClarityTracker.tsx) 와 [microsoftClarity.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/microsoftClarity.ts) 로 분리했다.
  - `StrictMode` 에서 effect 가 두 번 실행돼도 script id 기준으로 한 번만 삽입한다.
  - 외부 스크립트 로드 전 호출도 누적되도록 `window.clarity` queue 함수를 먼저 준비한다.
  - 사용자 기능과 무관한 추적 로더라서 실패 시 예외를 던지지 않고 조용히 no-op 처리한다.
- TDD로 [ClarityTracker.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ClarityTracker.test.tsx) 를 먼저 추가해 비활성화 no-op 과 `StrictMode` 단일 삽입 계약을 RED로 고정한 뒤 통과시켰다.
- 문서화:
  - [2026-03-26-clarity-tracker-design.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-26-clarity-tracker-design.md)
  - [2026-03-26-clarity-tracker.md](/D:/03_PROJECT/05_mathOCR/docs/plans/2026-03-26-clarity-tracker.md)
- 검증 결과:
  - `npm run test:run -- src/app/components/ClarityTracker.test.tsx` -> `2 passed`
  - `npm run test:run -- src/app/components/ClarityTracker.test.tsx src/app/components/GoogleAnalyticsTracker.test.tsx` -> `4 passed`
  - `npm run build` -> production build 성공
- 배포 영향:
  - 신규 환경 변수와 백엔드 변경은 없다.
  - 프런트엔드 정적 빌드를 다시 배포해야 실제 사이트에 Clarity가 반영된다.

## 2026-03-26 10:10 KST

- 사용자 제공 Google AdSense 클라이언트 ID `ca-pub-4088422118336195` 를 운영 프런트 [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx) 전역 라우트 레이아웃에 연결했다.
- 기존 `index.html` 직삽입 대신 [AdSenseTracker.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AdSenseTracker.tsx) 와 [googleAdSense.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/googleAdSense.ts) 로 분리했다.
  - `StrictMode` 에서 effect 가 두 번 실행돼도 script id 기준으로 한 번만 삽입한다.
  - `clientId` 누락이나 `document.head` 미준비 상황은 사용자 기능과 무관한 추적 로더라서 예외를 던지지 않고 no-op 처리한다.
  - `crossorigin="anonymous"` 와 async 로더 속성을 코드에서 일관되게 부여한다.
- TDD로 [AdSenseTracker.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AdSenseTracker.test.tsx) 를 먼저 추가해 비활성화 no-op 과 `StrictMode` 단일 삽입 계약을 RED로 고정한 뒤 통과시켰다.
- 검증 결과:
  - `npm run test:run -- src/app/components/AdSenseTracker.test.tsx src/app/components/ClarityTracker.test.tsx src/app/components/GoogleAnalyticsTracker.test.tsx` -> `6 passed`
  - `npm run build` -> production build 성공
- 배포 영향:
  - 신규 환경 변수와 백엔드 변경은 없다.
  - 프런트엔드 정적 빌드를 다시 배포해야 실제 사이트에 AdSense 로더가 반영된다.

## 2026-03-26 10:21 KST

- AdSense 검증 실패 원인을 확인했다. [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html) head 에는 광고 코드가 없고, [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx) 에서 React effect 기반 `AdSenseTracker` 로 런타임 주입하던 구조라 공급자가 요구한 `<head>` 직접 삽입 계약과 달랐다.
- TDD로 [adsensePlacement.test.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/adsensePlacement.test.ts) 를 먼저 추가해 다음 계약을 RED로 고정했다.
  - 배포 원본 HTML head 에 AdSense 스크립트가 직접 들어 있어야 한다.
  - 앱 라우트는 AdSense 로더를 런타임에 다시 주입하지 않아야 한다.
- 수정 내용:
  - [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html) head 에 AdSense 스크립트를 직접 추가했다.
  - [App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx) 에서 `AdSenseTracker` import 와 마운트를 제거했다.
  - 불필요해진 `AdSenseTracker.tsx`, `AdSenseTracker.test.tsx`, `googleAdSense.ts` 를 삭제했다.
  - 같은 유형 재발 방지를 위해 [error_patterns.md](/D:/03_PROJECT/05_mathOCR/error_patterns.md) 에 `<head>` 직접 삽입 요구 스크립트는 정적 HTML에 넣는 규칙을 추가했다.
- 검증 결과:
  - `npm run test:run -- src/app/adsensePlacement.test.ts src/app/components/ClarityTracker.test.tsx src/app/components/GoogleAnalyticsTracker.test.tsx` -> `6 passed`
  - `npm run build` -> production build 성공
- 배포 영향:
  - 신규 환경 변수와 백엔드 변경은 없다.
  - 프런트엔드 정적 빌드를 다시 배포한 뒤 AdSense 화면에서 재확인해야 한다.

## 2026-03-26 10:56 KST

- 운영 사이트에서 GA4 스크립트 삽입과 `gtag.js` 로더는 정상인데 `g/collect` 요청이 전혀 발생하지 않는 현상을 재현했다.
- 원인을 [googleAnalytics.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/googleAnalytics.ts) 의 queue 구현으로 좁혔다.
  - 기존 구현은 `gtag(...args)` 호출을 `dataLayer.push(args)` 로 적재했다.
  - Playwright 대조 실험에서 같은 측정 ID를 써도 공식 스니펫처럼 `dataLayer.push(arguments)` 를 사용하면 `g/collect` 가 발생하고, 배열 push 방식을 쓰면 발생하지 않았다.
- TDD로 [GoogleAnalyticsTracker.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.test.tsx) 에 “공식 gtag 스니펫과 같은 arguments queue 형식” 회귀 테스트를 먼저 추가해 RED를 확인했다.
- 수정 내용:
  - [googleAnalytics.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/googleAnalytics.ts) 에서 `gtag` 큐 함수를 공식 스니펫과 동일한 `arguments` 객체 적재 방식으로 교체했다.
  - [GoogleAnalyticsTracker.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.test.tsx) 의 dataLayer 읽기 헬퍼를 array-like queue 엔트리 정규화 방식으로 바꾸고, 실제 queue 계약 회귀 테스트를 추가했다.
  - Clarity 는 운영 사이트와 자동화 브라우저에서 `b.clarity.ms/collect` 204 응답이 확인돼 이번 턴에는 코드 변경하지 않았다.
- 검증 결과:
  - `npm run test:run -- src/app/components/GoogleAnalyticsTracker.test.tsx` -> `3 passed`
  - `npm run test:run -- src/app/components/GoogleAnalyticsTracker.test.tsx src/app/components/ClarityTracker.test.tsx` -> `5 passed`
  - `npm run build` -> production build 성공
- 배포 영향:
  - 신규 환경 변수와 백엔드 변경은 없다.
  - 프런트엔드 정적 빌드를 다시 배포해야 운영 사이트의 GA4 `g/collect` 전송이 반영된다.

## 2026-03-26 13:15 KST

- 사용자 요청에 맞춰 `04_design_renewal` 프런트를 Vite SPA 기준 SEO 구조로 정리했다.
- 아키텍처 변경:
  - [siteSeo.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/seo/siteSeo.ts)에 canonical URL, 라우트 메타, JSON-LD, `robots.txt`, `sitemap.xml` 생성 규칙을 모았다.
  - [SeoManager.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/SeoManager.tsx)를 `TrackingLayout` 최상단에 연결해 라우트 변경 시 title/description/canonical/OG/Twitter/robots/JSON-LD를 갱신하도록 했다.
  - [seoVitePlugin.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/seoVitePlugin.ts)를 추가해 build/dev에서 `robots.txt`, `sitemap.xml`을 HTML fallback이 아닌 실제 루트 파일로 제공하도록 했다.
  - [publicAppUrl.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/publicAppUrl.ts)는 `SITE_URL`, `NEXT_PUBLIC_SITE_URL`, `APP_URL` 우선순위를 함께 읽도록 확장했다.
- UX/콘텐츠 변경:
  - [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx)를 `MathHWP` 브랜드 기준으로 재작성했다.
  - 단일 H1, 소개 문단, 기능/형식/활용 사례/FAQ/개인정보 가이드, 크롤 가능한 내부 링크를 추가했다.
  - 외부 `googleusercontent` 이미지를 제거하고 로컬 자산만 사용하도록 바꿨다.
  - [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html)에 홈 기본 메타와 JS 이전 정적 fallback 콘텐츠를 넣었다.
  - [favicon.svg](/D:/03_PROJECT/05_mathOCR/04_design_renewal/public/favicon.svg), [og-image.svg](/D:/03_PROJECT/05_mathOCR/04_design_renewal/public/og-image.svg)를 추가했다.
  - 로그인/가격/작업실의 공개 브랜드 표기도 `MathHWP`로 정리했다.
- 문서화:
  - [docs/seo.md](/D:/03_PROJECT/05_mathOCR/docs/seo.md)에 환경 변수, Search Console 후속 작업, 새 페이지 메타 추가 절차를 기록했다.
- 검증 결과:
  - `npm run test:run -- src/app/seo/siteSeo.test.ts src/app/components/SeoManager.test.tsx src/app/components/PublicHomePage.test.tsx src/app/lib/publicAppUrl.test.ts` -> `22 passed`
  - `npm run test:run` -> `134 passed`
  - `npm run build` -> production build 성공, `dist/robots.txt`, `dist/sitemap.xml`, `dist/index.html` canonical 메타 확인
- 배포 영향:
  - 프런트엔드 정적 빌드를 다시 배포해야 운영 사이트에 SEO 메타/루트 파일이 반영된다.
  - 신규 선택형 환경 변수 `SITE_URL`, `NEXT_PUBLIC_SITE_URL`, `GOOGLE_SITE_VERIFICATION`, `NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION`, `VITE_GOOGLE_SITE_VERIFICATION` 을 사용할 수 있다.

## 2026-03-26 11:08 KST

- 사용자 요청에 맞춰 Google 가이드와 정확히 일치하는 정적 GA4 스니펫을 [index.html](/D:/03_PROJECT/05_mathOCR/04_design_renewal/index.html) 의 `<head>` 바로 다음에 그대로 추가했다.
- 아키텍처 조정:
  - [GoogleAnalyticsTracker.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.tsx) 는 더 이상 `gtag.js` 로더나 `config` 를 런타임에 주입하지 않는다.
  - 초기 진입 집계는 정적 스니펫에 맡기고, SPA 라우트 변경 시점에만 `page_view` 를 수동 전송하도록 책임을 축소했다.
  - [googleAnalytics.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/lib/googleAnalytics.ts) 에서 정적 삽입 후 불필요해진 동적 로더/초기화 코드를 제거했다.
- 검증 보강:
  - [googleAnalyticsPlacement.test.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/googleAnalyticsPlacement.test.ts) 를 추가해 배포 HTML head 바로 다음에 가이드 원문 스니펫이 들어가는 계약을 고정했다.
  - [GoogleAnalyticsTracker.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/GoogleAnalyticsTracker.test.tsx) 는 정적 스니펫이 이미 존재하는 상황을 재현해, 첫 진입 중복 없이 라우트 변경 때만 `page_view` 가 적재되는지 검증하도록 갱신했다.
- 검증 결과:
  - `npm run test:run -- src/app/googleAnalyticsPlacement.test.ts src/app/components/GoogleAnalyticsTracker.test.tsx src/app/adsensePlacement.test.ts` -> `6 passed`
  - `npm run build` -> production build 성공
- 배포 영향:
  - 신규 환경 변수와 백엔드 변경은 없다.
  - 프런트엔드 정적 빌드를 다시 배포해야 운영 사이트에 정적 Google 태그 스니펫이 반영된다.

## 2026-03-26 15:05 KST

- 코드베이스 빠른 온보딩용 [manual.md](/D:/03_PROJECT/05_mathOCR/manual.md) 를 새로 작성했다.
- 문서 범위는 운영 기준 디렉터리인 [02_main](/D:/03_PROJECT/05_mathOCR/02_main) 과 [04_design_renewal](/D:/03_PROJECT/05_mathOCR/04_design_renewal) 중심으로 제한했고, [04_new_design](/D:/03_PROJECT/05_mathOCR/04_new_design) 는 실험 영역으로만 분리 표기했다.
- 문서에는 아래 항목만 압축해 정리했다.
  - 시스템 개요와 핵심 사용 사례
  - 백엔드/프런트 아키텍처와 핵심 모듈 책임
  - 로그인, 작업 실행, HWPX export, 결제 흐름
  - OCR, HWPX, billing, SEO/build 파이프라인
  - 안전한 수정 지점과 기술 스택
- 검증 결과:
  - `py -3 C:\Users\user\.codex\skills\generate-manual-md\scripts\validate_manual_structure.py D:\03_PROJECT\05_mathOCR\manual.md` -> `manual.md structure is valid.`
- 배포 영향:
  - 문서 추가만 있어 백엔드/프런트 배포 환경 변경은 없다.

## 2026-03-26 14:40 KST

- 사용자 요청에 맞춰 코드베이스를 역분석해 `manual.md`를 생성하는 전역 스킬 [SKILL.md](/C:/Users/user/.codex/skills/generate-manual-md/SKILL.md) 를 새로 만들었다.
- 스킬 설계 결정:
  - 설치 위치는 전역 경로 `C:\Users\user\.codex\skills\generate-manual-md` 로 고정했다.
  - 출력은 `Overview -> System Architecture -> Core Modules -> Data Flow -> Key Pipelines -> Extension Points -> Tech Stack` 7개 섹션으로 강제했다.
  - 분석 워크플로는 `Structure Scanner`, `Module Analyzer`, `Flow Extractor`, `Pipeline Mapper`, `Synthesizer` 5개 서브에이전트 역할로 분리했다.
- 보조 자산:
  - [manual-template.md](/C:/Users/user/.codex/skills/generate-manual-md/references/manual-template.md) 에 엄격한 마크다운 골격을 추가했다.
  - [validate_manual_structure.py](/C:/Users/user/.codex/skills/generate-manual-md/scripts/validate_manual_structure.py) 로 섹션 순서와 모듈/파이프라인 블록 구조를 검증하도록 했다.
- 검증 결과:
  - `py C:\Users\user\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\user\.codex\skills\generate-manual-md` -> `Skill is valid!`
  - `py C:\Users\user\.codex\skills\generate-manual-md\scripts\validate_manual_structure.py C:\Users\user\.codex\skills\generate-manual-md\references\manual-template.md` -> `manual.md structure is valid.`
- 배포 영향:
  - 애플리케이션 런타임, 백엔드 환경 변수, 프런트 배포에는 영향이 없다.
## 2026-03-26 16:08:01
- `04_design_renewal` 비홈 페이지 shadcn/ui 리팩터 계획을 실행했다.
- `src/app/components/shared/` 아래에 공통 presentation component 10종을 추가해 페이지/레이아웃 조합을 표준화했다.
- `/login`, `/pricing`, `/payment/:planId`, `/connect-openai`, `/new`, `/workspace`, `/workspace/job/:jobId`, `*` 와 `AuthLayout`, `StudioLayout`, `Layout`, `AppSidebar`, `AccountSheet`, `ResultsViewer` 를 shared component 기준으로 재구성했다.
- auth, billing, store, route query 계약은 유지했고 기존 테스트가 보는 문구와 경로도 유지했다.
- 검증: `npm run test:run` 138 passed, `npm run build` 통과. 빌드에는 기존과 동일한 chunk size warning만 남았다.

## 2026-03-26 16:51:46 KST

- 사용자 피드백에 따라 `04_design_renewal` 최근 디자인 리뉴얼을 사실상 전면 롤백했다.
- 아키텍처 변경:
  - [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx), [LoginPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/LoginPage.tsx), [PricingPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PricingPage.tsx), [PaymentPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PaymentPage.tsx) 등 주요 화면을 `19fa0bc` 기준 UI로 복원했다.
  - [Layout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.tsx), [AuthLayout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AuthLayout.tsx), [StudioLayout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/StudioLayout.tsx), [AppSidebar.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AppSidebar.tsx), [AccountSheet.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AccountSheet.tsx) shell도 함께 되돌렸다.
  - 미사용 [shared](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/shared) presentation layer 파일 12개를 삭제해 복원 이후 죽은 코드를 정리했다.
  - `SeoManager`, `siteSeo`, `publicAppUrl`, auth/billing runtime 계약은 유지하고, 시각/UI만 이전 스타일로 복원했다.
- UX 조정:
  - 홈 첫 화면 히어로, 중앙 하이라이트, 카드형 소개, 하단 CTA를 이전 버전의 다크 랜딩 구성으로 복구했다.
  - 다만 운영 URL/브랜드 일관성을 위해 주요 서비스명 표기는 `MathHWP`로 유지했다.
- 검증 결과:
  - `npm run test:run` -> `134 passed`
  - `npm run build` -> production build 성공, 기존과 동일한 chunk size warning만 남음
- 배포 영향:
  - 백엔드/환경 변수 변경은 없다.
  - 프런트엔드 정적 빌드를 다시 배포해야 운영 사이트에 롤백된 UI가 반영된다.

## 2026-03-26 18:35:00 KST

- 비홈 화면 한정 리퀴드 글라스 리디자인 계획을 다시 적용했다.
- 아키텍처 변경:
  - [theme.css](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/styles/theme.css)에 `liquid-shell` 스코프 토큰과 카드, 버튼, 입력, 시트, 드롭다운, 사이드바 공통 유틸을 추가했다.
  - [AuthLayout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AuthLayout.tsx), [StudioLayout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/StudioLayout.tsx), [Layout.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/Layout.tsx)에 비홈 전용 래퍼 클래스를 부여해 홈 첫 화면과 테마 범위를 분리했다.
  - [LoginPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/LoginPage.tsx), [PricingPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PricingPage.tsx), [PaymentPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PaymentPage.tsx), [OpenAiConnectionPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/OpenAiConnectionPage.tsx), [DashboardPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/DashboardPage.tsx), [NewJobPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/NewJobPage.tsx), [JobDetailPage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/JobDetailPage.tsx), [AppSidebar.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AppSidebar.tsx), [AccountSheet.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/AccountSheet.tsx)을 실버+세이지 톤의 반투명 패널 구조로 정리했다.
  - [button.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ui/button.tsx), [badge.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/ui/badge.tsx)에 variant/data-slot 훅을 보강해 비홈 화면 전체 스타일 일관성을 맞췄다.
- UX 및 접근성 조정:
  - 홈 [`PublicHomePage.tsx`](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 와 홈 전용 스타일은 건드리지 않았다.
  - 아이콘 전용 버튼 `aria-label`, 비밀번호 입력 메타데이터, 키보드 포커스 링, 키보드 접근 가능한 작업 카드 상호작용을 추가해 리디자인 후 접근성 회귀를 막았다.
- 검증 결과:
  - `npm run test:run` -> `139 passed`
  - `npm run build` -> production build 성공, 기존과 동일한 chunk size warning만 남음
  - `VITE_LOCAL_UI_MOCK=true` 로 `/`, `/login`, `/pricing`, `/payment/starter`, `/connect-openai`, `/new`, `/workspace`, `/workspace/job/:jobId` 실브라우저 스모크 QA를 확인했다.
- 배포 영향:
  - 백엔드/환경 변수 변경은 없다.
  - 프런트엔드 정적 빌드를 다시 배포해야 운영 사이트에 이번 비홈 리디자인이 반영된다.
