import { useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  KeyRound,
  ShieldCheck,
  Sparkles,
  WalletCards,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { OpenAiKeyForm } from "./OpenAiKeyForm";

export function OpenAiConnectionPage() {
  const navigate = useNavigate();
  const { user, connectOpenAi, disconnectOpenAi } = useAuth();
  const isConnected = user?.openAiConnected ?? false;
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async (apiKey: string) => {
    try {
      setError(null);
      await connectOpenAi(apiKey);
    } catch (connectError) {
      const message = connectError instanceof Error ? connectError.message : "OpenAI key 저장에 실패했습니다.";
      setError(message);
      throw connectError;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-[440px]"
    >
      <button
        onClick={() => navigate("/new")}
        className="mb-6 flex items-center gap-1.5 text-[13px] text-[#71717a] transition-colors hover:text-[#111] cursor-pointer"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        새 작업으로 돌아가기
      </button>

      <div className="rounded-2xl border border-black/[0.04] bg-white p-8 text-center shadow-[0_2px_20px_rgba(0,0,0,0.06)]">
        <div
          className={`mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-xl ${
            isConnected ? "bg-[#f2f8f4]" : "bg-[#faf7f1]"
          }`}
        >
          {isConnected ? (
            <CheckCircle2 className="h-7 w-7 text-emerald-600" />
          ) : (
            <KeyRound className="h-7 w-7 text-[#111]" />
          )}
        </div>

        <h1 className="mb-3 text-[22px] tracking-[-0.02em] text-[#111]">
          {isConnected ? "OpenAI 연결 완료" : "OpenAI API key 연결"}
        </h1>

        {isConnected ? (
          <>
            <p className="mb-6 text-[14px] leading-relaxed text-[#71717a]">
              사용자 소유 키로 처리하도록 연결되었습니다.
            </p>
            <div className="mb-6 rounded-xl bg-[#fafaf8] p-4 text-left">
              <p className="text-[11px] uppercase tracking-[0.16em] text-[#9b948c]">
                Connected Key
              </p>
              <p className="mt-2 font-mono text-[13px] text-[#111]">
                {user?.openAiMaskedKey ?? "연결됨"}
              </p>
            </div>
            <div className="mb-6">
              <OpenAiKeyForm
                title="OpenAI key 다시 저장"
                description="오입력한 key도 이 화면에서 바로 덮어써 수정할 수 있습니다."
                submitLabel="OpenAI key 다시 저장"
                maskedKey={user?.openAiMaskedKey}
                onSubmit={handleConnect}
              />
            </div>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => navigate("/new")}
                className="flex h-11 items-center justify-center gap-2 rounded-lg bg-[#111] text-[14px] text-white transition-all hover:bg-[#222]"
              >
                새 작업으로 이동
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => void disconnectOpenAi()}
                className="text-[13px] text-[#a1a1aa] transition-colors hover:text-red-500"
              >
                연결 해제
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="mb-7 text-[14px] leading-relaxed text-[#71717a]">
              먼저 본인 OpenAI API key를 연결해 무료 처리 모드로 시작하세요. 연결하지 않으면
              아래에서 크레딧 구매로 넘어갈 수 있습니다.
            </p>

            <div className="mb-6 space-y-2.5 text-left">
              {[
                { icon: Sparkles, text: "본인 API key로 바로 OCR 실행" },
                { icon: ShieldCheck, text: "크레딧 없이 사용자 소유 키로 처리" },
                { icon: WalletCards, text: "연결하지 않으면 즉시 크레딧 구매로 이동" },
              ].map((item) => (
                <div
                  key={item.text}
                  className="flex items-center gap-2.5 rounded-lg bg-[#faf7f1] px-4 py-3"
                >
                  <item.icon className="h-4 w-4 shrink-0 text-[#111]" />
                  <span className="text-[13px] text-[#4b4b4b]">{item.text}</span>
                </div>
              ))}
            </div>

            <div className="mb-3 rounded-xl border border-[#ebe6df] bg-[#fcfbf8] p-3 text-left">
              <OpenAiKeyForm
                title="OpenAI API key 연결"
                description="저장된 key는 서버에서 암호화되며, 화면에는 마스킹 정보만 남습니다."
                submitLabel="OpenAI 연결"
                onSubmit={handleConnect}
              />
            </div>
            {error && <p className="mb-4 text-left text-[12px] text-red-500">{error}</p>}

            <div className="flex flex-col gap-3">
              <button
                onClick={() => navigate("/pricing")}
                className="flex h-11 items-center justify-center rounded-lg border border-[#e4e4e7] bg-white text-[14px] text-[#111] transition-colors hover:bg-[#fafafa]"
              >
                크레딧 구매로 이동
              </button>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}
