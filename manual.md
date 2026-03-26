## 1. Overview

- 이 시스템은 수식이 포함된 이미지를 업로드해 OCR, 해설 생성, 이미지 보정, HWPX 내보내기까지 연결하는 웹 애플리케이션이다.
- 운영 기준은 백엔드 `02_main`과 프런트엔드 `04_design_renewal`이며, 공개 홈과 작업실, 결제, 결과 확인이 하나의 흐름으로 이어진다.
- 핵심 사용 사례는 사용자가 문제 이미지를 올리고 영역을 지정한 뒤 결과를 문서로 내려받는 것이다.

## 2. System Architecture

- 고수준 컴포넌트
  - `[02_main/app/main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py)`는 FastAPI 진입점으로 인증, 과금, 작업 실행, export API를 노출한다.
  - `[02_main/app/billing.py](/D:/03_PROJECT/05_mathOCR/02_main/app/billing.py)`는 Polar checkout, webhook, 크레딧, 사용자 OpenAI 키를 관리한다.
  - `[02_main/app/pipeline/](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline)`은 OCR 작업 상태, 저장소, 오케스트레이션, export를 담당한다.
  - `[04_design_renewal/src/main.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/main.tsx) -> [04_design_renewal/src/app/App.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/App.tsx)`는 React 라우팅과 전역 provider를 조립한다.
  - `[04_design_renewal/src/app/context/AuthContext.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/context/AuthContext.tsx)`와 `[04_design_renewal/src/app/store/jobStore.ts](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/store/jobStore.ts)`가 화면 상태의 중심이다.
- 상호작용 방식
  - 프런트는 Supabase 세션과 billing profile을 먼저 동기화한 뒤 `/new`, `/workspace`, `/pricing` 흐름을 연다.
  - 작업 데이터는 `jobApi`를 통해 백엔드로 오가고, 실제 진실 소스는 Supabase DB/Storage와 `/billing/profile`, `/jobs/{id}` 응답이다.
  - 공개 SEO는 `SeoManager`와 `siteSeo`가 라우트별 메타와 정적 자산을 갱신한다.
  - `04_new_design`은 실험 영역으로만 보면 되며 운영 경로와 섞어 해석하면 안 된다.

## 3. Core Modules

### `02_main/app/main.py`

- Role: HTTP 계약 계층, 예외 정규화, 백엔드 라우트 조립
- Inputs: 업로드 파일, JWT, 작업 실행 옵션, 결제/웹훅 요청
- Outputs: job 상세/실행 응답, billing 응답, HWPX 다운로드 응답
- Dependencies: `auth.py`, `billing.py`, `pipeline`, `config`, `supabase`

### `02_main/app/auth.py`

- Role: Supabase JWT 검증과 사용자 컨텍스트 생성
- Inputs: `Authorization` 헤더, Supabase URL, JWT 관련 설정
- Outputs: `AuthenticatedUser`, 인증 실패 예외
- Dependencies: `PyJWT`, `requests`, `config`

### `02_main/app/billing.py`

- Role: Polar 상품 검증, checkout/webhook, 크레딧 적립과 차감, OpenAI 키 저장
- Inputs: 사용자, plan id, webhook payload, job/action 목록
- Outputs: billing profile, checkout 정보, 적립/차감 결과
- Dependencies: Polar SDK, `standardwebhooks`, Supabase, `auth`, `config`

### `02_main/app/pipeline/schema.py`

- Role: job/region/extractor/figure 상태 모델 정의
- Inputs: 도메인 상태 값
- Outputs: `JobPipelineContext`, `RegionPipelineContext` 등
- Dependencies: Pydantic

### `02_main/app/pipeline/repository.py`

- Role: Supabase DB/Storage를 파이프라인 저장소로 추상화
- Inputs: job 상태, region 상태, 바이너리/텍스트 자산, 사용자 토큰
- Outputs: DB row 매핑, signed URL, 저장/조회 결과
- Dependencies: `supabase`, `config`, `schema_compat`, `pipeline.schema`

### `02_main/app/pipeline/orchestrator.py`

- Role: OCR, 해설, 이미지 stylize, HWPX export를 순차 오케스트레이션
- Inputs: `job_id`, 사용자, API key, 실행 옵션, 변환 설정
- Outputs: 처리 완료 job 상태, 실행 요약, export 경로
- Dependencies: `extractor`, `figure`, `repository`, `exporter`, `markdown_contract`

### `02_main/app/pipeline/extractor.py`

- Role: GPT 기반 OCR/해설 생성과 Nano Banana 스타일 이미지 생성
- Inputs: crop 이미지, OCR 옵션, 해설 입력, 모델/프롬프트 설정
- Outputs: 구조화 OCR 결과, 해설 payload, 스타일 이미지 바이트
- Dependencies: OpenAI, `google-genai`, 프롬프트 자산, `config`

### `02_main/app/pipeline/exporter.py`

- Role: canonical HWPX 템플릿을 기반으로 최종 `.hwpx` 생성
- Inputs: 완료된 job, export 디렉터리, runtime/template 설정
- Outputs: 검증된 HWPX 파일
- Dependencies: `hwpx_reference_renderer`, `hwpforge_roundtrip`, `hwpx_math_layout`, vendored runtime

### `04_design_renewal/src/app/api/jobApi.ts`

