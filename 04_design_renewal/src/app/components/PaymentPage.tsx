import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, CreditCard, ExternalLink, Loader2, Lock, ShieldCheck } from "lucide-react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import {
  createCheckoutSessionApi,
  createCustomerPortalApi,
  getBillingCatalogApi,
  getCheckoutSessionStatusApi,
  type BillingPlanResponse,
} from "../api/billingApi";
import { useAuth } from "../context/AuthContext";
import { cloneDefaultBillingCatalog } from "../lib/billingCatalog";
import { formatBillingAmount, normalizeBillingCurrency } from "../lib/billingCurrency";
import { applyLocalUiMockCheckoutCredits, isLocalUiMockEnabled } from "../lib/localUiMock";
import { buildPublicAppUrl } from "../lib/publicAppUrl";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";
import { PageIntro } from "./shared/PageIntro";
import { CheckoutSummaryCard } from "./shared/CheckoutSummaryCard";
import { PaymentMethodSelector } from "./shared/PaymentMethodSelector";

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

const fallbackCatalog: BillingPlanResponse[] = cloneDefaultBillingCatalog();
const terminalFailureStatuses = new Set(["canceled", "cancelled", "expired", "failed"]);

const paymentMethods = [
  {
    id: "card",
    label: "카드 결제",
    icon: CreditCard,
    sublabel: "Visa / Mastercard / Amex",
  },
];

/** 결제 이후 되돌아갈 경로를 유지한 결제 URL을 만든다. */
function buildPaymentRoute(
  planId: PlanId,
  options: { checkout?: "success" | "cancel"; returnTo?: string | null } = {}
): string {
  const params = new URLSearchParams();
  if (options.checkout) params.set("checkout", options.checkout);
  if (options.returnTo) params.set("returnTo", options.returnTo);
  const query = params.toString();
  return query ? `/payment/${planId}?${query}` : `/payment/${planId}`;
}

/** location state와 catalog를 합쳐 현재 플랜 표시 정보를 계산한다. */
function resolvePlan(
  planIdParam: string | undefined,
  state: PaymentLocationState,
  catalog: BillingPlanResponse[],
  allowFallbackCatalog: boolean
): ResolvedPlan {
  const planId = (planIdParam as PlanId) || "starter";
  const catalogPlan = catalog.find((plan) => plan.plan_id === planId);
  const fallbackPlan = catalogPlan ?? (allowFallbackCatalog ? fallbackCatalog.find((plan) => plan.plan_id === planId) ?? fallbackCatalog[1] : null);
  const amount = state.amount ?? fallbackPlan?.amount ?? 0;
  const currency = state.currency ?? fallbackPlan?.currency ?? "krw";

  return {
    planId,
    title: state.title ?? fallbackPlan?.title ?? "상품 정보 확인 중",
    credits: state.credits ?? fallbackPlan?.credits ?? 0,
    amount,
    currency,
    priceLabel: state.price ?? (amount > 0 ? formatBillingAmount(amount, currency) : "확인 중"),
  };
}

