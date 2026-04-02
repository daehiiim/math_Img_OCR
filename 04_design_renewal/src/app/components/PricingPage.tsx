import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { motion } from "motion/react";
import { Check, ArrowLeft, Sparkles } from "lucide-react";

import { getBillingCatalogApi, type BillingPlanResponse } from "../api/billingApi";
import {
  formatBillingAmount,
  formatBillingUnitPrice,
  normalizeBillingCurrency,
} from "../lib/billingCurrency";
import { cloneDefaultBillingCatalog } from "../lib/billingCatalog";
import { isLocalUiMockEnabled } from "../lib/localUiMock";
import { Button } from "./ui/button";

type PlanId = "single" | "starter" | "pro";

interface PlanDecoration {
  description: string;
  badge: string | null;
  highlight: boolean;
  features: string[];
}

interface PlanCard extends BillingPlanResponse, PlanDecoration {
  priceLabel: string;
  perImageLabel: string;
}

const fallbackCatalog: BillingPlanResponse[] = cloneDefaultBillingCatalog();

const planDecorations: Record<PlanId, PlanDecoration> = {
  single: {
    description: "1개 이미지 변환",
    badge: null,
    highlight: false,
    features: ["1개 이미지 변환", "HWPX 내보내기", "AI OCR 처리"],
  },
  starter: {
    description: "100개 이미지",
    badge: null,
    highlight: false,
    features: ["100개 이미지 변환", "HWPX 내보내기", "AI OCR 처리", "영역 선택"],
  },
  pro: {
    description: "200개 이미지",
    badge: "가장 효율적",
    highlight: true,
    features: ["200개 이미지 변환", "HWPX 내보내기", "AI OCR 처리", "영역 선택", "우선 처리"],
  },
};

const planOrder: PlanId[] = ["single", "starter", "pro"];

function buildPlanCards(catalog: BillingPlanResponse[]): PlanCard[] {
  return [...catalog]
    .sort((left, right) => planOrder.indexOf(left.plan_id) - planOrder.indexOf(right.plan_id))
    .map((plan) => ({
      ...plan,
      ...planDecorations[plan.plan_id],
      priceLabel: formatBillingAmount(plan.amount, plan.currency),
      perImageLabel: formatBillingUnitPrice(plan.amount, plan.credits, plan.currency),
    }));
}

