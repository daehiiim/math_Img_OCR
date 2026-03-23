# 공개 홈 히어로 비디오 다크 루프 설계

## 목표

공개 홈 히어로 비디오가 `prefers-reduced-motion` 설정과 무관하게 항상 재생되도록 바꾸고, 기존의 밝은 후반 구간 대신 어두운 초반 구간만 반복 재생되게 한다.

## 현재 상태

- 비디오는 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx) 에서 데스크톱이면서 `prefers-reduced-motion: no-preference` 인 경우에만 렌더된다.
- 시작 시점은 `4.8초`, 재루프 시점은 `5.7초`로 잡혀 있어, 결과적으로 더 밝은 후반 구간만 반복된다.
- 테스트는 [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx) 에서 현재 계약을 그대로 검증한다.

## 요구사항 해석

- 사용자의 OS 감속 모드와 무관하게 비디오는 항상 재생되어야 한다.
- 밝은 부분이 아니라 어두운 부분의 영상만 계속 반복되어야 한다.
- 비디오 로드 실패 시에는 기존처럼 poster 기반 정적 폴백이 유지되어야 한다.

## 접근 방식

### 권장안

비디오 렌더 조건에서 `prefers-reduced-motion` 과 뷰포트 제한을 제거하고, 자산 로드 가능 여부만으로 비디오 렌더를 결정한다. 루프 구간은 원본 `6.0초` 영상의 프레임 밝기를 기준으로 어두운 흐름이 유지되는 초반 `0.3초 ~ 4.3초` 로 이동한다.

### 대안 1

CSS 필터만 더 어둡게 바꾸고 기존 밝은 루프 구간은 유지한다. 구현은 간단하지만, 사용자가 명시한 “어두운 부분만 반복” 요구를 만족하지 못한다.

### 대안 2

어두운 구간만 새 비디오 자산으로 잘라 재인코딩한다. 결과는 가장 깔끔하지만, 자산 관리 비용과 검증 비용이 늘어나 현재 범위에는 과하다.

## 선택 이유

권장안은 기존 자산을 유지하면서도 요구사항을 직접 충족한다. 변경 파일 수가 적고, 회귀 테스트로 계약을 고정하기 쉽다.

## 아키텍처와 비즈니스 로직 구분

### 아키텍처

- 히어로 비디오 렌더 조건을 단순화해, 클라이언트 환경 차이에 따른 불필요한 분기를 제거한다.
- 비디오 구간 제어는 `loadedmetadata` 와 `timeupdate` 이벤트 기반으로 유지해 브라우저 기본 loop 동작 위에 명시적 구간 루프를 강제한다.

### 비즈니스 로직

- 공개 홈의 첫 인상은 항상 살아 있는 배경 비디오를 유지한다.
- 반복 구간은 더 밝은 후반부가 아니라, 브랜드 톤에 맞는 어두운 초반부만 재생한다.

## 에러 처리

### 예상 가능한 에러

- 비디오 소스 로드 실패
- 브라우저가 비디오 재생을 막는 경우

### 사용자 메시지

- 두 경우 모두 사용자에게 별도 메시지는 노출하지 않는다.
- 기존 poster 배경만 남겨 레이아웃과 가독성을 유지한다.

## 테스트 전략

- 비디오가 모바일과 감속 모드에서도 렌더되는지 검증한다.
- `loadedmetadata` 이후 시작 시점이 어두운 구간으로 이동하는지 검증한다.
- `timeupdate` 에서 밝은 구간으로 진입하기 전에 다시 어두운 구간 시작점으로 되돌아가는지 검증한다.

## 배포 영향

이번 변경은 [PublicHomePage.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.tsx), [PublicHomePage.test.tsx](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/app/components/PublicHomePage.test.tsx), 필요 시 스타일 파일만 수정하는 프런트 범위다. 백엔드 API, Cloud Run, 환경 변수 변경은 없다.