/** live/mock 결제 카탈로그를 동일한 정책으로 로드한다. */
function usePaymentCatalog(isLocalUiMock: boolean) {
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

/** 결제 완료 후 이동 CTA와 portal 액션을 렌더링한다. */
function PaymentSuccessState({
  isLocalUiMock,
  portalLoading,
  returnTo,
  onOpenPortal,
}: {
  isLocalUiMock: boolean;
  portalLoading: boolean;
  returnTo: string | null;
  onOpenPortal: () => void;
}) {
  return (
    <Card className="mx-auto w-full max-w-xl">
      <CardContent className="space-y-6 pt-6 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-600"><CheckCircle2 className="size-8" /></div>
        <PageIntro title="결제가 완료되었습니다" description="결제 승인 후 크레딧 반영까지 정상적으로 확인되었습니다." align="center" />
        <Alert><AlertDescription>{isLocalUiMock ? "mock 모드에서는 주문/영수증 포털을 제공하지 않습니다." : "영수증과 주문 내역은 Polar customer portal에서 확인할 수 있습니다."}</AlertDescription></Alert>
        <div className="flex flex-col gap-3">
          <Button asChild><Link to={returnTo || "/workspace"}>{returnTo ? "이전 화면으로 이동" : "워크스페이스로 이동"}</Link></Button>
          <Button type="button" variant="outline" disabled={portalLoading || isLocalUiMock} onClick={onOpenPortal}>
            {portalLoading ? <><Loader2 className="animate-spin" />여는 중...</> : <>주문/영수증 관리<ExternalLink data-icon="inline-end" /></>}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/** 결제 전 요약, 수단 선택, CTA를 공통 카드 조합으로 렌더링한다. */
function PaymentCheckoutState({
  priceBackHref,
  resolvedPlan,
  selectedMethod,
  onMethodChange,
  payButtonDisabled,
  payLabel,
  isCatalogIssue,
  isCatalogPending,
  statusMessage,
  paymentError,
  onPay,
}: {
  priceBackHref: string;
  resolvedPlan: ResolvedPlan;
  selectedMethod: string;
  onMethodChange: (value: string) => void;
  payButtonDisabled: boolean;
  payLabel: string;
  isCatalogIssue: boolean;
  isCatalogPending: boolean;
  statusMessage: string | null;
  paymentError: string | null;
  onPay: () => void;
}) {
  return (
    <div className="space-y-6">
      <PageIntro title="결제 완료하기" description="Polar checkout으로 안전하게 결제됩니다." backHref={priceBackHref} backLabel="가격 페이지로 돌아가기" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <CheckoutSummaryCard title={resolvedPlan.title} credits={resolvedPlan.credits} priceLabel={resolvedPlan.priceLabel} currencyLabel={normalizeBillingCurrency(resolvedPlan.currency)} description="결제 직전 주문 요약과 통화를 다시 확인하세요." />
        <PaymentMethodSelector value={selectedMethod} options={paymentMethods} onValueChange={onMethodChange} description="현재는 카드 결제만 지원합니다." />
      </div>
      <Card>
        <CardContent className="space-y-4 pt-6">
          <Button type="button" className="w-full" disabled={payButtonDisabled} onClick={onPay}>{payLabel}</Button>
          {isCatalogIssue ? <Alert className="border-amber-200 bg-amber-50 text-amber-950"><AlertDescription>결제 설정 점검 중</AlertDescription></Alert> : null}
          {isCatalogPending && !isCatalogIssue ? <Alert><AlertDescription>상품 정보를 불러오는 중입니다.</AlertDescription></Alert> : null}
          {statusMessage ? <Alert className="border-amber-200 bg-amber-50 text-amber-950"><AlertDescription>{statusMessage}</AlertDescription></Alert> : null}
          {paymentError ? <Alert variant="destructive"><AlertDescription>{paymentError}</AlertDescription></Alert> : null}
          <Alert><ShieldCheck /><AlertDescription>실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.</AlertDescription></Alert>
          <p className="text-center text-xs text-muted-foreground">결제가 실패하면 잔액 변경 없이 다시 시도만 요청됩니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}

/** checkout 생성, polling, portal 이동을 기존 계약 그대로 유지한 결제 페이지를 렌더링한다. */
export function PaymentPage() {
  const navigate = useNavigate();
  const { planId } = useParams();
  const location = useLocation();
  const auth = useAuth();
  const { catalog, catalogLoadFailed } = usePaymentCatalog(isLocalUiMockEnabled());
  const refreshProfile = auth.refreshProfile;
  const purchaseCredits = auth.purchaseCredits;
  const prepareLogin = auth.prepareLogin ?? (() => undefined);
  const isLoading = auth.isLoading ?? false;
  const isExplicitlyUnauthenticated = auth.isAuthenticated === false;
  const isLocalUiMock = isLocalUiMockEnabled();
  const state = (location.state as PaymentLocationState) || {};
  const returnTo = new URLSearchParams(location.search).get("returnTo");
  const [selectedMethod, setSelectedMethod] = useState("card");
  const [paying, setPaying] = useState(false);
  const [checkingPayment, setCheckingPayment] = useState(false);
  const [paid, setPaid] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const resolvedPlan = useMemo(() => resolvePlan(planId, state, catalog, isLocalUiMock), [catalog, isLocalUiMock, planId, state]);
  const isCatalogIssue = catalogLoadFailed && !isLocalUiMock;
  const isCatalogPending = !isLocalUiMock && !catalogLoadFailed && catalog.length === 0 && state.amount === undefined;

  useEffect(() => {
    if (isLoading || !isExplicitlyUnauthenticated) {
      return;
    }

    prepareLogin(`${location.pathname}${location.search}`);
    navigate("/login");
  }, [isExplicitlyUnauthenticated, isLoading, location.pathname, location.search, navigate, prepareLogin]);

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
          if (!active) return;

          if (result.credits_applied) {
            if (isLocalUiMock) {
              if (applyLocalUiMockCheckoutCredits(checkoutId)) {
                purchaseCredits(resolvedPlan.credits);
              }
            } else {
              await refreshProfile();
            }
            if (!active) return;
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
          if (!active) return;
          setCheckingPayment(false);
          setStatusMessage(null);
          setPaymentError(error instanceof Error ? error.message : "결제 상태를 확인하지 못했습니다.");
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
  }, [isLocalUiMock, location.search, paid, purchaseCredits, refreshProfile, resolvedPlan.credits]);

  const handlePay = async () => {
    setPaying(true);
    setPaymentError(null);
    setStatusMessage(null);

    try {
      const successUrl = buildPublicAppUrl(`${buildPaymentRoute(resolvedPlan.planId, { checkout: "success", returnTo })}&checkout_id={CHECKOUT_ID}`);
      const cancelUrl = buildPublicAppUrl(buildPaymentRoute(resolvedPlan.planId, { checkout: "cancel", returnTo }));
      const session = await createCheckoutSessionApi({ planId: resolvedPlan.planId, successUrl, cancelUrl });
      window.location.assign(session.checkout_url);
    } catch (error) {
      setPaying(false);
      setPaymentError(error instanceof Error ? error.message : "결제 세션 생성에 실패했습니다.");
    }
  };

  const handleOpenPortal = async () => {
    if (isLocalUiMock) {
      setPaymentError("mock 모드에서는 주문/영수증 포털을 제공하지 않습니다.");
      return;
    }

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

  const payLabel = paying || checkingPayment
    ? "처리 중..."
    : isCatalogIssue
    ? "설정 점검 중"
    : isCatalogPending
    ? "상품 확인 중"
    : `지금 결제 · ${resolvedPlan.priceLabel}`;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }} className="w-full max-w-5xl">
      <AnimatePresence mode="wait">
        {paid ? (
          <motion.div key="success" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35 }}>
            <PaymentSuccessState isLocalUiMock={isLocalUiMock} portalLoading={portalLoading} returnTo={returnTo} onOpenPortal={() => void handleOpenPortal()} />
          </motion.div>
        ) : (
          <motion.div key="checkout" exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.2 }}>
            <PaymentCheckoutState priceBackHref={returnTo ? `/pricing?returnTo=${encodeURIComponent(returnTo)}` : "/pricing"} resolvedPlan={resolvedPlan} selectedMethod={selectedMethod} onMethodChange={setSelectedMethod} payButtonDisabled={paying || checkingPayment || isCatalogIssue || isCatalogPending} payLabel={payLabel} isCatalogIssue={isCatalogIssue} isCatalogPending={isCatalogPending} statusMessage={statusMessage} paymentError={paymentError} onPay={() => void handlePay()} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
