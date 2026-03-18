# 경쟁사 윈도우 한글 자동화 방식 비교 및 역설계 판단 보고서

## 1. 핵심 요약

### 결론
- `문서 편집기 레이어`만 비교하면 윈도우 한글 직접 자동화가 더 쉽다.
- `서비스 전체 레이어`까지 포함하면 현재 저장소와 정합적인 선택은 `웹 유지 + HWPX 지속`이다.
- 이번 단계의 최종 권장안은 `웹 유지 + 현재 HWPX 파이프라인 강화`다.
- `.hwp` 원본 편집 정밀도가 사업 핵심 요구가 되면 `윈도우 보조 워커`를 별도 추가하는 하이브리드 구성이 가장 현실적이다.

### 범위
- 분석 범위는 공개 저장소, 현재 코드, 공개 문서, 공개 라이브러리 문서까지로 제한한다.
- 바이너리 크래킹, 패킷 탈취, EULA 위반 가능 행위는 범위 밖이다.
- 이번 단계는 분석과 계획만 수행하며 코드 변경에 따른 재배포는 없다.

### 판단 기준
- 편집 품질
- 운영 복잡도
- 배포 자동화
- 병렬 처리와 확장성
- 라이선스 및 운영체제 종속성
- 역설계 가능 범위

---

## 2. 현재 저장소 기준 사실

### 아키텍처
- 현재 백엔드는 FastAPI 기반 웹 SaaS이며, 공개 HWPX 내보내기 API는 `POST /jobs/{job_id}/export/hwpx` 와 다운로드 엔드포인트로 고정되어 있다. 근거: [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py):267, [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py):398
- 내보내기 실행은 완료된 job을 임시 디렉터리에 물질화한 뒤 HWPX를 생성해 storage에 업로드하는 구조다. 근거: [orchestrator.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/orchestrator.py):302
- 현재 HWPX 런타임은 외부 윈도우 한글 엔진이 아니라 vendored runtime bundle을 기본 사용한다. 근거: [README.md](/D:/03_PROJECT/05_mathOCR/02_main/README.md):16, [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):80
- exporter는 base 템플릿을 복사한 뒤 `section0.xml`, `content.hpf`, `header.xml`, `BinData`를 직접 조립한다. 근거: [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):50, [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):62, [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):245, [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):434, [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):454

### 비즈니스 로직
- OCR 단계는 이미지 영역을 분석해 텍스트, 수식, 도형을 JSON으로 반환하도록 GPT 계열 모델에 직접 요청한다. 근거: [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):182
- 수식은 LaTeX가 아니라 `Hancom Office Equation Script`로 강제하고 `<math>...</math>` 태그로 감싸도록 지시한다. 근거: [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):214
- exporter는 `<math>` 토큰을 분리해 HWPX equation run으로 변환한다. 근거: [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):219
- 이미지 삽입은 현재 SVG 원본을 편집 가능한 개체로 넣는 방식이 아니라 `png_rendered_url` 또는 `crop_url`을 `BinData`로 복사해 그림 문단으로 넣는 방식이다. 근거: [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):322, [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):347

### 이 사실이 의미하는 것
- 현재 저장소는 `한글 애플리케이션 자동화기`가 아니라 `웹 기반 OCR + HWPX XML 조립기`에 가깝다.
- 따라서 경쟁사 코드가 윈도우 한글 직접 자동화라면, 차이는 OCR 품질보다도 `문서 작성기 레이어`에서 가장 크게 난다.
- 반대로 현재 저장소는 운영 자동화, 배포, 확장성 축에서 이미 유리한 출발점을 갖고 있다.

---

## 3. 경쟁사 코드 조각의 추정 레이어

경쟁사 조각은 아래 4개 레이어로 분해해 보는 것이 가장 설명력이 높다.

| 레이어 | 추정 책임 | 현재 저장소 대응 |
| --- | --- | --- |
| OCR/도형 추출 | 이미지에서 텍스트, 수식, 도형 분리 | [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):195 |
| 수식 정규화 | 한글 수식 스크립트로 변환 | [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):214 |
| 문서 DSL | `insert_text`, `insert_equation`, `insert_generated_image`, `insert_template`, `focus_placeholder` 같은 명령 집합 | 현재는 명시적 DSL 대신 exporter 함수군으로 분산 |
| 한글 실행기 | COM 또는 COM 래퍼로 실제 문서에 반영 | 현재 저장소에는 없음 |

### 중요한 보정 1
- `insert_equation`, `insert_generated_image`는 현재 저장소 기능과 강하게 매핑된다.
- 하지만 `insert_table`과 `focus_placeholder`는 현재 저장소에서 직접 확인되는 구현이 아니다.
- 즉, 사용자가 제시한 `insert_template + focus_placeholder ↔ 현재 템플릿 + 필드/누름틀 이동 방식`은 경쟁사 쪽 추정으로는 타당하지만, 현재 저장소 근거로는 `템플릿 파일 사용`까지만 사실이고 `필드 이동`은 아직 확인되지 않았다.

