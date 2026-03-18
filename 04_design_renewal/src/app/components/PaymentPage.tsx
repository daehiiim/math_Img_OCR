import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  ExternalLink,
  Loader2,
  Lock,
  ShieldCheck,
} from "lucide-react";

import {
  createCheckoutSessionApi,
  createCustomerPortalApi,
  getBillingCatalogApi,
  getCheckoutSessionStatusApi,
  type BillingPlanResponse,
} from "../api/billingApi";
import { useAuth } from "../context/AuthContext";
import { formatBillingAmount, normalizeBillingCurrency } from "../lib/billingCurrency";
import { buildPublicAppUrl } from "../lib/publicAppUrl";

type PlanId = "single" | "starter" | "pro";

interface PaymentLocationState {
  title?: string;
  price?: string;
  amount?: number;
  currency?: string;
  credits?: number;
}

interface ResolvedPlan {
  planId: PlanId;
  title: string;
  credits: number;
  amount: number;
  currency: string;
  priceLabel: string;
}

const paymentMethods = [
  {
    id: "card",
    label: "카드 결제",
    icon: CreditCard,
    sublabel: "Visa / Mastercard / Amex",
  },
];

const fallbackCatalog: BillingPlanResponse[] = [
  { plan_id: "single", title: "Single", amount: 1000, currency: "krw", credits: 1 },
  { plan_id: "starter", title: "Starter", amount: 19000, currency: "krw", credits: 100 },
  { plan_id: "pro", title: "Pro", amount: 29000, currency: "krw", credits: 200 },
];

const terminalFailureStatuses = new Set(["canceled", "cancelled", "expired", "failed"]);

function resolvePlan(
  planIdParam: string | undefined,
  state: PaymentLocationState,
  catalog: BillingPlanResponse[]
): ResolvedPlan {
  const planId = (planIdParam as PlanId) || "starter";
  const fallbackPlan = catalog.find((plan) => plan.plan_id === planId) ?? fallbackCatalog[1];
  const amount = state.amount ?? fallbackPlan.amount;
  const currency = state.currency ?? fallbackPlan.currency;

  return {
    planId,
    title: state.title ?? fallbackPlan.title,
    credits: state.credits ?? fallbackPlan.credits,
    amount,
    currency,
    priceLabel: state.price ?? formatBillingAmount(amount, currency),
  };
}

