# HWPX 구조 분석 보고서

작성일: 2026-03-23  
목적: 이후 AI agent가 HWPX 파일을 안정적으로 분석하고 편집할 수 있도록, HWPX의 패키지 구조, XML 논리 구조, 참조 규칙, 편집 규칙을 정리한다.

## 1. 핵심 요약

- HWPX는 `ZIP 패키지 + XML 파트 + 바이너리 리소스`로 구성된 개방형 문서 포맷이다.
- 문서 읽기의 시작점은 파일명 정렬이 아니라 `Contents/content.hpf`의 `manifest`와 `spine`이다.
- 본문 텍스트는 주로 `Contents/sectionN.xml` 내부의 `hp:p -> hp:run -> hp:t` 구조에 저장된다.
- 서식 자체는 본문 XML에 중복 저장되지 않고, 대부분 `Contents/header.xml`의 `hh:refList`에 정의되고 본문에서 `paraPrIDRef`, `charPrIDRef`, `styleIDRef`로 참조된다.
- 표, 그림, 머리말/꼬리말, 미리보기, 바이너리 첨부는 각각 별도 파트 또는 별도 폴더로 분리된다.
- AI agent가 HWPX를 편집할 때 가장 중요한 규칙은 `참조 무결성 유지`, `spine 순서 보존`, `namespace 동적 처리`, `manifest/header/section 간 동기화`다.

## 2. 분석 범위와 출처 신뢰도

### 2.1 원문 접근 상태

- 사용자가 요청한 NHN Cloud Meetup 글 `https://meetup.nhncloud.com/posts/311`은 2026-03-23 기준 404로 확인됐다.
- 따라서 본 보고서는 다음 3종의 자료를 교차 검증해 작성했다.
  - 원문을 직접 가리키는 2차 인용 자료
  - 한컴 공식 HWPX 구조 문서
  - 한컴 공식 Python 파싱 문서

### 2.2 출처별 역할

| 출처 | 역할 | 신뢰도 |
|---|---|---|
| NHN Meetup 원문 URL | 원 요청 대상 확인, 현재 접근 불가 상태 확인 | 낮음 |
| GitHub Wiki 2차 인용 | 원문 핵심 포인트 복원 보조 | 중간 |
| 한컴 공식 HWPX 구조 문서 | 패키지 구조와 파일 역할의 1차 근거 | 높음 |
| 한컴 공식 Python 파싱 문서 (1), (2) | 실제 파싱/참조 규칙의 1차 근거 | 높음 |
| 한컴 HWP/OWPML 형식 안내 | 포맷 공개 범위와 표준 배경 확인 | 높음 |
| 로컬 샘플 [style_guide.hwpx](/D:/03_PROJECT/05_mathOCR/templates/style_guide.hwpx) | 현재 저장소에서 실제 사용 중인 패키지 구조 검증 | 높음 |

### 2.3 추론으로 표시하는 범위

- 아래 문서에서 `추론`이라고 표시한 항목은 공식 문서의 직접 문장보다 한 단계 더 나아가, AI 편집기 설계 관점에서 재정리한 운영 규칙이다.
- 예를 들어 `Preview` 폴더를 편집 우선순위에서 후순위로 두는 판단, `text-only edit`와 `structure edit`를 나누는 정책은 공식 구조 설명과 로컬 샘플을 바탕으로 정리한 실무 규칙이다.

## 3. NHN 원문 핵심 내용 복원

GitHub Wiki의 2차 인용과 한컴 공식 문서를 대조하면, 원문은 대체로 아래 메시지를 전달한 것으로 복원된다.

- HWPX는 기존 바이너리 중심 HWP보다 내부 분석이 쉬운 새로운 한/글 포맷이다.
- 파일 전체는 ZIP처럼 열어볼 수 있고, 핵심 데이터는 XML에 저장된다.
- 본문은 `section.xml`에 저장되며, 페이지 단위 파일이 아니라 문단이 순차적으로 쌓이는 방식이다.
- 문서 본문의 기본 단위는 `hp:p`이고, 그 아래 `hp:run`, `hp:t`가 텍스트 표현의 핵심 단위다.
- 표와 그림도 별도 바이너리 포맷이 아니라 XML 구조와 참조 체계로 연결된다.
- `header.xml`의 `refList`가 본문 서식 참조의 중심이며, ID 기반 매핑 테이블을 잘 이해해야 파싱과 편집이 가능하다.

