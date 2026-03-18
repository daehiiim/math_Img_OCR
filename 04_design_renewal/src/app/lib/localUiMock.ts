import { createDefaultProfile, readStoredProfile, type StoredProfile } from "./authStorage";

export type MockPaymentOutcome = "success" | "cancel" | "fail";

interface MockCheckoutRecord {
  outcome: MockPaymentOutcome;
  creditsApplied: boolean;
}

const MOCK_CHECKOUTS_KEY = "math-ocr:mock-checkouts";
const MOCK_USER_NAME = "로컬 테스트 사용자";
const MOCK_USER_EMAIL = "local-ui-mock@example.com";

export const LOCAL_UI_MOCK_AUTH_ERROR_MESSAGE =
  "로컬 UI mock 모드를 켜거나 Supabase 인증 환경값을 설정해주세요.";

export const LOCAL_UI_MOCK_BILLING_CATALOG = [
  { plan_id: "single", title: "Single", amount: 1000, currency: "krw", credits: 1 },
  { plan_id: "starter", title: "Starter", amount: 19000, currency: "krw", credits: 100 },
  { plan_id: "pro", title: "Pro", amount: 29000, currency: "krw", credits: 200 },
] as const;

// 로컬 UI mock 모드 활성 여부를 env 기준으로 판별한다.
export function isLocalUiMockEnabled(): boolean {
  return String(import.meta.env.VITE_LOCAL_UI_MOCK ?? "").toLowerCase() === "true";
}

// 저장소 접근 가능한 브라우저 환경인지 확인한다.
function canUseStorage() {
  return typeof window !== "undefined";
}

// mock checkout 저장소를 안전하게 읽는다.
function readMockCheckouts(): Record<string, MockCheckoutRecord> {
  if (!canUseStorage()) {
    return {};
  }

  const raw = window.localStorage.getItem(MOCK_CHECKOUTS_KEY);
  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw) as Record<string, MockCheckoutRecord>;
  } catch {
    return {};
  }
}

// mock checkout 저장소를 로컬 스토리지에 기록한다.
function writeMockCheckouts(records: Record<string, MockCheckoutRecord>) {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(MOCK_CHECKOUTS_KEY, JSON.stringify(records));
}

// 허용된 mock 결제 결과만 통과시키고 나머지는 success로 정규화한다.
function normalizeMockPaymentOutcome(value: string | null | undefined): MockPaymentOutcome {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (normalized === "cancel" || normalized === "fail" || normalized === "success") {
    return normalized;
  }

  return "success";
}

// 현재 페이지 쿼리와 env를 기준으로 mock 결제 결과를 결정한다.
export function resolveMockPaymentOutcome(search?: string): MockPaymentOutcome {
  const params = new URLSearchParams(search ?? globalThis.location?.search ?? "");
  const queryOutcome = params.get("mock_payment");
  if (queryOutcome) {
    return normalizeMockPaymentOutcome(queryOutcome);
  }

  return normalizeMockPaymentOutcome(import.meta.env.VITE_LOCAL_UI_MOCK_PAYMENT_OUTCOME);
}

// 로컬 테스트용 사용자 프로필을 새로 만든다.
export function createLocalUiMockProfile(): StoredProfile {
  return createDefaultProfile(MOCK_USER_NAME, MOCK_USER_EMAIL);
}

// 기존에 저장된 로컬 테스트 사용자 프로필만 읽는다.
export function readLocalUiMockProfile(): StoredProfile | null {
  return readStoredProfile(MOCK_USER_EMAIL);
}

// mock checkout ID를 로컬 테스트용 형식으로 생성한다.
function createMockCheckoutId(): string {
  const suffix = Math.random().toString(36).slice(2, 8);
  return `chk_mock_${Date.now().toString(36)}_${suffix}`;
}

// mock redirect URL에 결과와 checkout ID를 반영한다.
function buildMockCheckoutUrl(baseUrl: string, checkoutId: string, outcome: MockPaymentOutcome): string {
  const origin = globalThis.location?.origin ?? "http://localhost:5173";
  const url = new URL(baseUrl, origin);
  url.searchParams.set("checkout", outcome);
  url.searchParams.set("checkout_id", checkoutId);
  return url.toString();
}

// 플랜 ID에 대응하는 mock 카탈로그 항목을 반환한다.
function findMockPlan(planId: "single" | "starter" | "pro") {
  return LOCAL_UI_MOCK_BILLING_CATALOG.find((plan) => plan.plan_id === planId) ?? LOCAL_UI_MOCK_BILLING_CATALOG[1];
}

// mock checkout 세션을 만들고 결과를 로컬 저장소에 기록한다.
export function createLocalUiMockCheckout(payload: {
  planId: "single" | "starter" | "pro";
  successUrl: string;
  cancelUrl: string;
}) {
  const checkoutId = createMockCheckoutId();
  const outcome = resolveMockPaymentOutcome();
  const successUrl = payload.successUrl.replace("{CHECKOUT_ID}", checkoutId);
  const redirectBaseUrl = outcome === "cancel" ? payload.cancelUrl : successUrl;
  const checkoutUrl = buildMockCheckoutUrl(redirectBaseUrl, checkoutId, outcome);
  const records = readMockCheckouts();
  records[checkoutId] = { outcome, creditsApplied: false };
  writeMockCheckouts(records);

  return {
    checkout_id: checkoutId,
    checkout_url: checkoutUrl,
    ...findMockPlan(payload.planId),
  };
}

// 저장된 mock checkout 결과를 결제 상태 응답 형태로 반환한다.
export function readLocalUiMockCheckoutStatus(checkoutId: string) {
  const record = readMockCheckouts()[checkoutId];
  if (!record) {
    return {
      checkout_id: checkoutId,
      status: "failed",
      credits_applied: false,
    };
  }

  return {
    checkout_id: checkoutId,
    status: record.outcome === "cancel" ? "canceled" : record.outcome === "fail" ? "failed" : "succeeded",
    credits_applied: record.outcome === "success",
  };
}

// 성공 checkout의 크레딧 반영을 checkout ID 기준으로 한 번만 허용한다.
export function applyLocalUiMockCheckoutCredits(checkoutId: string): boolean {
  const records = readMockCheckouts();
  const record = records[checkoutId];
  if (!record) {
    records[checkoutId] = { outcome: "success", creditsApplied: true };
    writeMockCheckouts(records);
    return true;
  }

  if (record.outcome !== "success" || record.creditsApplied) {
    return false;
  }

  records[checkoutId] = { ...record, creditsApplied: true };
  writeMockCheckouts(records);
  return true;
}
