# HwpForge 기능 분석 및 mathOCR 적용 전략 보고서

작성일: 2026-03-23  
대상 버전: `hwpforge` workspace `0.5.0`

## 1. 핵심 요약

`hwpforge`는 단순한 HWPX 생성 라이브러리가 아니라, 다음 다섯 층을 가진 문서 플랫폼에 가깝다.

1. `HWPX/HWP5`를 읽고 쓰는 codec
2. 포맷 독립 문서 IR(`core`)
3. 스타일/템플릿 레지스트리(`blueprint`)
4. CLI 기반 변환·검증·감사 도구
5. MCP 기반 AI 편집 도구

현재 `mathOCR`의 HWPX 경로는 `OCR 결과 -> reference section 복제 -> canonical template 재패킹` 구조다. 이 구조는 수학 OCR 결과를 우리가 원하는 한글 양식으로 안정적으로 찍어내는 데 강하다. 반면 `hwpforge`는 문서를 읽고, 구조를 분석하고, Markdown/JSON으로 꺼내고, 섹션 단위로 다시 패치하는 편집성과 범용성에서 훨씬 강하다.

결론은 명확하다.

- 지금 당장 `hwpforge`로 전면 교체하는 것은 비추천이다.
- 가장 현실적인 개선은 `검증/분석/사후편집용 Rust sidecar`로 먼저 붙이는 것이다.
- 그 다음 단계로 `HWPX -> Markdown/JSON` 역변환과 `preserve-first patch`를 붙이면 현재 SaaS의 사용자 편집성과 운영 디버깅 능력이 크게 좋아진다.

## 2. 조사 근거

외부 근거:

