import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { Check, ArrowLeft, Sparkles } from "lucide-react";

const plans = [
  {
    id: "single",
    title: "Single",
    price: "90",
    currency: "원",
    description: "1개 이미지 변환",
    perImage: "90원 / 이미지",
    badge: null,
    highlight: false,
    credits: 1,
    features: ["1개 이미지 변환", "HWPX 내보내기", "AI OCR 처리"],
  },
  {
    id: "starter",
    title: "Starter",
    price: "5,900",
    currency: "원",
    description: "100개 이미지",
    perImage: "59원 / 이미지",
    badge: null,
    highlight: false,
    credits: 100,
    features: [
      "100개 이미지 변환",
      "HWPX 내보내기",
      "AI OCR 처리",
      "영역 선택",
    ],
  },
  {
    id: "pro",
    title: "Pro",
    price: "10,900",
    currency: "원",
    description: "200개 이미지",
    perImage: "54.5원 / 이미지",
    badge: "최고 가치",
    highlight: true,
    credits: 200,
    features: [
      "200개 이미지 변환",
      "HWPX 내보내기",
      "AI OCR 처리",
      "영역 선택",
      "우선 처리",
    ],
  },
];

export function PricingPage() {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-[900px]"
    >
      {/* Back link */}
      <button
        onClick={() => navigate("/")}
        className="flex items-center gap-1.5 text-[13px] text-[#71717a] hover:text-[#111] transition-colors mb-8 cursor-pointer"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        홈으로 돌아가기
      </button>

      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-[26px] tracking-[-0.02em] text-[#111] mb-2">
          이미지 구매
        </h1>
        <p className="text-[15px] text-[#71717a]">
          수학 이미지를 HWPX 문서로 즉시 변환하세요.
        </p>
      </div>

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {plans.map((plan, index) => (
          <motion.div
            key={plan.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.4,
              delay: index * 0.08,
              ease: [0.25, 0.46, 0.45, 0.94],
            }}
            className="relative"
          >
            {/* Badge */}
            {plan.badge && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                <div className="flex items-center gap-1 bg-indigo-600 text-white text-[11px] px-3 py-1 rounded-full">
                  <Sparkles className="w-3 h-3" />
                  {plan.badge}
                </div>
              </div>
            )}

            <div
              className={`bg-white rounded-xl border p-7 flex flex-col h-full transition-shadow ${
                plan.highlight
                  ? "border-indigo-200 shadow-[0_4px_24px_rgba(79,70,229,0.1)] ring-1 ring-indigo-100"
                  : "border-[#e4e4e7] shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)]"
              }`}
            >
              {/* Plan name */}
              <p className="text-[13px] text-[#71717a] mb-4">{plan.title}</p>

              {/* Price */}
              <div className="flex items-baseline gap-0.5 mb-1">
                <span className="text-[36px] tracking-[-0.03em] text-[#111] leading-none">
                  {plan.price}
                </span>
                <span className="text-[15px] text-[#71717a]">{plan.currency}</span>
              </div>

              {/* Per image */}
              <p className="text-[13px] text-[#a1a1aa] mb-6">{plan.perImage}</p>

              {/* CTA Button */}
              <button
                onClick={() =>
                  navigate(`/payment/${plan.id}`, {
                    state: {
                      title: plan.title,
                      price: `${plan.price}${plan.currency}`,
                      credits: plan.credits,
                    },
                  })
                }
                className={`w-full h-10 rounded-lg text-[14px] cursor-pointer transition-all active:scale-[0.98] mb-7 ${
                  plan.highlight
                    ? "bg-[#111] text-white hover:bg-[#222]"
                    : "bg-[#fafafa] border border-[#e4e4e7] text-[#111] hover:bg-[#f4f4f5]"
                }`}
              >
                구매
              </button>

              {/* Features */}
              <div className="space-y-2.5 pt-6 border-t border-[#f4f4f5]">
                {plan.features.map((feature) => (
                  <div key={feature} className="flex items-start gap-2">
                    <Check className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
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