### 중요한 보정 2
- 현재 exporter는 이미지를 그림으로 넣지만, 윈도우 한글 자동화기는 표, 누름틀, 컨트롤, 수식 객체를 한글 내부 모델에 직접 생성할 수 있다.
- 따라서 최종 편집 가능성만 놓고 보면 경쟁사 방식이 우위일 가능성이 높다.

---

## 4. 라이브러리 추정

### 1순위 추정
- `Hancom COM 직접 호출`
- `pyhwpx 같은 COM 래퍼`

이 추정이 가장 강한 이유는 공개 문서상 `pyhwpx`가 아래 패턴을 모두 제공하기 때문이다.

- `insert_text`
- `create_table`
- `move_to_field`
- `put_field_text`
- `import_mathml`
- HwpAutomation API를 `pywin32` 기반으로 래핑

외부 근거:
- [pyhwpx Core](https://martiniifun.github.io/pyhwpx/core.html)
- [pyhwpx PyPI](https://pypi.org/project/pyhwpx/)

### 외부 문서에서 읽히는 사실
- `pyhwpx`는 Windows 환경과 한글 설치를 전제로 한다.
- PyPI 설명에는 `HwpAutomation API`를 `pywin32`로 래핑한다고 적혀 있다.
- Core 문서에는 `insert_text`, `create_table`, `move_to_field`, `put_field_text`, `import_mathml` 같은 메서드가 노출되어 있다.

### 추론
- 경쟁사 코드가 `insert_template`, `focus_placeholder`, `insert_equation`, `insert_generated_image` 같은 명령을 보인다면, 내부 구현은 직접 COM 호출이거나 pyhwpx 류 얇은 래퍼일 가능성이 높다.
- 다만 이것은 `라이브러리 추정`이지 `확정`이 아니다.
- 같은 형태의 DSL은 자체 래퍼 위에 직접 COM dispatch를 올려도 만들 수 있다.

---

## 5. 비교 판단

### 5.1 문서 편집기 레이어

| 항목 | 웹 + HWPX 조립 | 윈도우 한글 자동화 |
| --- | --- | --- |
| 표/누름틀/컨트롤 | 직접 XML 설계 필요 | 한글 엔진 기능 위임 가능 |
| 페이지 레이아웃 정합성 | 템플릿과 XML 조립 품질에 좌우 | 실제 한글 렌더러와 높은 일치 |
| 수식 객체화 | `<math>`를 HWPX equation run으로 변환 | 한글 수식 입력 API 직접 사용 가능 |
| 최종 편집성 | 구조화는 가능하나 세부 편집은 상대적으로 제한 | 사용자가 한글에서 바로 수정하기 쉬움 |
| 구현 난이도 | 포맷 학습비용 큼 | 문서 편집만 보면 더 쉬움 |

판단:
- 이 레이어만 보면 윈도우 한글 자동화가 더 쉽고 직관적이다.

### 5.2 서비스 전체 레이어

| 항목 | 웹 + HWPX 조립 | 윈도우 한글 자동화 |
| --- | --- | --- |
| 운영체제 종속 | 낮음 | 매우 높음 |
| 서버 세션 안정성 | 상대적으로 높음 | GUI, COM 세션, 권한 이슈 가능 |
| 병렬 처리 | 작업 큐 확장 용이 | 한글 프로세스 수평 확장 부담 큼 |
| 배포 자동화 | 컨테이너 친화적 | Windows 전용 런타임 관리 필요 |
| 라이선스/설치 | 단순 | 한글 설치와 라이선스 고려 필요 |
| 관측성과 복구 | 웹 파이프라인 로깅 용이 | 앱 자동화 장애 분석 난도 높음 |
| 보안 표면 | 상대적으로 좁음 | 파일 시스템, GUI, COM, 템플릿 의존 증가 |

판단:
- 서비스 전체로 보면 `웹 + HWPX`가 더 낫다.

### 5.3 비즈니스 로직 레이어

| 항목 | 현재 저장소 | 윈도우 자동화가 유리한 경우 |
| --- | --- | --- |
| 시험지 번호/본문/해설 | 이미 구현 가능 | 큰 차이 없음 |
| 이미지 삽입 | 현재 가능 | 배치 정밀도가 더 필요할 때 유리 |
| 템플릿 기반 작성 | base 템플릿 bundle 기반 | 필드/누름틀 중심 템플릿이 필요할 때 유리 |
| 벡터 도형 최종 편집 | 현재 export는 이미지 중심 | 도형을 최종 문서에서 수정해야 하면 유리 |

판단:
- 현재 SaaS의 핵심 가치가 `자동 생성 후 다운로드`라면 웹 구조가 맞다.
- 핵심 가치가 `한글 문서 원본을 사람이 매우 세밀하게 후편집`하는 것이라면 윈도우 보조 워커가 실용적이다.

---

## 6. 역설계 가능한 것과 불가능한 것

### 가능한 것
- 문서 조립 명령 체계의 존재
- 수식 포맷이 한글 수식 스크립트 계열일 가능성
- 템플릿 파일 + 필드/placeholder 기반 작성 방식일 가능성
- 최종 실행기가 윈도우 한글 COM 계열일 가능성
- 서비스가 `OCR/수식/문서작성기`를 분리한 파이프라인 구조일 가능성

### 불가능한 것
- 실제 OCR 엔진 모델명
- 프롬프트 원문
- 후처리 규칙 세부
- 페이지네이션 규칙 전부
- 스타일 템플릿 원본
- 이미지 생성 엔진 종류
- 예외 처리 정책과 QA 기준

### 이유
- 현재 저장소는 prompt와 모델명이 코드에 명시되어 있어서 내부를 읽으면 알 수 있다. 근거: [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):189, [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):195
- 반대로 경쟁사 코드 조각만으로는 `문서 DSL` 일부만 보일 뿐 그 위의 모델 선택, 프롬프트, 템플릿 자산, QA 정책은 보이지 않는다.

---

## 7. 권장 아키텍처 3안

### 권장: 웹 유지 + 현재 HWPX 파이프라인 강화

#### 아키텍처
- 현재 공개 API를 유지한다.
- exporter 내부 품질만 높인다.
- 수식/도형/템플릿 조립 규칙을 점진적으로 강화한다.

#### 비즈니스 로직
- 문제 번호, 배점, 해설, 선택지, 이미지 삽입 규칙을 HWPX 생성기 안에서 표준화한다.
- 필요한 경우 템플릿 종류를 늘리되 공개 API는 그대로 둔다.

#### 장점
- 재배포/운영 비용이 가장 낮다.
- 현재 저장소와 가장 정합적이다.
- 병렬 처리와 CI/CD 친화성이 높다.

#### 단점
- `.hwp` 원본 편집 품질은 직접 자동화보다 불리할 수 있다.
- 표/누름틀/복잡한 페이지 레이아웃은 구현 비용이 누적된다.

### 대안 1: 웹 유지 + 내부 전용 윈도우 작성 워커 추가

#### 아키텍처
- 외부 API는 그대로 유지한다.
- 내부에서 `DocumentWriter` 추상화를 두고 `HwpxXmlWriter`와 `WindowsHancomWriter`를 분리한다.
- 특정 템플릿 또는 고정밀 `.hwp` 작업만 윈도우 워커로 보낸다.

#### 비즈니스 로직
- 일반 문서는 기존 HWPX writer를 사용한다.
- 누름틀, 표, 세밀한 편집이 필요한 템플릿만 Windows writer를 사용한다.

#### 장점
- 품질과 운영성의 균형이 가장 좋다.
- 비용 증가를 제한하면서 정밀 편집만 확보할 수 있다.

#### 단점
- 운영 복잡도가 증가한다.
- 템플릿과 writer 간 정합성 테스트가 필요하다.

### 대안 2: 전체를 윈도우 앱 중심으로 전환

#### 아키텍처
- 문서 작성 핵심을 한글 자동화기로 옮긴다.
- 웹은 업로드와 작업 큐만 담당하고 산출물 생성은 사실상 Windows 앱에 의존한다.

#### 비즈니스 로직
- 문서 템플릿, 필드 이동, 표/수식/그림 삽입 규칙 대부분이 한글 엔진 종속이 된다.

#### 장점
- 편집 품질과 최종 문서 정합성이 가장 높을 수 있다.

#### 단점
- SaaS 확장성, 병렬 처리, 배포 자동화, 운영 비용 면에서 가장 불리하다.
- 한글 설치, 라이선스, 세션 안정성이 모두 운영 리스크가 된다.

---

## 8. 명령 매핑 검증

| 경쟁사 명령 | 현재 저장소 대응 | 판단 |
| --- | --- | --- |
| `insert_equation` | `<math>` 입력 후 HWPX equation run 생성 | 강하게 매핑됨 |
| `insert_generated_image` | region 이미지 `BinData` 삽입 | 강하게 매핑됨 |
| `insert_template` | base 템플릿 bundle 복사 | 부분 매핑 |
| `focus_placeholder` | 현재 저장소에서 직접 근거 없음 | 경쟁사 전용 패턴으로 추정 |
| `insert_table` | 현재 exporter에 직접 구현 근거 없음 | 미매핑 |

이 표에서 중요한 결론은 두 가지다.
- 경쟁사 문서 DSL 전체를 현재 저장소 기능과 `1:1 동일`하다고 보면 과해석이다.
- 하지만 `수식`, `이미지`, `템플릿 기반 작성`이라는 큰 흐름은 충분히 같은 계열로 볼 수 있다.

---

## 9. 후속 PoC 제안

### 아키텍처
- 공개 API는 그대로 유지한다.
- 내부적으로 `DocumentWriter` 추상화를 만든다.
- 구현체는 `HwpxXmlWriter` 와 `WindowsHancomWriter` 두 개로 분리한다.

### 비즈니스 로직
- writer 입력 DTO는 문제 번호, 본문, 수식, 이미지, 해설, 템플릿 슬롯, 선택지를 공통 구조로 만든다.
- 템플릿 이름과 placeholder 이름은 writer 구현 바깥에서 결정한다.

### 설계 원칙
- `/jobs/{job_id}/export/hwpx` API 유지
- 템플릿/placeholder 명세를 writer 인터페이스 바깥으로 분리
- writer별 실패 원인을 사용자 메시지와 내부 로그 코드로 분리

---

## 10. 예상 가능한 에러와 사용자 메시지

### 예상 가능한 에러 목록
- 한글 미설치 또는 COM 등록 실패
- 서버 세션에서 GUI 또는 권한 문제
- 템플릿 파일 누락
- placeholder 또는 필드 이름 불일치
- 수식 스크립트 파싱 실패
- 이미지 경로 누락
- 임시 파일 정리 충돌
- writer 타임아웃 또는 프로세스 hang

### 사용자 메시지 기본안
- `한글 자동화 환경이 준비되지 않았습니다. 한글 설치 및 COM 사용 가능 여부를 확인해 주세요.`
- `문서 템플릿을 찾지 못했습니다. 템플릿 경로 또는 placeholder 이름을 확인해 주세요.`
- `수식 변환에 실패했습니다. 원본 수식 또는 OCR 결과를 검토해 주세요.`
- `이미지 삽입에 실패했습니다. 이미지 경로와 임시 파일 상태를 확인해 주세요.`
- `문서 생성 시간이 제한을 초과했습니다. 잠시 후 다시 시도해 주세요.`

### 설계 주의사항
- 내부 예외 메시지를 그대로 사용자에게 노출하면 안 된다.
- 사용자 메시지는 한국어 고정 문구로 표준화하고, 상세 원인은 서버 로그와 job 메타데이터에 남겨야 한다.
- 현재 exporter도 runtime 누락, validation 실패, API 오류를 문자열로 바로 올리는 구조가 있으므로, Windows writer 도입 시에는 오류 코드 체계를 함께 정리하는 것이 좋다. 근거: [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):58, [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):92, [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):282

---

## 11. 최종 판단

### 아키텍처 판단
- 기본 추천은 `웹 유지 + HWPX 지속`이다.
- 이유는 현재 저장소 구조, 배포 방식, 병렬 처리, 운영 자동화와 가장 잘 맞기 때문이다.

### 비즈니스 로직 판단
- `.hwp` 원본 후편집 정밀도가 사업의 핵심 KPI가 아니면 현재 구조를 버릴 이유가 약하다.
- 반대로 표, 누름틀, 정교한 페이지 배치, 한글 내부 편집성이 매출에 직접 연결되면 `윈도우 보조 워커` 검토가 타당하다.

### 재배포 영향
- 이번 단계는 문서 작성만 수행했으므로 재배포는 불필요하다.
- 다만 후속 PoC에서 writer 추상화나 Windows worker를 실제 구현하면 백엔드 재배포가 필요하다.

---

## 12. 참고 근거

### 저장소 근거
- [multi_problem_ocr_vector_hwp_plan_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/multi_problem_ocr_vector_hwp_plan_ko.md):47
- [multi_problem_ocr_vector_hwp_plan_ko.md](/D:/03_PROJECT/05_mathOCR/02_main/docs/multi_problem_ocr_vector_hwp_plan_ko.md):53
- [README.md](/D:/03_PROJECT/05_mathOCR/02_main/README.md):16
- [extractor.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/extractor.py):214
- [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):44
- [exporter.py](/D:/03_PROJECT/05_mathOCR/02_main/app/pipeline/exporter.py):219
- [main.py](/D:/03_PROJECT/05_mathOCR/02_main/app/main.py):267

### 외부 근거
- [pyhwpx Core](https://martiniifun.github.io/pyhwpx/core.html)
- [pyhwpx PyPI](https://pypi.org/project/pyhwpx/)
