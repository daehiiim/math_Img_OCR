export interface BillingCatalogPlan {
  plan_id: "single" | "starter" | "pro";
  title: string;
  amount: number;
  currency: string;
  credits: number;
}

export const DEFAULT_BILLING_CATALOG: readonly BillingCatalogPlan[] = [
  { plan_id: "single", title: "Single", amount: 100, currency: "krw", credits: 1 },
  { plan_id: "starter", title: "Starter", amount: 9900, currency: "krw", credits: 100 },
  { plan_id: "pro", title: "Pro", amount: 19000, currency: "krw", credits: 200 },
];

/** fallback과 mock에서 재사용할 기본 결제 카탈로그 복사본을 만든다. */
export function cloneDefaultBillingCatalog(): BillingCatalogPlan[] {
  return DEFAULT_BILLING_CATALOG.map((plan) => ({ ...plan }));
}