export function PaymentPage() {
  const navigate = useNavigate();
  const { planId } = useParams();
  const location = useLocation();
  const auth = useAuth();

  const refreshProfile = auth.refreshProfile;
  const prepareLogin = auth.prepareLogin ?? (() => undefined);
  const isLoading = auth.isLoading ?? false;
  const isExplicitlyUnauthenticated = auth.isAuthenticated === false;

  const state = (location.state as PaymentLocationState) || {};

  const [catalog, setCatalog] = useState<BillingPlanResponse[]>(fallbackCatalog);
  const [selectedMethod, setSelectedMethod] = useState("card");
  const [paying, setPaying] = useState(false);
  const [checkingPayment, setCheckingPayment] = useState(false);
  const [paid, setPaid] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

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

  useEffect(() => {
    if (isLoading || !isExplicitlyUnauthenticated) {
      return;
    }

    prepareLogin(`${location.pathname}${location.search}`);
    navigate("/login");
  }, [isExplicitlyUnauthenticated, isLoading, location.pathname, location.search, navigate, prepareLogin]);

  const resolvedPlan = useMemo(
    () => resolvePlan(planId, state, catalog),
    [catalog, planId, state]
  );

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const checkoutId = params.get("checkout_id");
    const checkoutState = params.get("checkout");

    if (checkoutState === "cancel") {
      setPaymentError("결제가 취소되었습니다. 다시 시도해주세요.");
      setCheckingPayment(false);
      setStatusMessage(null);
      return;
    }

    if (!checkoutId || paid) {
      return;
    }

    let active = true;
    setCheckingPayment(true);
    setPaymentError(null);
    setStatusMessage("결제 승인 후 크레딧 반영을 확인하고 있습니다.");

    const pollCheckout = async () => {
      for (let attempt = 0; attempt < 10; attempt += 1) {
        try {
          const result = await getCheckoutSessionStatusApi(checkoutId);
          if (!active) {
            return;
          }

          if (result.credits_applied) {
            await refreshProfile();
            if (!active) {
              return;
            }

            setPaid(true);
            setCheckingPayment(false);
            setStatusMessage(null);
            return;
          }

          if (terminalFailureStatuses.has(result.status)) {
            setCheckingPayment(false);
            setPaymentError("결제가 완료되지 않았습니다. 다시 시도해주세요.");
            setStatusMessage(null);
            return;
          }

          if (attempt < 9) {
            await new Promise((resolve) => window.setTimeout(resolve, 1500));
          }
        } catch (error) {
          if (active) {
            setCheckingPayment(false);
            setStatusMessage(null);
            setPaymentError(error instanceof Error ? error.message : "결제 상태를 확인하지 못했습니다.");
          }
          return;
        }
      }

      if (active) {
        setCheckingPayment(false);
        setStatusMessage("결제는 승인되었지만 크레딧 반영을 기다리는 중입니다. 잠시 후 다시 확인해주세요.");
      }
    };

    void pollCheckout();

    return () => {
      active = false;
    };
  }, [location.search, paid, refreshProfile]);

  const handlePay = async () => {
    setPaying(true);
    setPaymentError(null);
    setStatusMessage(null);

    try {
      const successUrl = buildPublicAppUrl(
        `/payment/${resolvedPlan.planId}?checkout=success&checkout_id={CHECKOUT_ID}`
      );
      const cancelUrl = buildPublicAppUrl(`/payment/${resolvedPlan.planId}?checkout=cancel`);
      const session = await createCheckoutSessionApi({
        planId: resolvedPlan.planId,
        successUrl,
        cancelUrl,
      });
      window.location.assign(session.checkout_url);
    } catch (error) {
      setPaying(false);
      setPaymentError(error instanceof Error ? error.message : "결제 세션 생성에 실패했습니다.");
    }
  };

  const handleOpenPortal = async () => {
    setPortalLoading(true);
    setPaymentError(null);

    try {
      const result = await createCustomerPortalApi(buildPublicAppUrl(`/payment/${resolvedPlan.planId}`));
      window.location.assign(result.customer_portal_url);
    } catch (error) {
      setPortalLoading(false);
      setPaymentError(error instanceof Error ? error.message : "주문 관리 페이지를 열지 못했습니다.");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-[460px]"
    >
      <AnimatePresence mode="wait">
        {paid ? (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.35 }}
            className="flex flex-col items-center rounded-2xl border border-black/[0.04] bg-white p-10 text-center shadow-[0_2px_20px_rgba(0,0,0,0.06)]"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.15 }}
              className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50"
            >
              <CheckCircle2 className="h-8 w-8 text-emerald-600" />
            </motion.div>
            <h1 className="mb-2 text-[20px] tracking-[-0.02em] text-[#111]">
              결제가 완료되었습니다
            </h1>
            <p className="mb-1 text-[14px] text-[#71717a]">
              {resolvedPlan.credits}개의 이미지 크레딧이 계정에 반영되었습니다.
            </p>
            <p className="mt-1 text-[13px] text-[#a1a1aa]">
              영수증과 주문 내역은 Polar customer portal에서 확인할 수 있습니다.
            </p>
            <div className="mt-6 flex w-full flex-col gap-3">
              <button
                onClick={() => navigate("/workspace")}
                className="h-11 w-full cursor-pointer rounded-lg bg-[#14532d] text-[14px] text-white transition-colors hover:bg-[#0f3f22]"
              >
                워크스페이스로 이동
              </button>
              <button
                onClick={handleOpenPortal}
                disabled={portalLoading}
                className="flex h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-lg border border-[#d4d4d8] bg-white text-[14px] text-[#111] transition-colors hover:bg-[#fafafa] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {portalLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    여는 중...
                  </>
                ) : (
                  <>
                    주문/영수증 관리
                    <ExternalLink className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="form"
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2 }}
          >
            <button
              onClick={() => navigate("/pricing")}
              className="mb-6 flex cursor-pointer items-center gap-1.5 text-[13px] text-[#71717a] transition-colors hover:text-[#111]"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              가격 페이지로 돌아가기
            </button>

            <div className="mb-6">
              <h1 className="mb-1 text-[22px] tracking-[-0.02em] text-[#111]">
                결제 완료하기
              </h1>
              <p className="text-[14px] text-[#71717a]">
                Polar checkout으로 안전하게 결제됩니다.
              </p>
            </div>

            <div className="overflow-hidden rounded-2xl border border-black/[0.04] bg-white shadow-[0_2px_20px_rgba(0,0,0,0.06)]">
              <div className="border-b border-[#f4f4f5] p-6">
                <p className="mb-4 text-[11px] uppercase tracking-widest text-[#a1a1aa]">
                  주문 요약
                </p>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[14px] text-[#71717a]">플랜</span>
                  <span className="text-[14px] text-[#111]">{resolvedPlan.title}</span>
                </div>
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-[14px] text-[#71717a]">이미지</span>
                  <span className="text-[14px] text-[#111]">{resolvedPlan.credits}</span>
                </div>
                <div className="my-3 h-px bg-[#f4f4f5]" />
                <div className="flex items-center justify-between">
                  <span className="text-[15px] text-[#111]">총액</span>
                  <div className="text-right">
                    <span className="text-[18px] tracking-[-0.02em] text-[#111]">
                      {resolvedPlan.priceLabel}
                    </span>
                    <p className="text-[11px] uppercase tracking-[0.2em] text-[#a1a1aa]">
                      {normalizeBillingCurrency(resolvedPlan.currency)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="border-b border-[#f4f4f5] p-6">
                <p className="mb-4 text-[11px] uppercase tracking-widest text-[#a1a1aa]">
                  결제 수단
                </p>
                <div className="space-y-2">
                  {paymentMethods.map((method) => {
                    const Icon = method.icon;
                    const isSelected = selectedMethod === method.id;

                    return (
                      <button
                        key={method.id}
                        onClick={() => setSelectedMethod(method.id)}
                        className={`flex w-full cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition-all ${
                          isSelected
                            ? "border-[#111] bg-[#fafafa]"
                            : "border-[#e4e4e7] bg-white hover:border-[#d4d4d8]"
                        }`}
                      >
                        <div
                          className={`flex h-4 w-4 items-center justify-center rounded-full border-2 transition-colors ${
                            isSelected ? "border-[#111]" : "border-[#d4d4d8]"
                          }`}
                        >
                          {isSelected && (
                            <div className="h-2 w-2 rounded-full bg-[#111]" />
                          )}
                        </div>
                        <Icon
                          className={`h-4 w-4 ${
                            isSelected ? "text-[#111]" : "text-[#a1a1aa]"
                          }`}
                        />
                        <div className="flex-1 text-left">
                          <span className="text-[14px] text-[#3f3f46]">
                            {method.label}
                          </span>
                        </div>
                        {method.sublabel && (
                          <span className="text-[11px] text-[#a1a1aa]">
                            {method.sublabel}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="p-6">
                <button
                  onClick={handlePay}
                  disabled={paying || checkingPayment}
                  className="flex h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-[#111] text-[14px] text-white transition-all hover:bg-[#222] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {paying || checkingPayment ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      처리 중...
                    </>
                  ) : (
                    <>
                      <Lock className="h-3.5 w-3.5" />
                      지금 결제 · {resolvedPlan.priceLabel}
                    </>
                  )}
                </button>

                <div className="mt-4 flex items-center justify-center gap-1.5 text-[11px] text-[#a1a1aa]">
                  <ShieldCheck className="h-3 w-3" />
                  실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.
                </div>
                <p className="mt-2 text-center text-[11px] text-[#a1a1aa]">
                  결제가 실패하면 잔액 변경 없이 다시 시도만 요청됩니다.
                </p>
                {statusMessage && (
                  <p className="mt-3 text-center text-[12px] text-amber-700">{statusMessage}</p>
                )}
                {paymentError && (
                  <p className="mt-3 text-center text-[12px] text-rose-600">{paymentError}</p>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