export function PricingPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const isLocalUiMock = isLocalUiMockEnabled();
  const [catalog, setCatalog] = useState<BillingPlanResponse[]>(() =>
    isLocalUiMock ? fallbackCatalog : []
  );
  const [catalogLoadFailed, setCatalogLoadFailed] = useState(false);
  const returnTo = new URLSearchParams(location.search).get("returnTo");

  useEffect(() => {
    let active = true;

    const loadCatalog = async () => {
      try {
        const plans = await getBillingCatalogApi();
        if (active && plans.length > 0) {
          setCatalog(plans);
          setCatalogLoadFailed(false);
          return;
        }

        if (active) {
          setCatalogLoadFailed(true);
          setCatalog(isLocalUiMock ? fallbackCatalog : []);
        }
      } catch {
        if (active) {
          setCatalogLoadFailed(true);
          setCatalog(isLocalUiMock ? fallbackCatalog : []);
        }
      }
    };

    void loadCatalog();

    return () => {
      active = false;
    };
  }, []);

  const plans = useMemo(() => buildPlanCards(catalog), [catalog]);
  const isCatalogIssue = catalogLoadFailed && !isLocalUiMock;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="liquid-page-shell liquid-page-shell--billing w-full max-w-[980px]"
    >
      <button
        onClick={() => navigate("/")}
        className="mb-8 flex cursor-pointer items-center gap-1.5 text-[13px] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        홈으로 돌아가기
      </button>

      <section
        aria-label="상단 안내 surface"
        className="liquid-frost-panel liquid-frost-panel--soft mb-10 rounded-[32px] px-6 py-8 text-center md:px-10"
      >
        <div className="mb-5 flex flex-wrap justify-center gap-2">
          <span className="liquid-chip liquid-chip--accent rounded-full px-4 py-2 text-[12px] font-medium text-foreground">
            Credits Store
          </span>
          <span className="liquid-chip rounded-full px-4 py-2 text-[12px] text-foreground/72">
            Polar checkout
          </span>
        </div>
        <h1 className="mb-2 text-[26px] tracking-[-0.02em] text-foreground">이미지 구매</h1>
        <p className="mx-auto max-w-[560px] text-[15px] leading-relaxed text-muted-foreground">
          수학 이미지를 HWPX 문서로 즉시 변환하고, 필요한 크레딧만 가볍게 충전할 수 있습니다.
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <div className="liquid-inline-note rounded-[24px] px-5 py-4 text-left">
            <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              Checkout Guide
            </p>
            <p className="mt-2 text-[14px] leading-relaxed text-foreground/82">
              실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.
            </p>
          </div>
          <div className="liquid-inline-note rounded-[24px] px-5 py-4 text-left">
            <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              Catalog Currency
            </p>
            <p className="mt-2 text-[14px] leading-relaxed text-foreground/82">
              KRW catalog 기준으로 패키지 가격과 이미지 단가를 먼저 확인합니다.
            </p>
          </div>
        </div>
        {isCatalogIssue && (
          <p className="mt-3 text-[13px] text-amber-700">결제 설정 점검 중</p>
        )}
      </section>

      <section aria-label="plan surface" className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {!isCatalogIssue && plans.length === 0 ? (
          <div className="liquid-frost-panel rounded-[28px] p-7 text-[14px] text-muted-foreground md:col-span-3">
            플랜 정보를 불러오는 중입니다.
          </div>
        ) : null}
        {plans.map((plan, index) => (
          <motion.div
            key={plan.plan_id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.4,
              delay: index * 0.08,
              ease: [0.25, 0.46, 0.45, 0.94],
            }}
            className="relative"
          >
            {plan.badge && (
              <div className="absolute left-1/2 top-0 z-10 -translate-x-1/2 -translate-y-1/2">
                <div className="liquid-chip liquid-chip--accent flex items-center gap-1 rounded-full px-3 py-1 text-[11px] text-foreground">
                  <Sparkles className="h-3 w-3" />
                  {plan.badge}
                </div>
              </div>
            )}

            <div
              className={`liquid-frost-panel flex h-full flex-col rounded-[28px] p-7 transition-shadow ${
                plan.highlight
                  ? "liquid-frost-panel--accent"
                  : "liquid-frost-panel--soft hover:-translate-y-0.5"
              }`}
            >
              <p className="mb-2 text-[13px] text-muted-foreground">{plan.title}</p>
              <div className="mb-1 flex items-baseline gap-2">
                <span className="text-[34px] tracking-[-0.03em] text-foreground">
                  {plan.priceLabel}
                </span>
                <span className="text-[12px] uppercase tracking-[0.2em] text-muted-foreground">
                  {normalizeBillingCurrency(plan.currency)}
                </span>
              </div>
              <p className="mb-2 text-[14px] text-foreground/80">{plan.description}</p>
              <p className="mb-6 text-[13px] text-muted-foreground">{plan.perImageLabel}</p>

              <Button
                onClick={() =>
                  navigate(
                    `/payment/${plan.plan_id}${
                      returnTo ? `?returnTo=${encodeURIComponent(returnTo)}` : ""
                    }`,
                    {
                      state: {
                        title: plan.title,
                        price: plan.priceLabel,
                        amount: plan.amount,
                        currency: plan.currency,
                        credits: plan.credits,
                      },
                    }
                  )
                }
                disabled={isCatalogIssue}
                variant={plan.highlight ? "default" : "glass"}
                size="pill"
                className={`mb-7 w-full text-[14px] ${
                  isCatalogIssue
                    ? "cursor-not-allowed opacity-55"
                    : ""
                }`}
              >
                구매
              </Button>

              <div className="space-y-2.5 border-t border-white/55 pt-6">
                {plan.features.map((feature) => (
                  <div key={feature} className="flex items-start gap-2">
                    <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#4da3ff]" />
                    <span className="text-[13px] text-foreground/80">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        ))}
      </section>
    </motion.div>
  );
}