즉, 원문은 "HWPX를 ZIP 안의 XML 묶음으로 이해하면, 사람이든 프로그램이든 HWP보다 훨씬 쉽게 분석할 수 있다"는 방향의 입문 글로 보는 것이 타당하다.

## 4. HWPX 패키지 구조

### 4.1 최상위 구조

HWPX는 ZIP 패키지이며, 일반적으로 다음과 같은 구조를 가진다.

```text
mimetype
version.xml
settings.xml
Contents/
  content.hpf
  header.xml
  section0.xml
  section1.xml
  ...
  masterpage0.xml
  masterpage1.xml
BinData/
META-INF/
Preview/
Scripts/
```

문서에 따라 일부 폴더나 파일은 없을 수 있다. 예를 들어 이미지가 없으면 `BinData/`가 비어 있거나 없을 수 있고, 스크립트가 없으면 `Scripts/`가 없을 수 있다.

### 4.2 현재 저장소의 실측 결과

현재 저장소의 대표 템플릿 [style_guide.hwpx](/D:/03_PROJECT/05_mathOCR/templates/style_guide.hwpx)에는 아래 항목이 존재한다.

```text
BinData/image1.bmp
Contents/content.hpf
Contents/header.xml
Contents/masterpage0.xml
Contents/masterpage1.xml
Contents/section0.xml
META-INF/container.rdf
META-INF/container.xml
META-INF/manifest.xml
mimetype
Preview/PrvImage.png
Preview/PrvText.txt
settings.xml
version.xml
```

또한 `mimetype` 값은 `application/hwp+zip`으로 확인됐다.

## 5. 핵심 파일별 역할

### 5.1 `mimetype`

- HWPX 패키지 시그니처다.
- 로컬 샘플 기준 값은 `application/hwp+zip`이다.
- 압축 해제 전에 파일 유형을 빠르게 판별할 때 가장 먼저 확인할 수 있다.

### 5.2 `version.xml`

- OWPML 버전과 문서를 저장한 애플리케이션 환경 정보를 담는다.
- 버전 차이에 따라 namespace 해석 전략이 달라질 수 있으므로, 파서는 이 정보를 참고하되 namespace는 XML에서 직접 추출하는 편이 더 안전하다.

### 5.3 `settings.xml`

- 커서 위치(`CaretPosition`)와 외부 설정 정보를 저장한다.
- 텍스트 본문을 읽는 데 필수는 아니지만, 편집기 복원성과 사용자 상태 재현에는 의미가 있다.

### 5.4 `Contents/content.hpf`

- HWPX 패키지의 핵심 인덱스 파일이다.
- OPF(Open Packaging Format) 구조를 따르며 `metadata`, `manifest`, `spine`으로 구성된다.
- `manifest`는 패키지에 포함된 파일 목록이다.
- `spine`은 문서 내부 읽기 순서를 정의한다.
- 실무 규칙상 `manifest`는 존재 확인용, `spine`은 읽기 순서용으로 분리해 다뤄야 한다.

### 5.5 `Contents/header.xml`

- 문서 전체에서 쓰이는 각종 서식과 참조 테이블의 중심이다.
- 공식 문서상 `hh:head` 하위에는 `beginNum`, `refList`, 호환성 설정, 변경 추적 관련 정보 등이 들어간다.
- 특히 `hh:refList`는 본문에서 참조하는 글꼴, 테두리, 글자 모양, 문단 모양, 스타일 정의를 담는다.

### 5.6 `Contents/sectionN.xml`

- 문서 본문이 저장되는 파일이다.
- 문서는 1개 이상의 구역(section)으로 이루어지며, 각 구역은 `section0.xml`, `section1.xml` 같은 파일로 저장된다.
- 공식 문서 기준, `header.xml`의 `secCnt` 값만큼 section 파일이 존재하는 것이 정상이다.

### 5.7 `Contents/masterpageN.xml`

