import { browserSupabase } from "../lib/supabase";
import { buildApiUrl } from "./apiBase";

export interface BillingProfileResponse {
  credits_balance: number;
  used_credits: number;
  openai_connected: boolean;
  openai_key_masked?: string | null;
}

export interface BillingPlanResponse {
  plan_id: "single" | "starter" | "pro";
  title: string;
  amount: number;
  currency: string;
  credits: number;
}

export interface BillingCheckoutResponse {
  checkout_id: string;
  checkout_url: string;
  plan_id: string;
  credits: number;
  amount: number;
  currency: string;
}

export interface BillingCheckoutStatusResponse {
  checkout_id: string;
  status: string;
  credits_applied: boolean;
}

async function buildRequestHeaders(initHeaders?: HeadersInit): Promise<Headers> {
  const headers = new Headers(initHeaders);
  const session = browserSupabase ? await browserSupabase.auth.getSession() : null;
  const accessToken = session?.data.session?.access_token;

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

function mapBillingDetailToMessage(detail: string): string {
  if (detail === "OPENAI_KEY_ENCRYPTION_SECRET is not configured") {
    return "OpenAI 개인 키 저장을 위해 서버의 OPENAI_KEY_ENCRYPTION_SECRET 설정이 필요합니다.";
  }
  if (detail === "POLAR_ACCESS_TOKEN is not configured") {
    return "결제를 위해 서버의 POLAR_ACCESS_TOKEN 설정이 필요합니다.";
  }
  if (detail === "POLAR_SERVER must be production for live billing") {
    return "운영 결제를 사용하려면 서버의 POLAR_SERVER 값을 production으로 설정해야 합니다.";
  }
  if (detail === "POLAR_ACCESS_TOKEN does not match POLAR_SERVER") {
    return "Polar 운영 토큰이 현재 POLAR_SERVER 설정과 맞지 않습니다. 설정 값을 다시 확인해 주세요.";
  }
  if (detail.startsWith("missing Polar product ids:")) {
    return "결제 상품 설정이 누락되었습니다. 서버의 Polar 상품 ID를 확인해 주세요.";
  }
  if (detail === "Polar gateway is not configured") {
    return "결제 서버 설정이 아직 완료되지 않았습니다. 관리자 설정을 확인해 주세요.";
  }
  return detail;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = buildApiUrl(path);
  const headers = await buildRequestHeaders(init?.headers);
  let response: Response;

  try {
    response = await fetch(url, {
      ...init,
      headers,
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    throw new Error(`API 연결 실패 (${url}): ${reason}`);
  }

  if (!response.ok) {
    const text = await response.text();
    let message = text || `HTTP ${response.status}`;

    try {
      const parsed = JSON.parse(text) as { detail?: string };
      if (typeof parsed.detail === "string") {
        message = mapBillingDetailToMessage(parsed.detail);
      }
    } catch {
      // JSON이 아닌 에러 응답은 그대로 둔다.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function getBillingProfileApi(): Promise<BillingProfileResponse> {
  return requestJson<BillingProfileResponse>("/billing/profile", { method: "GET" });
}

export async function saveOpenAiKeyApi(apiKey: string): Promise<BillingProfileResponse> {
  return requestJson<BillingProfileResponse>(
    "/billing/openai-key",
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey }),
    }
  );
}

export async function deleteOpenAiKeyApi(): Promise<BillingProfileResponse> {
  return requestJson<BillingProfileResponse>("/billing/openai-key", { method: "DELETE" });
}

export async function getBillingCatalogApi(): Promise<BillingPlanResponse[]> {
  const response = await requestJson<{ plans: BillingPlanResponse[] }>("/billing/catalog", { method: "GET" });
  return response.plans;
}

export async function createCheckoutSessionApi(payload: {
  planId: "single" | "starter" | "pro";
  successUrl: string;
  cancelUrl: string;
}) {
  return requestJson<BillingCheckoutResponse>(
    "/billing/checkout",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan_id: payload.planId,
        success_url: payload.successUrl,
        cancel_url: payload.cancelUrl,
      }),
    }
  );
}

export async function getCheckoutSessionStatusApi(checkoutId: string) {
  return requestJson<BillingCheckoutStatusResponse>(
    `/billing/checkout/${checkoutId}`,
    { method: "GET" }
  );
}

export async function createCustomerPortalApi(returnUrl?: string) {
  const search = returnUrl ? `?return_url=${encodeURIComponent(returnUrl)}` : "";
  return requestJson<{ customer_portal_url: string }>(`/billing/portal${search}`, { method: "GET" });
}
