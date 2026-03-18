import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "framer-motion";
import { Check, ArrowLeft, Sparkles } from "lucide-react";

import { getBillingCatalogApi, type BillingPlanResponse } from "../api/billingApi";
import {
  formatBillingAmount,
  formatBillingUnitPrice,
  normalizeBillingCurrency,
} from "../lib/billingCurrency";

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

const fallbackCatalog: BillingPlanResponse[] = [
  { plan_id: "single", title: "Single", amount: 1000, currency: "krw", credits: 1 },
  { plan_id: "starter", title: "Starter", amount: 19000, currency: "krw", credits: 100 },
  { plan_id: "pro", title: "Pro", amount: 29000, currency: "krw", credits: 200 },
];

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
  const navigate = useNavigate();
  const [catalog, setCatalog] = useState<BillingPlanResponse[]>(fallbackCatalog);

  useEffect(() => {
    let active = true;

    const loadCatalog = async () => {
      try {
        const plans = await getBillingCatalogApi();
        if (active && plans.length > 0) {
          setCatalog(plans);
        }
      } catch {
        if (active) {
          setCatalog(fallbackCatalog);
        }
      }
    };

    void loadCatalog();

    return () => {
      active = false;
    };
  }, []);

  const plans = useMemo(() => buildPlanCards(catalog), [catalog]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-[900px]"
    >
      <button
        onClick={() => navigate("/")}
        className="mb-8 flex cursor-pointer items-center gap-1.5 text-[13px] text-[#71717a] transition-colors hover:text-[#111]"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        홈으로 돌아가기
      </button>

      <div className="mb-10 text-center">
        <h1 className="mb-2 text-[26px] tracking-[-0.02em] text-[#111]">
          이미지 구매
        </h1>
        <p className="text-[15px] text-[#71717a]">
          수학 이미지를 HWPX 문서로 즉시 변환하세요.
        </p>
        <div className="mt-4 inline-flex flex-col gap-1 rounded-2xl border border-[#ece7dd] bg-[#fbf7f1] px-5 py-3 text-[13px] text-[#6b6258]">
          <p>실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
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
                <div className="flex items-center gap-1 rounded-full bg-[#14532d] px-3 py-1 text-[11px] text-white">
                  <Sparkles className="h-3 w-3" />
                  {plan.badge}
                </div>
              </div>
            )}

            <div
              className={`flex h-full flex-col rounded-xl border p-7 transition-shadow ${
                plan.highlight
                  ? "border-[#b7d3bf] bg-[#f7fbf8] shadow-[0_10px_30px_rgba(20,83,45,0.08)]"
                  : "border-[#e4e4e7] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)]"
              }`}
            >
              <p className="mb-2 text-[13px] text-[#71717a]">{plan.title}</p>
              <div className="mb-1 flex items-baseline gap-2">
                <span className="text-[34px] tracking-[-0.03em] text-[#111]">
                  {plan.priceLabel}
                </span>
                <span className="text-[12px] uppercase tracking-[0.2em] text-[#a1a1aa]">
                  {normalizeBillingCurrency(plan.currency)}
                </span>
              </div>
              <p className="mb-2 text-[14px] text-[#52525b]">{plan.description}</p>
              <p className="mb-6 text-[13px] text-[#a1a1aa]">{plan.perImageLabel}</p>

              <button
                onClick={() =>
                  navigate(`/payment/${plan.plan_id}`, {
                    state: {
                      title: plan.title,
                      price: plan.priceLabel,
                      amount: plan.amount,
                      currency: plan.currency,
                      credits: plan.credits,
                    },
                  })
                }
                className={`mb-7 h-10 w-full cursor-pointer rounded-lg text-[14px] transition-all active:scale-[0.98] ${
                  plan.highlight
                    ? "bg-[#14532d] text-white hover:bg-[#0f3f22]"
                    : "border border-[#e4e4e7] bg-[#fafafa] text-[#111] hover:bg-[#f4f4f5]"
                }`}
              >
                구매
              </button>

              <div className="space-y-2.5 border-t border-[#f4f4f5] pt-6">
                {plan.features.map((feature) => (
                  <div key={feature} className="flex items-start gap-2">
                    <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
                    <span className="text-[13px] text-[#52525b]">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