- 현재 저장소 샘플에서 확인되는 머리말/꼬리말 계열 레이아웃 파트다.
- 페이지 번호, 헤더/푸터 테이블, 반복 레이아웃이 여기에 들어갈 수 있다.
- `section.xml`의 구역 설정과 결합되어 페이지별 공통 요소를 형성한다.
- 추론: 머리말/꼬리말이나 페이지 공통 장식이 중요한 템플릿에서는 `masterpage` 편집을 별도 단계로 분리해야 한다.

### 5.8 `BinData/`

- 이미지, OLE 같은 바이너리 리소스 저장소다.
- 본문 XML에는 리소스 자체가 아니라 참조 정보가 들어가고, 실제 바이너리는 `BinData/`에 들어간다.

### 5.9 `META-INF/`

- 컨테이너 주요 파일 목록과 암호화 관련 정보가 저장된다.
- 공식 문서 기준, 암호 문서인 경우 `manifest.xml`에 각 파일별 암호화 정보가 들어간다.
- 따라서 암호화된 HWPX는 단순 ZIP 파서로는 처리 불완전할 수 있다.

### 5.10 `Scripts/`

- 문서 내 스크립트 정보가 저장된다.
- 일반적인 텍스트 편집 워크플로에서는 핵심 우선순위가 낮다.

### 5.11 `Preview/`

- 탐색기 미리보기용 이미지와 텍스트가 저장된다.
- 공식 문서상 암호 문서에는 보안을 위해 저장되지 않는다.
- 추론: 문서 자체를 열 수 있는지 여부는 `Preview/`보다 `Contents/`, `META-INF/`, `mimetype`의 무결성에 더 크게 좌우된다.

## 6. 본문의 논리 구조

### 6.1 기본 계층

HWPX 본문은 대체로 다음과 같이 이해하면 된다.

```text
Document
└ Section
  └ Paragraph (hp:p)
    └ Run (hp:run)
      ├ Text (hp:t)
      ├ Picture (hp:pic)
      ├ Table (hp:tbl)
      └ 기타 컨트롤
```

### 6.2 핵심 태그

| 태그 | 의미 | 실무 해석 |
|---|---|---|
| `hp:p` | 문단 | 본문 편집의 1차 단위 |
| `hp:run` | 동일 글자 모양 구간 | 같은 문단 안의 스타일 분기 |
| `hp:t` | 텍스트 | 순수 텍스트 추출의 핵심 |
| `hp:tbl` | 표 | 구조 편집 난이도가 높은 블록 |
| `hp:tr` | 표 행 | 표 내부 순회 단위 |
| `hp:tc` | 표 셀 | 표 내부 텍스트와 서식의 실제 컨테이너 |
| `hp:pic` | 그림 | BinData와 연결되는 컨트롤 |

### 6.3 페이지와 문단의 관계

- 2차 인용 자료 기준, HWPX는 페이지를 별도 XML 파일로 쪼개기보다 문단이 순차적으로 저장되고 실제 페이지 나눔은 한/글 렌더러가 계산한다.
- 따라서 AI agent는 `페이지 번호 위치`보다 `문단 순서`와 `구역 설정`을 먼저 신뢰해야 한다.
- 추론: 레이아웃 보존이 중요한 편집에서는 텍스트 길이 변화가 페이지 넘김에 영향을 줄 수 있으므로, 구조 편집과 시각 검증을 분리해야 한다.

## 7. 참조 규칙

### 7.1 `header.xml`의 `refList`

공식 문서 예시 기준 `refList`에는 다음과 같은 테이블이 들어간다.

- `fontfaces`
- `borderFills`
- `charProperties`
- `tabProperties`
- `numberings`
- `bullets`
- `paraProperties`
- `styles`

각 그룹에는 `itemCnt`가 존재할 수 있으며, 실제 하위 원소 개수와 맞아야 한다.

### 7.2 본문과 서식의 연결 방식

- `hp:p`는 `paraPrIDRef`, `styleIDRef`로 문단/스타일을 참조한다.
- `hp:run`은 `charPrIDRef`로 글자 모양을 참조한다.
- 따라서 본문 XML만 수정하고 `header.xml`을 갱신하지 않으면, 문서는 열리더라도 서식이 깨질 수 있다.

### 7.3 section 개수와 파일 개수

- `header.xml`의 `secCnt`는 구역 수를 나타낸다.
- 정상 문서에서는 `secCnt`와 실제 `sectionN.xml` 파일 개수가 일치해야 한다.
- 새 section을 추가하거나 제거하면 `content.hpf`, `header.xml`, 실제 파일 목록을 함께 맞춰야 한다.

