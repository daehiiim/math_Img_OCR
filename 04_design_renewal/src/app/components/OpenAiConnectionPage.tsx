import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router";
import { motion } from "motion/react";
import { ArrowRight, CheckCircle2, KeyRound, ShieldCheck, Sparkles, WalletCards } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { OpenAiKeyForm } from "./OpenAiKeyForm";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Separator } from "./ui/separator";
import { PageIntro } from "./shared/PageIntro";

/** 연결 안내 항목을 아이콘 카드 한 줄로 렌더링한다. */
function ConnectionBenefit({
  icon: Icon,
  text,
}: {
  icon: typeof Sparkles;
  text: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
      <Icon className="shrink-0 text-foreground" />
      <span>{text}</span>
    </div>
  );
}

/** OpenAI 연결 완료 상태의 관리 카드를 렌더링한다. */
function ConnectedState({
  maskedKey,
  returnTo,
  onConnect,
  onDisconnect,
}: {
  maskedKey?: string | null;
  returnTo: string;
  onConnect: (apiKey: string) => Promise<void>;
  onDisconnect: () => Promise<void>;
}) {
  return (
    <Card>
      <CardHeader className="items-center text-center">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600"><CheckCircle2 /></div>
        <CardTitle>OpenAI 연결 완료</CardTitle>
        <Badge variant="secondary">사용자 key 연결됨</Badge>
      </CardHeader>
      <CardContent className="space-y-6">
        <Alert><AlertDescription>사용자 소유 키로 OCR과 해설을 처리합니다. 이미지 생성은 계정 크레딧을 계속 사용합니다.</AlertDescription></Alert>
        <div className="rounded-xl border bg-muted/30 p-4"><p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Connected Key</p><p className="mt-2 font-mono text-sm text-foreground">{maskedKey ?? "연결됨"}</p></div>
        <OpenAiKeyForm title="OpenAI key 다시 저장" description="오입력한 key도 이 화면에서 바로 덮어써 수정할 수 있습니다." submitLabel="OpenAI key 다시 저장" maskedKey={maskedKey} onSubmit={onConnect} />
        <Separator />
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild className="flex-1"><Link to={returnTo}>이전 화면으로 이동<ArrowRight data-icon="inline-end" /></Link></Button>
          <Button type="button" variant="outline" className="flex-1" onClick={() => void onDisconnect()}>연결 해제</Button>
        </div>
      </CardContent>
    </Card>
  );
}

/** OpenAI 미연결 상태의 연결 안내와 입력 폼을 렌더링한다. */
function DisconnectedState({
  error,
  returnTo,
  onConnect,
}: {
  error: string | null;
  returnTo: string;
  onConnect: (apiKey: string) => Promise<void>;
}) {
  return (
    <Card>
      <CardHeader className="items-center text-center">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-muted text-foreground"><KeyRound /></div>
        <CardTitle>OpenAI API key 연결</CardTitle>
        <Badge variant="outline">연결 필요</Badge>
      </CardHeader>
      <CardContent className="space-y-6">
        <Alert><AlertDescription>OpenAI API key를 연결하면 OCR과 해설은 사용자 소유 키로 처리할 수 있습니다. 이미지 생성은 별도 크레딧이 필요합니다.</AlertDescription></Alert>
        <div className="space-y-3"><ConnectionBenefit icon={Sparkles} text="OCR과 해설은 사용자 OpenAI key로 처리" /><ConnectionBenefit icon={ShieldCheck} text="이미지 생성은 크레딧이 필요" /><ConnectionBenefit icon={WalletCards} text="연결하지 않으면 모든 작업에 크레딧 사용" /></div>
        <OpenAiKeyForm title="OpenAI API key 연결" description="저장된 key는 서버에서 암호화되며, 화면에는 마스킹 정보만 남습니다." submitLabel="OpenAI 연결" onSubmit={onConnect} />
        {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
        <Separator />
        <Button asChild variant="outline" className="w-full"><Link to={returnTo ? `/pricing?returnTo=${encodeURIComponent(returnTo)}` : "/pricing"}>크레딧 구매로 이동</Link></Button>
      </CardContent>
    </Card>
  );
}

/** OpenAI key 연결, 재등록, 해제를 공통 카드 패턴으로 렌더링한다. */
export function OpenAiConnectionPage() {
  const location = useLocation();
  const { user, connectOpenAi, disconnectOpenAi } = useAuth();
  const isConnected = user?.openAiConnected ?? false;
  const [error, setError] = useState<string | null>(null);
  const returnTo = useMemo(() => new URLSearchParams(location.search).get("returnTo") || "/new", [location.search]);

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
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }} className="w-full max-w-2xl">
      <div className="space-y-6">
        <PageIntro title={isConnected ? "OpenAI 연결 관리" : "OpenAI API key 연결"} description="OCR, 해설, 이미지 생성의 과금 경계를 바꾸지 않고 key 연결 상태만 관리합니다." backHref={returnTo} backLabel="이전 화면으로 돌아가기" />
        {isConnected ? <ConnectedState maskedKey={user?.openAiMaskedKey} returnTo={returnTo} onConnect={handleConnect} onDisconnect={disconnectOpenAi} /> : <DisconnectedState error={error} returnTo={returnTo} onConnect={handleConnect} />}
      </div>
    </motion.div>
  );
}
