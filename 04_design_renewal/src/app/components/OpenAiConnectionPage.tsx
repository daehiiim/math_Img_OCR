import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { motion } from "motion/react";
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
import { Button } from "./ui/button";

export function OpenAiConnectionPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, connectOpenAi, disconnectOpenAi } = useAuth();
  const isConnected = user?.openAiConnected ?? false;
  const [error, setError] = useState<string | null>(null);
  const returnTo = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("returnTo") || "/new";
  }, [location.search]);

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
      className="liquid-page-shell liquid-page-shell--auth w-full max-w-[460px]"
    >
      <button
        onClick={() => navigate(returnTo)}
        className="mb-6 flex cursor-pointer items-center gap-1.5 text-[13px] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        새 작업으로 돌아가기
      </button>

      <div className="liquid-frost-panel rounded-[32px] p-8 text-center">
        <div
          className={`liquid-inline-note mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-[20px] ${
            isConnected ? "text-emerald-700" : "text-foreground"
          }`}
        >
          {isConnected ? (
            <CheckCircle2 className="h-7 w-7 text-emerald-600" />
          ) : (
            <KeyRound className="h-7 w-7" />
          )}
        </div>

        <h1 className="mb-3 text-[22px] tracking-[-0.02em] text-foreground">
          {isConnected ? "OpenAI 연결 완료" : "OpenAI API key 연결"}
        </h1>

        {isConnected ? (
          <>
            <p className="mb-6 text-[14px] leading-relaxed text-muted-foreground">
              사용자 소유 키로 OCR과 해설을 처리합니다. 이미지 생성은 계정 크레딧을 계속 사용합니다.
            </p>
            <div className="liquid-inline-note mb-6 rounded-[22px] p-4 text-left">
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                Connected Key
              </p>
              <p className="mt-2 font-mono text-[13px] text-foreground">
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
              <Button
                onClick={() => navigate(returnTo)}
                className="h-11 gap-2"
              >
                새 작업으로 이동
                <ArrowRight className="h-4 w-4" />
              </Button>
              <Button
                onClick={() => void disconnectOpenAi()}
                variant="ghost"
                className="text-[13px] text-muted-foreground hover:text-red-500"
              >
                연결 해제
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="mb-7 text-[14px] leading-relaxed text-muted-foreground">
              OpenAI API key를 연결하면 OCR과 해설은 사용자 소유 키로 처리할 수 있습니다.
              이미지 생성은 별도 크레딧이 필요합니다.
            </p>

            <div className="mb-6 space-y-2.5 text-left">
              {[
                { icon: Sparkles, text: "OCR과 해설은 사용자 OpenAI key로 처리" },
                { icon: ShieldCheck, text: "이미지 생성은 크레딧이 필요" },
                { icon: WalletCards, text: "연결하지 않으면 모든 작업에 크레딧 사용" },
              ].map((item) => (
                <div
                  key={item.text}
                  className="liquid-feature-row flex items-center gap-2.5 rounded-[20px] px-4 py-3"
                >
                  <item.icon className="h-4 w-4 shrink-0 text-foreground" />
                  <span className="text-[13px] text-foreground/80">{item.text}</span>
                </div>
              ))}
            </div>

            <div className="liquid-inline-note mb-3 rounded-[24px] p-3 text-left">
              <OpenAiKeyForm
                title="OpenAI API key 연결"
                description="저장된 key는 서버에서 암호화되며, 화면에는 마스킹 정보만 남습니다."
                submitLabel="OpenAI 연결"
                onSubmit={handleConnect}
              />
            </div>
            {error && <p className="mb-4 text-left text-[12px] text-red-500">{error}</p>}

            <div className="flex flex-col gap-3">
              <Button
                onClick={() =>
                  navigate(returnTo ? `/pricing?returnTo=${encodeURIComponent(returnTo)}` : "/pricing")
                }
                variant="outline"
                className="h-11"
              >
                크레딧 구매로 이동
              </Button>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}