### 7.4 spine 순서

- 공식 문서 기준 `manifest`의 순서는 중요하지 않지만 `spine`의 순서는 중요하다.
- 따라서 AI agent는 section 파일명을 정렬한 결과보다 `spine`에 적힌 문서 순서를 우선해야 한다.

### 7.5 ID 무결성

- 2차 인용 자료 기준, `header.xml`의 각 태그는 고유 ID를 가지며 `section.xml`에서 `IDRef`로 참조된다.
- 실무 규칙상 새 서식/스타일을 추가할 때는 기존 ID와 충돌하지 않는 새 ID를 발급해야 한다.
- 실무 규칙상 삭제 시에는 참조 제거를 먼저 하고 정의를 제거해야 한다.

## 8. AI agent용 편집 규칙

### 8.1 필수 읽기 순서

1. ZIP 파일인지 확인하고 `mimetype`를 확인한다.
2. `version.xml`을 참고하되 namespace는 각 XML에서 직접 추출한다.
3. `Contents/content.hpf`를 읽어 `manifest`와 `spine`을 파악한다.
4. `Contents/header.xml`을 읽어 `refList`와 `secCnt`를 파싱한다.
5. `spine` 순서대로 `sectionN.xml`을 읽는다.
6. `paraPrIDRef`, `charPrIDRef`, `styleIDRef`를 `header.xml` 정의와 해석해 내부 IR로 올린다.

### 8.2 텍스트만 수정할 때

- 가능하면 기존 `hp:p`와 `hp:run` 구조를 유지하고 `hp:t` 텍스트만 교체한다.
- 텍스트 분절 수를 불필요하게 바꾸지 않는다.
- 스타일 변화가 필요 없으면 `header.xml`은 수정하지 않는다.
- 텍스트 길이 증가로 페이지가 밀릴 수 있으므로 결과 문서 시각 검증이 필요하다.

### 8.3 스타일을 수정할 때

- `paraPrIDRef`, `charPrIDRef`, `styleIDRef`의 대상 정의가 `header.xml`에 존재하는지 먼저 확인한다.
- 기존 정의를 직접 변경할지, 새 정의를 추가하고 참조를 바꿀지 정책을 분리한다.
- 권장: 여러 문단이 공유하는 스타일은 새 ID를 추가하는 방식이 안전하다.

### 8.4 표를 수정할 때

- 표는 `hp:tbl -> hp:tr -> hp:tc` 구조로 본다.
- 셀 텍스트도 결국 `hp:p -> hp:run -> hp:t` 계층 안에 있을 수 있으므로, 단순 문자열 치환만으로는 셀 경계가 깨질 수 있다.
- 행/열 추가 삭제는 ID, 크기, 병합, borderFill 참조까지 영향이 갈 수 있으므로 구조 편집 단계로 분류한다.

### 8.5 이미지를 수정할 때

- 바이너리 교체만으로 끝나지 않을 수 있다.
- `BinData/` 항목, `content.hpf manifest`, 본문의 그림 참조가 모두 일관되어야 한다.
- 새 이미지를 추가하면 파일 추가와 참조 추가를 함께 수행해야 한다.

### 8.6 구역을 수정할 때

- 새 `sectionN.xml` 추가 시 `header.xml secCnt`, `content.hpf manifest`, `content.hpf spine`, 실제 section 파일을 동시에 갱신한다.
- 구역 삭제 시에도 같은 항목을 역방향으로 정리한다.

### 8.7 namespace 처리

- 공식 파싱 문서 기준 namespace는 문서 버전에 따라 달라질 수 있다.
- 따라서 XPath를 하드코딩하지 말고 XML별 namespace를 먼저 추출해 사용해야 한다.

### 8.8 pretty print 주의

- 추론: 대규모 재직렬화와 pretty print는 불필요한 diff를 키우고 템플릿 parity를 해칠 수 있다.
- 특히 현재 저장소처럼 canonical template를 기준으로 엄격한 차이를 관리하는 경우, 변경 범위를 최소화하는 직렬화 전략이 유리하다.

## 9. 권장 구현 아키텍처

### 9.1 아키텍처 계층