- Role: 작업 생성/저장/실행/조회/export용 백엔드 어댑터
- Inputs: 파일, job id, region payload, 실행 옵션
- Outputs: `BackendJob`, `RunPipelineResult`, 다운로드 blob
- Dependencies: `fetch`, Supabase 세션, `apiBase`

### `04_design_renewal/src/app/context/AuthContext.tsx`

- Role: 인증, 프로필, 크레딧, OpenAI 연결 상태의 단일 진입점
- Inputs: Supabase 세션, billing API 응답, local storage 상태
- Outputs: 로그인/로그아웃, OpenAI 연결, 크레딧 갱신 함수
- Dependencies: `billingApi`, `authStorage`, `localUiMock`, `supabase`

### `04_design_renewal/src/app/store/jobStore.ts`

- Role: 프런트 job aggregate 상태와 optimistic UI 전환 관리
- Inputs: UI 이벤트, 백엔드 job 응답
- Outputs: 화면용 `jobs` 상태, create/save/run/export 액션
- Dependencies: `jobApi`, `jobMappers`, React state

## 4. Data Flow

- 사용자는 공개 홈에서 로그인하고, `AuthContext`가 Supabase 세션과 `/billing/profile` 응답을 합쳐 화면 상태를 만든다.
- `/new`에서 이미지를 업로드하면 프런트가 `POST /jobs`로 job을 만들고 `PUT /jobs/{id}/regions`로 영역을 저장한다.
- 실행 시 프런트는 `POST /jobs/{id}/run`을 호출하고, 백엔드는 선택된 액션 기준으로 크레딧을 선검사한 뒤 OCR/해설/이미지 처리를 수행한다.
- 완료 후 프런트는 `GET /jobs/{id}`로 최신 상태를 다시 받아 결과 화면을 갱신하고, 필요하면 `POST /jobs/{id}/export/hwpx`와 `/download`로 문서를 내려받는다.
- 결제는 `/pricing -> /payment/:planId -> Polar checkout -> polling -> webhook 적립` 순서로 진행되며, 최종 크레딧 반영은 webhook과 Supabase 저장소가 기준이다.

## 5. Key Pipelines

### OCR 변환 파이프라인

1. `POST /jobs`로 원본 이미지를 Supabase Storage에 저장하고 job row를 만든다.
2. `PUT /jobs/{id}/regions`로 사용자가 지정한 영역을 `queued` 상태로 저장한다.
3. `POST /jobs/{id}/run`에서 각 region을 crop하고 GPT로 OCR/해설을 생성한다.
4. 필요하면 이미지 영역을 다시 crop해 스타일 이미지를 만들고 결과를 Storage에 저장한다.
5. `GET /jobs/{id}`로 DB와 Storage 상태를 합쳐 프런트에 반환한다.

### HWPX export 파이프라인

1. 완료된 job을 읽고 export 가능한 region만 선별한다.
2. canonical HWPX 템플릿을 풀고 runtime 자산과 section0.xml을 준비한다.
3. legacy renderer 또는 direct/roundtrip HwpForge 경로로 문서 본문을 만든다.
4. manifest, header, masterpage, style 참조를 검증한 뒤 `.hwpx`로 패키징한다.
5. 생성 결과를 Supabase Storage에 저장하고 다운로드 엔드포인트를 제공한다.

### Billing 파이프라인

1. `/billing/catalog`에서 Polar 상품 3개를 읽어 플랜을 검증한다.
2. `/billing/checkout`로 checkout 세션을 만들고 사용자를 Polar로 보낸다.
3. webhook `order.paid`가 들어오면 idempotent 하게 적립을 기록한다.
4. `/jobs/{id}/run`에서는 실행 전 크레딧을 선검사하고, 실행 후 성공한 액션만 후차감한다.

### SEO/build 파이프라인

1. `siteSeo`가 경로별 title, description, robots, canonical, JSON-LD를 계산한다.
2. `SeoManager`가 라우트 변경마다 head 메타와 canonical을 갱신한다.
3. `seoVitePlugin`이 `robots.txt`와 `sitemap.xml`을 build/dev에서 직접 제공한다.
4. `index.html`과 공개 홈은 검색 노출과 운영 브랜드를 위한 정적 fallback 역할을 한다.

## 6. Extension Points

- 새로운 OCR/해설 단계 추가: `pipeline/orchestrator.py`에서 region 처리 순서를 바꾸고, 필요하면 `pipeline/schema.py`와 `jobApi.ts`를 함께 확장한다.
- 새로운 저장소나 외부 스토리지 연결: `pipeline/repository.py`를 교체하거나 추가 구현을 붙이면 된다.
- 결제 플랜/적립 규칙 변경: `billing.py`와 Polar 상품 설정, 관련 스키마를 우선 수정한다.
- HWPX 출력 규격 변경: `pipeline/exporter.py`와 `hwpx_reference_renderer.py` 축을 수정하고, `02_main/README.md`의 runtime 계약을 같이 확인한다.
- 공개 홈 메타/색인 확장: `src/app/seo/siteSeo.ts`, `SeoManager.tsx`, `seoVitePlugin.ts`를 수정한다.
- 화면 흐름 변경: `components/*Page.tsx`, `AuthContext.tsx`, `jobStore.ts`, `api/*` 순서로 맞춘다.

## 7. Tech Stack

- Frameworks: FastAPI, React, Vite, React Router
- Infra: Supabase, Polar, Vercel, Cloud Run, Docker
- Database: Supabase Postgres
- External services: OpenAI, Google GenAI, Polar
