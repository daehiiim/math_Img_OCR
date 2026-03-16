# Supabase OCR Storage Design

**목표:** `02_main`의 로컬 `runtime/jobs` 영구 저장을 제거하고 `Supabase DB + Supabase Storage`를 정답 저장소로 전환한다.

## 접근 후보

### 1. Supabase REST + Storage REST + 사용자 JWT 전달

- FastAPI가 브라우저의 Supabase 세션 토큰을 받아 `rest/v1`와 `storage/v1`를 호출한다.
- 장점: 새 Python 의존성이 거의 없고, RLS 정책을 그대로 활용할 수 있다.
- 단점: REST 요청 조립 코드가 다소 장황하고, 작업 수가 많아지면 서버와 Supabase 사이 HTTP 왕복이 늘어난다.

### 2. Postgres 드라이버 + Storage REST

- DB는 `psycopg`로 직접 다루고, 파일만 Storage REST를 사용한다.
- 장점: SQL 제어력이 높고 배치 업데이트가 쉽다.
- 단점: 의존성 추가가 필요하고, RLS보다 서버 권한 설계가 앞서 정리되어야 한다.

### 3. Supabase Python SDK 일원화

- DB/Storage를 SDK로 통일한다.
- 장점: 코드가 짧아질 수 있다.
- 단점: Python 3.14 호환성과 SDK 추상화 디버깅 비용이 불확실하다.

## 채택안

1번을 채택한다.

- 현재 저장 전환의 핵심 병목은 로컬 파일 의존 제거이지 ORM 도입이 아니다.
- 이미 프로젝트에 `requests`가 있고, Supabase는 공식적으로 `rest/v1`와 `storage/v1/object/authenticated/...` 경로를 제공한다.
- 현재 API는 동기 요청 단위로 처리되므로 사용자 JWT를 그대로 전달해도 동작 모델이 단순하다.

## 아키텍처

### 저장 계층

- `SupabasePipelineRepository`
  - `ocr_jobs`, `ocr_job_regions`를 읽고 쓰는 저장소
  - `source_image_path`, `svg_path`, `edited_svg_path`, `crop_path`, `png_rendered_path`, `hwpx_export_path`를 내부 경로로 유지
- `PipelineRepository` 프로토콜
  - 파이프라인은 저장소 구현을 모르고 `create_job`, `read_job`, `save_job`, `upload_bytes`, `download_bytes`, `download_text`만 호출
- 테스트에서는 메모리 저장소 더블을 사용

### 인증 계층

- 브라우저는 Supabase 세션의 access token을 `Authorization: Bearer ...`로 FastAPI에 전달
- FastAPI는 `SUPABASE_JWT_SECRET`으로 JWT를 검증하고 `user_id`와 `access_token`을 얻는다
- 저장소 호출은 같은 토큰으로 Supabase REST/Storage에 접근한다

### 자산 처리

- 영구 저장: Supabase Storage bucket
- 임시 작업: `tempfile.TemporaryDirectory()`
- OCR, PNG 렌더, HWPX 생성은 로컬 임시 경로를 사용하고 끝나면 Storage로 업로드한다

### API 응답

- DB에는 내부 storage path를 저장
- 프런트 응답의 `image_url`, `crop_url`, `svg_url`, `edited_svg_url`는 FastAPI 프록시 URL로 재구성
- 다운로드 API는 Storage에서 읽은 바이트를 그대로 스트리밍한다

## 필요한 스키마 변경

- `ocr_jobs`
  - `image_width integer`
  - `image_height integer`
- `ocr_job_regions`
  - `mathml text`
  - `model_used text`
  - `openai_request_id text`
- `storage.buckets`, `storage.objects` 정책
  - bucket: `ocr-assets`
  - 경로 규칙: `{user_id}/{job_id}/...`
  - `storage.foldername(name)[1] = auth.uid()::text` 정책 사용

## 위험과 대응

- 위험: Storage bucket/RLS가 미설정이면 업로드가 전부 실패한다.
  - 대응: SQL 마이그레이션 파일로 bucket/policy를 같이 제공한다.
- 위험: 프런트가 토큰을 붙이지 않으면 모든 API가 401이 된다.
  - 대응: `jobApi.ts`에서 요청 공통 헤더에 세션 토큰을 주입한다.
- 위험: 동기 파이프라인에서 중간 실패 시 일부 결과만 남을 수 있다.
  - 대응: 각 region 처리 후 즉시 `save_job`으로 DB 상태를 갱신한다.