아래처럼 기술 계층과 비즈니스 계층을 분리하는 것을 권장한다.

#### 기술 계층

- `PackageReader`
  - ZIP 열기, 필수 파일 존재 확인, `mimetype` 검증
- `NamespaceRegistry`
  - XML별 namespace 추출과 XPath 바인딩 관리
- `ManifestResolver`
  - `content.hpf`의 `manifest`와 `spine` 파싱
- `HeaderResolver`
  - `header.xml refList`, `beginNum`, `secCnt` 파싱
- `SectionParser`
  - `sectionN.xml`을 문단/표/그림 단위 IR로 변환
- `ResourceResolver`
  - `BinData`, `masterpage`, `Preview`, `Scripts` 관리
- `Validator`
  - `itemCnt`, IDRef, secCnt, manifest/spine, XML well-formedness 검증
- `Serializer`
  - 변경된 IR을 최소 diff 전략으로 XML과 ZIP에 반영

#### 비즈니스 계층

- 수학 문제 본문 삽입
- 해설/선지/번호 스타일 적용
- 평가원 양식에 맞는 문단 템플릿 치환
- 페이지 번호 정책
- 표지, 머리말, 꼬리말, 마스터페이지 정책

핵심은 "HWPX 파일 구조를 해석하는 엔진"과 "수학 OCR 산출물을 어떻게 문서화할지"를 섞지 않는 것이다.

### 9.2 현재 저장소와 연결되는 포인트

- canonical 템플릿: [style_guide.hwpx](/D:/03_PROJECT/05_mathOCR/templates/style_guide.hwpx)
- exporter 구현: [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py)
- HWPX exporter 테스트: [test_exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/tests/test_exporter.py)

이 저장소는 이미 `canonical template 유지`를 매우 중요하게 다루고 있으므로, 새 AI agent도 "XML을 예쁘게 다시 쓰는 편집기"보다 "참조 무결성을 유지하면서 필요한 노드만 바꾸는 편집기"에 가깝게 설계하는 편이 적합하다.

## 10. 예상 가능한 에러와 사용자 메시지 설계

| 에러 코드 | 상황 | 사용자 메시지 | 내부 처리 |
|---|---|---|---|
| `HWPX_NOT_ZIP` | ZIP으로 열 수 없음 | `유효한 HWPX 파일이 아닙니다.` | 업로드 중단 |
| `HWPX_MIMETYPE_INVALID` | `mimetype` 누락 또는 값 불일치 | `HWPX 포맷 시그니처가 올바르지 않습니다.` | 포맷 검증 실패 |
| `HWPX_REQUIRED_PART_MISSING` | `content.hpf`, `header.xml`, `section.xml` 등 필수 파일 누락 | `문서 필수 구성요소가 누락되어 편집할 수 없습니다.` | 누락 파일명 로그 |
| `HWPX_NAMESPACE_UNSUPPORTED` | namespace 추출 실패 또는 예상 불가 버전 | `지원하지 않는 HWPX XML 버전입니다.` | 원본 namespace 로그 |
| `HWPX_SECTION_COUNT_MISMATCH` | `secCnt`와 실제 section 파일 수 불일치 | `문서 구역 정보가 손상되었습니다.` | `secCnt`, 파일 목록 로그 |
| `HWPX_MANIFEST_SPINE_MISMATCH` | spine 참조 대상이 manifest에 없음 | `문서 내부 읽기 순서 정보가 손상되었습니다.` | spine/manifest diff 로그 |
| `HWPX_REF_BROKEN` | `charPrIDRef`, `paraPrIDRef`, `styleIDRef`가 `header.xml`에 없음 | `문서 서식 참조가 손상되었습니다.` | 끊어진 ID 로그 |
| `HWPX_ITEM_COUNT_MISMATCH` | `itemCnt`와 실제 노드 수 불일치 | `문서 서식 테이블 개수가 맞지 않습니다.` | 테이블명, 기대값, 실제값 로그 |
| `HWPX_ENCRYPTED_UNSUPPORTED` | 암호화 문서라 일반 파싱 불가 | `암호화된 HWPX 문서는 현재 지원하지 않습니다.` | 암호화 정보 로그 |
| `HWPX_XML_MALFORMED` | XML 파싱 실패 | `문서 내부 XML 구조가 올바르지 않습니다.` | 파일명, parse error 로그 |