- [lib.rs crate page](https://lib.rs/crates/hwpforge)
- [docs.rs crate page](https://docs.rs/crate/hwpforge/latest)
- [GitHub repository](https://github.com/ai-screams/HwpForge)

내부 비교 근거:

- [02_main/app/pipeline/exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py)
- [02_main/app/pipeline/hwpx_reference_renderer.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/hwpx_reference_renderer.py)
- [02_main/app/main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py)
- [02_main/README.md](/D:/03_PROJECT/05_mathOCR/02_main/README.md)
- [02_main/requirements.txt](/D:/03_PROJECT/05_mathOCR/02_main/requirements.txt)

## 3. HwpForge로 할 수 있는 작업 전체 정리

### 3.1 HWPX 문서 생성

`hwpforge`는 Rust 코드에서 직접 문서 IR을 만들고, 이를 HWPX로 인코딩할 수 있다.

- 새 문서 생성
- 섹션 추가
- 문단/런 구성
- 페이지 설정 적용
- 스타일 스토어를 붙여 최종 `.hwpx` 인코딩

이 말은 즉, 템플릿 XML을 직접 조립하지 않고도 문서 구조를 코드 수준에서 만들 수 있다는 뜻이다.

### 3.2 HWPX 문서 읽기

이미 존재하는 `.hwpx`를 디코딩해서 문서 구조를 읽을 수 있다.

- HWPX ZIP 패키지 열기
- `mimetype` 및 구조 검증
- section/header/footer/style/image store 복원
- decode 후 validate 수행

현재 우리 서비스에는 `기존 HWPX를 읽어 분석하는 정식 경로`가 거의 없는데, `hwpforge`는 이 부분이 기본 기능이다.

### 3.3 Lossless roundtrip

문서를 읽고 다시 쓰는 roundtrip을 지원한다.

- `decode -> validate -> encode`
- 지원 범위 내 콘텐츠는 lossless roundtrip 지향
- section patch는 preserve-first 방식으로 원본 패키지 보존을 우선함

이건 운영에서 매우 중요하다. 단순 생성기가 아니라, 기존 문서를 가능한 한 안 깨뜨리고 다룰 수 있는 기반이 있다는 의미다.

### 3.4 Markdown <-> HWPX 변환

`hwpforge`의 핵심 강점 중 하나다.

- Markdown -> HWPX
- HWPX -> Markdown
- lossy Markdown encode
- lossless HTML+YAML 기반 encode
- YAML frontmatter 처리
- GFM 기반 표, 제목, 리스트, 링크 등 지원

즉 AI 친화적인 중간 표현을 공식 한글 포맷과 연결하는 다리 역할을 한다.

### 3.5 JSON round-trip 편집

현재 시점에서 `mathOCR`가 가장 크게 배울 수 있는 부분이다.

- 전체 문서를 JSON으로 export
- 특정 section만 JSON으로 export
- JSON Schema 출력
- JSON에서 HWPX 재생성
- base HWPX에 section만 patch
- preserve-first patch로 원본 패키지의 이미지/스타일/나머지 section 유지

특히 section patch는 단순 재생성이 아니라, preservation metadata를 이용해 원본 `sectionN.xml`의 patch 가능한 text slot만 교체하려고 설계돼 있다.

### 3.6 문서 구조 분석/검증

CLI/MCP 레벨에서 다음 작업이 가능하다.

- 문서 구조 inspect
- 섹션 수, 문단 수, 표/이미지/차트 수 요약
- HWPX 구조/무결성 validate
- JSON 에러 포맷과 machine-readable 출력

운영 디버깅과 CI 품질 게이트에 바로 쓸 수 있는 능력이다.

### 3.7 스타일 프리셋/템플릿

`blueprint`와 preset 계층으로 스타일을 다룬다.

- built-in preset 조회
- preset 기반 Markdown -> HWPX 생성
- 기존 문서 restyle
- YAML 템플릿 상속 구조
- style registry 기반 char/para shape 관리

다만 주의할 점도 있다.

- 공개 preset은 현재 `default`, `modern`, `classic`, `latest` 중심이다.
- `restyle`은 실제 코드상 전체 레이아웃 재설계보다 `기존 style store의 base font 교체` 성격이 강하다.
- 즉, “완전한 템플릿 변환기”라고 보기는 이르다.

### 3.8 지원 콘텐츠

문서 모델 기준으로 지원 범위는 넓다.

- 텍스트
- character shape / paragraph shape / style
- 표
- 이미지
- 텍스트박스
- 캡션
- 다단
- 페이지 설정
- 가로/세로 방향
- 제본 여백
- master page
- header / footer / page number
- footnote / endnote
- 도형: line, ellipse, polygon, arc, curve, connect line
- 수식: HancomEQN script
- 차트: 18종 OOXML chart
- 참조: bookmark, cross reference, field, memo, index mark
- 주석성 요소: dutmal, compose characters

추가로 최근 변경점 기준으로 다음 세부 속성도 강화되고 있다.

- table page-break
- repeat-header
- cell-spacing
- border/fill reference
- header-row semantics
- cell margin
- vertical align
- image placement metadata
- tab-stop semantics

### 3.9 HWP5(`.hwp`) 경로

README와 코드 기준으로 HWP5는 완성형 write 경로는 아니지만, 꽤 실용적인 read/audit 계층이 이미 있다.

- `convert-hwp5`
- `audit-hwp5`
- `census-hwp5`
- HWP5 semantic truth 추출
- HWP5 -> HWPX 변환 결과를 source truth와 비교
- 표 반복 헤더, page break, OLE 기반 차트 흔적, 섹션별 구조 차이를 감사

다만 프로젝트 문서에는 여전히 `smithy-hwp5`와 `bindings-py`가 “예정”으로도 표기된다. 이건 기능이 없다는 뜻보다는, API 안정성/지원 약속이 HWPX 메인 경로만큼 단단하지 않다는 신호로 읽는 게 맞다.

### 3.10 AI 통합

`hwpforge`는 AI 도구와의 결합을 전면에 둔다.

- CLI
- MCP server
- resource
- prompt
- JSON schema

현재 코드 기준 MCP 도구는 다음이 확인된다.

- `hwpforge_convert`
- `hwpforge_inspect`
- `hwpforge_to_json`
- `hwpforge_from_json`
- `hwpforge_patch`
- `hwpforge_validate`
- `hwpforge_restyle`
- `hwpforge_templates`
- `hwpforge_to_md`

즉, 생성뿐 아니라 읽기, 검증, 변환, 부분 편집까지 AI 툴 호출 표면으로 노출돼 있다.

## 4. 현재 mathOCR 구조와의 비교

### 4.1 현재 구조가 잘하는 일

현재 백엔드는 HWPX export를 매우 명확한 하나의 목적에 최적화하고 있다.

- `POST /jobs/{job_id}/export/hwpx` 및 다운로드 엔드포인트 제공
- `python-hwpx` 의존성 사용
- `02_main/vendor/hwpxskill-math` runtime 사용
- `style_guide.hwpx` canonical bundle을 기준으로 패키지 유지
- `section0.xml`의 reference subtree를 복제해 문제/보기/해설을 삽입
- 수학 OCR 결과를 한글 수식 스크립트 친화 표기로 정규화

즉, 우리는 이미 “범용 HWPX 편집기”가 아니라 “수학 OCR 산출물을 한글 문서로 안정 출력하는 엔진”을 만들고 있다.

### 4.2 현재 구조의 제한

반대로 지금 구조는 아래 지점에서 한계가 분명하다.

- 기존 HWPX를 읽고 분석하는 표준 경로가 약함
- HWPX -> Markdown / JSON 역변환 부재
- section 단위 정밀 patch 부재
- 템플릿/스타일 registry가 아닌 단일 canonical template 의존
- 스타일 프리셋 개념 부재
- 구조 inspect / validate / schema 공개 경로 부재
- HWP5 intake / audit 부재

### 4.3 구조적 차이 한 줄 정리

- `mathOCR`: 출력 품질 고정형, 수학 OCR 특화, template parity 중심
- `hwpforge`: 범용 문서 플랫폼형, read/edit/convert/validate 중심

## 5. mathOCR에 바로 개선 가능한 부분

### 5.1 1순위: HWPX 검증 sidecar 추가

가장 현실적이고 효과가 큰 개선이다.

적용 방식:

- 현재 Python exporter는 그대로 유지
- export 직후 `hwpforge inspect` + `hwpforge validate`를 sidecar로 실행
- 결과를 로그 또는 CI artifact로 저장

얻는 이점:

- 우리가 놓친 구조 손상 탐지
- section 수, 표/이미지/차트 수 자동 요약
- 운영 장애 시 “파일은 내려갔지만 내부 구조가 깨진 경우” 조기 탐지

성능/보안/비용 관점:

- 성능: export 후 한 번 더 decode 비용이 든다. 하지만 배치/비동기 검증으로 완화 가능하다.
- 보안: Rust 쪽에서 ZIP/mimetype 검증과 구조 검증을 추가로 받는 셈이라 오히려 안전성이 올라간다.
- 비용: Cloud Run 이미지에 Rust binary를 싣는 운영 비용이 소폭 증가한다.

### 5.2 2순위: HWPX -> Markdown/JSON 역변환 추가

현재 서비스는 내보내기만 강하고, 산출물 사후 분석 경로가 없다.

적용 방식:

- 관리자/운영 전용 툴로 `to-md`, `to-json`
- 실패한 export 샘플이나 사용자 문서를 역으로 읽어 구조 점검
- LLM이 기존 한글 산출물을 읽고 수정 제안을 할 수 있는 기반 확보

얻는 이점:

- 고객 문서 역분석
- 운영 디버깅 속도 향상
- “내가 만든 HWPX를 다시 AI가 읽고 수정”하는 루프 구성 가능

### 5.3 3순위: section preserving patch 개념 도입

우리 현재 구조는 문서를 다시 생성하는 방식이다. 사용자가 export 후 일부 문장만 고치려면 전체 재생성이 필요하다.

적용 방향:

- 사용자 수정은 section-level JSON edit로 분리
- 원본 HWPX는 보존
- 텍스트 슬롯만 교체

이 방식이 붙으면 다음이 가능해진다.

- OCR 결과 오탈자 수정
- 해설 문구만 수정
- 원본 이미지/레이아웃/스타일 유지
- “문서 전체 다시 만들기” 없이 부분 수정

### 5.4 4순위: preset/template abstraction 도입

현재 `style_guide.hwpx` 1개에 강하게 묶여 있다.

개선 방향:

- canonical bundle을 고객사/시험지 유형별 preset으로 분리
- `style_guide.hwpx`를 하나의 preset으로 취급
- 이후 `school_exam`, `academy_handout`, `teacher_solution` 같은 variant 추가

이건 `hwpforge`의 preset/blueprint 철학을 우리 현실에 맞게 옮겨오는 작업이다.

### 5.5 5순위: 운영 감사 도구 강화

`hwpforge`의 HWP5 감사 도구를 그대로 가져오긴 어렵더라도, 접근법은 바로 배울 수 있다.

적용 방향:

- export 결과에 대해 `deep counts` 요약 저장
- 섹션별 첫 문장, 표 수, 이미지 수, 해설 수, header/footer 유무 기록
- 회귀 테스트에서 이전 결과와 diff

즉 “파일이 생성됐다”가 아니라 “구조가 기대와 같은가”까지 보는 체계로 바꾸는 것이다.

## 6. 적용 대안 3가지

### 대안 A. 검증 전용 sidecar

구성:

- Python exporter 유지
- Rust `hwpforge`는 `inspect/validate/to-md` 전용

장점:

- 현재 서비스 리스크 최소
- 빠른 도입 가능
- 운영 디버깅 즉시 개선

단점:

- 사용자 편집 경험 개선은 제한적
- 문서 생성 로직 품질 향상 자체는 제한적

추천도:

- 가장 추천

### 대안 B. 생성은 Python, 편집/변환은 Rust 하이브리드

구성:

- export 생성은 현재 pipeline 유지
- post-export edit/inspect/patch는 `hwpforge`

장점:

- 현재 수학 OCR 특화 로직 보존
- 역변환/사후편집/부분수정 확보
- 기능 대비 리스크가 적절함

단점:

- Python/Rust 이중 스택 운영 필요
- JSON 계약과 파일 경로 계약을 정리해야 함

추천도:

- 중기적으로 가장 좋은 목표

### 대안 C. HWPX 파이프라인 전면 Rust 전환

구성:

- reference renderer, canonical packer, validation을 Rust 기반으로 재작성

장점:

- 장기적으로 구조 일관성 확보
- 문서 플랫폼화 가능

단점:

- 지금까지 쌓은 `style_guide.hwpx` parity 노하우 재구현 필요
- Python 기반 OCR pipeline과 연결 비용 큼
- Python binding이 아직 stub이라 바로 drop-in 불가
- 배포 이미지/빌드 파이프라인 변경 필요

추천도:

- 현재 시점 비추천

## 7. 권장 실행 순서

1. `hwpforge inspect` + `validate`를 로컬 CI/운영 smoke test에 붙인다.
2. 관리자용 `to-md` 또는 `to-json` 툴을 붙여 exported HWPX를 역분석할 수 있게 한다.
3. section patch 개념을 검증용 PoC로 붙인다.
4. 그 다음에야 preset abstraction 또는 Rust sidecar 확장을 결정한다.

## 8. 주의사항

### 8.1 과대평가하면 안 되는 부분

- Python binding은 아직 사실상 미구현 stub이다.
- HWPX 완전 지원은 아직 roadmap에 남아 있다.
- `restyle`은 현재 코드상 폰트 교체 중심이다.
- preserve-first patch는 텍스트성 수정에 특히 강하고, 구조/스타일 대수술은 별도 rebuild가 필요하다.

### 8.2 문서와 실제 코드의 미세한 드리프트

조사 중 다음 드리프트가 보였다.

- README/MCP 소개 문구와 실제 server code의 tool 개수가 완전히 같지 않다.
- HWP5는 README 상 사용 가능성이 보이지만 일부 구조 문서에는 여전히 “예정”으로 남아 있다.

이 뜻은 `hwpforge`가 빠르게 진화 중이라는 것이다. 도입 시 README만 보지 말고 실제 crate 코드와 changelog를 함께 확인해야 한다.

### 8.3 배포 환경 영향

`mathOCR`에 `hwpforge`를 실제 도입하면 배포 환경이 바뀐다.

- Cloud Run 이미지에 Rust binary 또는 별도 sidecar 포함 필요
- 빌드 단계에 Cargo 또는 사전 빌드 아티팩트 추가 필요
- 이미지 크기와 cold start에 영향 가능

즉, 이건 단순 라이브러리 교체가 아니라 배포 파이프라인 변경 이슈다.

## 9. 최종 권고

현재 `mathOCR`의 핵심 경쟁력은 “수학 OCR 결과를 특정 한글 양식으로 안정 출력”하는 데 있다. 이 강점을 버리고 `hwpforge`로 바로 갈아타는 것은 기술적으로도, 사업적으로도 효율이 낮다.

대신 아래 전략이 가장 현실적이다.

- 단기: `hwpforge`를 검증/분석 도구로 도입
- 중기: `HWPX -> Markdown/JSON -> section patch` 편집 루프 도입
- 장기: Rust sidecar 확대 여부를 실제 운영 데이터로 판단

한 줄로 정리하면:

> `hwpforge`는 지금 당장 “대체 엔진”보다 “검증·역변환·사후편집 엔진”으로 붙이는 것이 맞다.
