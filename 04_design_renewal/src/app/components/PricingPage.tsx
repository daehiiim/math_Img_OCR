import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { motion } from "motion/react";

import { getBillingCatalogApi, type BillingPlanResponse } from "../api/billingApi";
import { cloneDefaultBillingCatalog } from "../lib/billingCatalog";
import {
  formatBillingAmount,
  formatBillingUnitPrice,
  normalizeBillingCurrency,
} from "../lib/billingCurrency";
import { isLocalUiMockEnabled } from "../lib/localUiMock";
import { Alert, AlertDescription } from "./ui/alert";
import { Skeleton } from "./ui/skeleton";
import { PageIntro } from "./shared/PageIntro";
import { PlanCard } from "./shared/PlanCard";

type PlanId = "single" | "starter" | "pro";

interface PlanDecoration {
  description: string;
  badge: string | null;
  highlight: boolean;
  features: string[];
}

interface PlanCardView extends BillingPlanResponse, PlanDecoration {
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

/** 결제 화면으로 넘길 플랜 카드 표시 정보를 계산한다. */
function buildPlanCards(catalog: BillingPlanResponse[]): PlanCardView[] {
  return [...catalog]
    .sort((left, right) => planOrder.indexOf(left.plan_id) - planOrder.indexOf(right.plan_id))
    .map((plan) => ({
      ...plan,
      ...planDecorations[plan.plan_id],
      priceLabel: formatBillingAmount(plan.amount, plan.currency),
      perImageLabel: formatBillingUnitPrice(plan.amount, plan.credits, plan.currency),
    }));
}

/** 플랜 목록을 로드해 live/fallback 표시 정책을 유지한다. */
function usePricingCatalog(isLocalUiMock: boolean) {
  const [catalog, setCatalog] = useState<BillingPlanResponse[]>(() =>
    isLocalUiMock ? fallbackCatalog : []
  );
  const [catalogLoadFailed, setCatalogLoadFailed] = useState(false);

  useEffect(() => {
    let active = true;

    const loadCatalog = async () => {
      try {
        const plans = await getBillingCatalogApi();
        if (!active) {
          return;
        }

        if (plans.length > 0) {
          setCatalog(plans);
          setCatalogLoadFailed(false);
          return;
        }

        setCatalogLoadFailed(true);
        setCatalog(isLocalUiMock ? fallbackCatalog : []);
      } catch {
        if (!active) {
          return;
        }

        setCatalogLoadFailed(true);
        setCatalog(isLocalUiMock ? fallbackCatalog : []);
      }
    };

    void loadCatalog();
    return () => {
      active = false;
    };
  }, [isLocalUiMock]);

  return { catalog, catalogLoadFailed };
}

/** 로딩 중에는 플랜 카드 스켈레톤을 렌더링한다. */
function PricingSkeletonGrid() {
  return (
    <div className="grid gap-5 md:grid-cols-3">
      {[0, 1, 2].map((item) => (
        <div key={item} className="space-y-4 rounded-xl border p-6">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-9 w-28" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ))}
    </div>
  );
}

/** 플랜 선택 화면을 shadcn 카드 패턴으로 렌더링한다. */
export function PricingPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const isLocalUiMock = isLocalUiMockEnabled();
  const { catalog, catalogLoadFailed } = usePricingCatalog(isLocalUiMock);
  const returnTo = new URLSearchParams(location.search).get("returnTo");
  const plans = useMemo(() => buildPlanCards(catalog), [catalog]);
  const isCatalogIssue = catalogLoadFailed && !isLocalUiMock;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-6xl"
    >
      <div className="space-y-8">
        <PageIntro
          title="수식 OCR 크레딧 가격 안내"
          description="MathHWP 작업실에서 필요한 수식 OCR 분량에 맞춰 크레딧 플랜을 선택하세요."
          backHref="/"
          backLabel="홈으로 돌아가기"
          align="center"
        />

        <Alert className="mx-auto max-w-2xl">
          <AlertDescription>
            실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.
          </AlertDescription>
        </Alert>

        {isCatalogIssue ? (
          <Alert className="mx-auto max-w-2xl border-amber-200 bg-amber-50 text-amber-950">
            <AlertDescription>결제 설정 점검 중</AlertDescription>
          </Alert>
        ) : null}

        {!isCatalogIssue && plans.length === 0 ? <PricingSkeletonGrid /> : null}

        {!isCatalogIssue && plans.length > 0 ? (
          <div className="grid gap-5 md:grid-cols-3">
            {plans.map((plan) => (
              <PlanCard
                key={plan.plan_id}
                title={plan.title}
                priceLabel={plan.priceLabel}
                currencyLabel={normalizeBillingCurrency(plan.currency)}
                description={plan.description}
                perImageLabel={plan.perImageLabel}
                features={plan.features}
                actionLabel="구매"
                badge={plan.badge}
                highlight={plan.highlight}
                onAction={() =>
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
              />
            ))}
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}
