import { useState } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import { motion } from "motion/react";
import {
  Bot,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Zap,
  Infinity,
  ShieldCheck,
} from "lucide-react";

export function ChatGptConnectionPage() {
  const navigate = useNavigate();
  const { user, connectChatGpt, disconnectChatGpt } = useAuth();
  const isConnected = user?.chatGptConnected ?? false;
  const [connecting, setConnecting] = useState(false);

  const handleConnect = () => {
    setConnecting(true);
    setTimeout(() => {
      connectChatGpt();
      setConnecting(false);
    }, 1500);
  };

  const handleDisconnect = () => {
    disconnectChatGpt();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-[420px]"
    >
      {/* Back */}
      <button
        onClick={() => navigate("/")}
        className="flex items-center gap-1.5 text-[13px] text-[#71717a] hover:text-[#111] transition-colors mb-6 cursor-pointer"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        워크스페이스로 돌아가기
      </button>

      <div className="bg-white rounded-2xl shadow-[0_2px_20px_rgba(0,0,0,0.06)] border border-black/[0.04] p-8 flex flex-col items-center text-center">
        {/* Icon */}
        <div
          className={`w-14 h-14 rounded-xl flex items-center justify-center mb-6 transition-colors ${
            isConnected ? "bg-[#f4f4f5]" : "bg-[#fafafa]"
          }`}
        >
          {isConnected ? (
            <CheckCircle2 className="w-7 h-7 text-[#111]" />
          ) : (
            <Bot className="w-7 h-7 text-[#111]" />
          )}
        </div>

        <h1 className="text-[20px] tracking-[-0.02em] text-[#111] mb-3">
          {isConnected ? "ChatGPT 연결됨" : "ChatGPT 계정 연결"}
        </h1>

        {isConnected ? (
          <>
            <p className="text-[14px] text-[#71717a] leading-relaxed mb-6 max-w-[340px]">
              ChatGPT 계정이 연결되었습니다. Math OCR이 무제한 변환을 위해 계정을 사용합니다.
            </p>

            <div className="w-full bg-[#fafafa] rounded-lg p-4 mb-6">
              <div className="flex items-center justify-center gap-2 text-[13px] text-[#111]">
                <Infinity className="w-4 h-4" />
                무제한 변환 활성화
              </div>
            </div>

            <button
              onClick={handleDisconnect}
              className="text-[13px] text-[#a1a1aa] hover:text-red-500 transition-colors cursor-pointer"
            >
              ChatGPT 연결 해제
            </button>
          </>
        ) : (
          <>
            <p className="text-[14px] text-[#71717a] leading-relaxed mb-2 max-w-[340px]">
              Math OCR은 수학 OCR 처리를 위해 ChatGPT 계정을 사용할 수 있습니다.
            </p>
            <p className="text-[14px] text-[#71717a] leading-relaxed mb-7 max-w-[340px]">
              ChatGPT Plus 또는 Pro 사용자에게 권장됩니다.
            </p>

            {/* Benefits */}
            <div className="w-full space-y-2.5 mb-7">
              {[
                { icon: Infinity, text: "무제한 이미지 변환" },
                { icon: Zap, text: "더 빠른 처리 속도" },
                { icon: ShieldCheck, text: "본인 ChatGPT 계정 사용" },
              ].map((item) => (
                <div
                  key={item.text}
                  className="flex items-center gap-2.5 text-left px-4 py-2.5 bg-[#fafafa] rounded-lg"
                >
                  <item.icon className="w-4 h-4 text-[#111] shrink-0" />
                  <span className="text-[13px] text-[#52525b]">{item.text}</span>
                </div>
              ))}
            </div>

            {/* Connect Button */}
            <button
              onClick={handleConnect}
              disabled={connecting}
              className="w-full h-11 rounded-lg bg-[#111] text-white text-[14px] hover:bg-[#222] active:scale-[0.99] transition-all cursor-pointer disabled:opacity-60 flex items-center justify-center gap-2 mb-5"
            >
              {connecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  연결 중...
                </>
              ) : (
                <>
                  ChatGPT 연결
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            {/* Skip link */}
            <button
              onClick={() => navigate("/")}
              className="text-[13px] text-[#a1a1aa] hover:text-[#71717a] transition-colors cursor-pointer"
            >
              건너뛰기
            </button>
          </>
        )}
      </div>
    </motion.div>
  );
}