## 11. 구현 대안

### 대안 A. 저수준 ZIP+XML 직접 편집

- 추천도: 높음
- 장점: 가장 정밀하고 현재 저장소의 canonical template 전략과 잘 맞는다.
- 단점: 구현 복잡도가 높고, 참조 무결성 검증이 필수다.
- 적합한 상황: 현재 프로젝트처럼 HWPX 출력 품질과 구조 안정성이 중요한 경우

### 대안 B. 템플릿 기반 치환 엔진

- 추천도: 높음
- 장점: 개발 비용이 낮고 레이아웃 안정성이 높다.
- 단점: 자유로운 구조 편집이 어렵다.
- 적합한 상황: 정해진 양식에 OCR 결과를 주입하는 보고서/시험지 생성

### 대안 C. 내부 IR 기반 문서 편집기

- 추천도: 중간
- 장점: 문단, 표, 그림, 수식을 공통 모델로 다룰 수 있어 기능 확장성이 높다.
- 단점: 구현 비용이 가장 높고 serializer 품질이 핵심 병목이 된다.
- 적합한 상황: 장기적으로 읽기, 비교, 병합, 자동 교정까지 포함한 플랫폼을 만들 때

### 실무 권고

- 단기: `대안 B + 필요한 부분만 대안 A` 조합이 가장 비용 대비 효율이 좋다.
- 중기: 파서와 validator를 분리한 뒤 `대안 C`로 단계적 확장하는 것이 바람직하다.

## 12. AI agent용 체크리스트

- `mimetype`가 `application/hwp+zip`인지 확인했는가
- `content.hpf`의 `manifest`와 `spine`을 모두 읽었는가
- `header.xml`의 `secCnt`와 실제 `sectionN.xml` 개수가 일치하는가
- 모든 `paraPrIDRef`, `charPrIDRef`, `styleIDRef`가 유효한가
- `itemCnt`와 실제 노드 수가 일치하는가
- 이미지/바이너리 추가 시 `BinData`와 `manifest`를 함께 갱신했는가
- masterpage를 쓰는 템플릿이면 관련 참조를 유지했는가
- 불필요한 pretty print 또는 전체 재직렬화를 피했는가
- 결과 ZIP이 다시 정상적으로 열리고 XML이 모두 well-formed인가

## 13. 결론

HWPX는 "압축을 푼 뒤 텍스트 XML을 읽으면 끝"인 단순 포맷이 아니다. 텍스트 자체는 쉽게 읽히지만, 실제 편집 가능성을 결정하는 것은 `content.hpf`, `header.xml`, `section.xml`, `BinData`, `masterpage` 사이의 참조 무결성이다.

따라서 이후 AI agent는 HWPX를 `문자열 치환 대상`이 아니라 `패키지 + 참조 그래프 + 스타일 매핑 테이블`로 다뤄야 한다. 이 기준만 지키면 현재 프로젝트의 HWPX 생성/편집 기능도 비교적 안정적으로 확장할 수 있다.

## 14. 참고 링크

- NHN Meetup 원문 URL: [https://meetup.nhncloud.com/posts/311](https://meetup.nhncloud.com/posts/311)
- 한컴 공식 구조 문서: [https://tech.hancom.com/hwpxformat/](https://tech.hancom.com/hwpxformat/)
- 한컴 공식 파싱 문서 (1): [https://tech.hancom.com/python-hwpx-parsing-1/](https://tech.hancom.com/python-hwpx-parsing-1/)
- 한컴 공식 파싱 문서 (2): [https://tech.hancom.com/python-hwpx-parsing-2/](https://tech.hancom.com/python-hwpx-parsing-2/)
- 한컴 HWP/OWPML 형식 안내: [https://www.hancom.com/support/downloadCenter/hwpOwpml](https://www.hancom.com/support/downloadCenter/hwpOwpml)
- 원문 2차 인용 자료: [https://github-wiki-see.page/m/pai-plznw4me/hwp-format-transfer/wiki/hwpx-xmlfile-%EB%B6%84%EC%84%9D](https://github-wiki-see.page/m/pai-plznw4me/hwp-format-transfer/wiki/hwpx-xmlfile-%EB%B6%84%EC%84%9D)
