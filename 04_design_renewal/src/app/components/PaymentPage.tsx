import { useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router";
import { useAuth } from "../context/AuthContext";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, CheckCircle2, CreditCard, Loader2, Lock, ShieldCheck } from "lucide-react";

const paymentMethods = [
  {
    id: "card",
    label: "신용카드",
    icon: CreditCard,
    sublabel: "**** **** **** 4242",
  },
];

export function PaymentPage() {
  const navigate = useNavigate();
  const { planId } = useParams();
  const location = useLocation();
  const { purchaseCredits } = useAuth();

  const state =
    (location.state as {
      title?: string;
      price?: string;
      credits?: number;
    }) || {};
  const title = state.title || planId || "Starter";
  const price = state.price || "5,900원";
  const credits = state.credits || 200;

  const [selectedMethod, setSelectedMethod] = useState("card");
  const [paying, setPaying] = useState(false);
  const [paid, setPaid] = useState(false);

  const handlePay = () => {
    setPaying(true);
    setTimeout(() => {
      setPaying(false);
      setPaid(true);
      purchaseCredits(credits);
      setTimeout(() => {
        navigate("/workspace");
      }, 2000);
    }, 2200);
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
            className="bg-white rounded-2xl shadow-[0_2px_20px_rgba(0,0,0,0.06)] border border-black/[0.04] p-10 flex flex-col items-center text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.15 }}
              className="w-16 h-16 rounded-full bg-emerald-50 flex items-center justify-center mb-6"
            >
              <CheckCircle2 className="w-8 h-8 text-emerald-600" />
            </motion.div>
            <h1 className="text-[20px] tracking-[-0.02em] text-[#111] mb-2">
              결제 성공
            </h1>
            <p className="text-[14px] text-[#71717a] mb-1">
              {credits}개의 이미지가 계정에 추가되었습니다.
            </p>
            <p className="text-[13px] text-[#a1a1aa] mt-1">
              워크스페이스로 이동합니다...
            </p>
            <div className="mt-4">
              <Loader2 className="w-4 h-4 animate-spin text-[#a1a1aa]" />
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="form"
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2 }}
          >
            {/* Back */}
            <button
              onClick={() => navigate("/pricing")}
              className="flex items-center gap-1.5 text-[13px] text-[#71717a] hover:text-[#111] transition-colors mb-6 cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              가격 페이지로 돌아가기
            </button>

            {/* Title */}
            <div className="mb-6">
              <h1 className="text-[22px] tracking-[-0.02em] text-[#111] mb-1">
                결제 완료하기
              </h1>
              <p className="text-[14px] text-[#71717a]">
                Stripe 보안 결제 시스템
              </p>
            </div>

            <div className="bg-white rounded-2xl shadow-[0_2px_20px_rgba(0,0,0,0.06)] border border-black/[0.04] overflow-hidden">
              {/* Order Summary */}
              <div className="p-6 border-b border-[#f4f4f5]">
                <p className="text-[11px] text-[#a1a1aa] uppercase tracking-widest mb-4">
                  주문 요약
                </p>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[14px] text-[#71717a]">플랜</span>
                  <span className="text-[14px] text-[#111]">{title}</span>
                </div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[14px] text-[#71717a]">이미지</span>
                  <span className="text-[14px] text-[#111]">{credits}</span>
                </div>
                <div className="h-px bg-[#f4f4f5] my-3" />
                <div className="flex items-center justify-between">
                  <span className="text-[15px] text-[#111]">총액</span>
                  <span className="text-[18px] tracking-[-0.02em] text-[#111]">
                    {price}
                  </span>
                </div>
              </div>

              {/* Payment Methods */}
              <div className="p-6 border-b border-[#f4f4f5]">
                <p className="text-[11px] text-[#a1a1aa] uppercase tracking-widest mb-4">
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
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-all cursor-pointer ${
                          isSelected
                            ? "border-[#111] bg-[#fafafa]"
                            : "border-[#e4e4e7] hover:border-[#d4d4d8] bg-white"
                        }`}
                      >
                        <div
                          className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ${
                            isSelected ? "border-[#111]" : "border-[#d4d4d8]"
                          }`}
                        >
                          {isSelected && (
                            <div className="w-2 h-2 rounded-full bg-[#111]" />
                          )}
                        </div>
                        <Icon
                          className={`w-4 h-4 ${
                            isSelected ? "text-[#111]" : "text-[#a1a1aa]"
                          }`}
                        />
                        <div className="flex-1 text-left">
                          <span className="text-[14px] text-[#3f3f46]">
                            {method.label}
                          </span>
                        </div>
                        {method.sublabel && isSelected && (
                          <span className="text-[12px] text-[#a1a1aa] font-mono">
                            {method.sublabel}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Pay Button */}
              <div className="p-6">
                <button
                  onClick={handlePay}
                  disabled={paying}
                  className="w-full h-11 rounded-lg bg-[#111] text-white text-[14px] hover:bg-[#222] active:scale-[0.99] transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {paying ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      처리 중...
                    </>
                  ) : (
                    <>
                      <Lock className="w-3.5 h-3.5" />
                      지금 결제 &middot; {price}
                    </>
                  )}
                </button>

                <div className="flex items-center justify-center gap-1.5 mt-4 text-[11px] text-[#a1a1aa]">
                  <ShieldCheck className="w-3 h-3" />
                  256-bit SSL 암호화 &middot; Stripe 보안 결제
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
