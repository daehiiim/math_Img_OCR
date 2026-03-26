# Clarity Tracker Design

## 목표

- 운영 프런트 앱인 `04_design_renewal` 전체 라우트에 Microsoft Clarity 기본 스크립트를 공통 삽입한다.
- React `StrictMode` 와 SPA 구조에서도 스크립트가 중복 삽입되지 않도록 보장한다.
- OCR, 결제, 인증 비즈니스 로직과 분리된 추적 인프라 레이어로 유지한다.

## 현재 구조

- 운영 프런트 진입점은 `04_design_renewal` 이다.
- 전역 라우트 추적은 `App.tsx` 의 `AnalyticsLayout` 에서 `GoogleAnalyticsTracker` 로 이미 처리하고 있다.
- 따라서 Clarity 역시 동일한 루트 레이아웃 계층에 두는 것이 가장 변경 범위가 작다.

## 고려한 접근안

### 1. 루트 React 트래커 컴포넌트 추가

- `ClarityTracker` 컴포넌트와 `microsoftClarity` 유틸을 분리한다.
- `AnalyticsLayout` 에서 전역으로 마운트한다.
- 장점: 중복 삽입 방지, 테스트, 추후 env 토글 추가가 쉽다.
- 권장안이다.

### 2. `index.html` 에 raw snippet 직접 삽입

- 장점: 구현이 가장 단순하다.
- 단점: 로컬 개발과 테스트 환경까지 무조건 스크립트가 로드되고, 중복 제어와 테스트가 불편하다.

### 3. 특정 페이지에서만 조건부 삽입

- 장점: 수집 범위를 최소화할 수 있다.
- 단점: 현재 요구사항인 전역 삽입과 맞지 않고, 워크스페이스 사용자 흐름이 빠질 수 있다.

## 설계 결정

- `src/app/lib/microsoftClarity.ts` 에 스크립트 URL 생성, 전역 queue 준비, 중복 삽입 방지, 테스트 리셋 함수를 둔다.
- `src/app/components/ClarityTracker.tsx` 는 `enabled`, `projectId` prop 을 받고 `useEffect` 에서 한 번만 주입한다.
- `src/app/App.tsx` 의 전역 레이아웃에서 `GoogleAnalyticsTracker` 와 함께 `ClarityTracker` 를 렌더링한다.

## 에러 처리 설계

예상 가능한 에러 목록:

- `enabled=false` 또는 project id 누락
- React `StrictMode` 로 인한 effect 중복 실행
- 이미 같은 Clarity 스크립트가 head 에 존재함
- 테스트 환경에서 외부 스크립트가 실제 로드되지 않음

사용자 전달 메시지 설계:

- 추적 스크립트 로드 실패는 사용자 기능과 무관하므로 UI 에 노출하지 않는다.
- 예외를 던지지 않고 안전하게 no-op 처리한다.

예방 규칙:

- 전역 추적 스크립트는 React `StrictMode` 기준으로 두 번 mount 되어도 DOM 삽입이 한 번만 일어나도록 `script id` 기반 중복 방지를 둔다.

## 테스트 전략

- 비활성화 상태에서는 스크립트와 전역 `window.clarity` 가 생성되지 않는지 검증한다.
- `StrictMode` 환경에서 렌더링해도 동일한 script 가 한 번만 삽입되는지 검증한다.
- queue 함수가 준비되어 스크립트 로드 전 호출도 적재되는지 검증한다.

## 배포 영향

- 백엔드 API, Cloud Run, 데이터베이스, 환경 변수 변경은 없다.
- 프런트 재배포만 필요하다.
