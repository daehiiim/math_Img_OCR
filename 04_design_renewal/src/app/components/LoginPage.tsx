import { useEffect } from "react";
import { motion } from "motion/react";
import { useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { resolvePostLoginPath } from "../lib/authFlow";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Separator } from "./ui/separator";
import { PageIntro } from "./shared/PageIntro";

/** Google 로고를 로그인 버튼에 재사용 가능한 SVG로 렌더링한다. */
function GoogleLogo() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}

/** 로그인 완료 후 실제 목적지로 이동하는 공통 분기 규칙을 적용한다. */
function useLoginRedirect() {
  const navigate = useNavigate();
  const { clearPostLoginPath, isAuthenticated, isLocalUiMock, readPostLoginPath, user } = useAuth();

  useEffect(() => {
    if (!isAuthenticated || !user) {
      return;
    }

    const nextPath = readPostLoginPath();
    const destination = isLocalUiMock
      ? nextPath
      : resolvePostLoginPath({ openAiConnected: user.openAiConnected, credits: user.credits }, nextPath);
    clearPostLoginPath();
    navigate(destination, { replace: true });
  }, [clearPostLoginPath, isAuthenticated, isLocalUiMock, navigate, readPostLoginPath, user]);
}

/** 로그인 화면 하단 안내 문구를 mock/live 모드에 맞게 렌더링한다. */
function LoginHint({ isLocalUiMock }: { isLocalUiMock: boolean }) {
  return (
    <p className="text-xs text-muted-foreground">
      {isLocalUiMock
        ? "Google 없이 로컬 프로필로 바로 진입합니다."
        : "이미지를 올리는 순간에만 로그인하도록 동작합니다."}
    </p>
  );
}

/** 인증 진입점을 공통 카드 패턴으로 렌더링한다. */
export function LoginPage() {
  const { authErrorMessage, isAuthenticated, isLoading, isLocalUiMock, loginWithGoogle } = useAuth();
  useLoginRedirect();

  if (isLoading || isAuthenticated) {
    return null;
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }} className="w-full max-w-[420px]">
      <Card>
        <CardHeader className="items-center text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-foreground text-lg text-background">M</div>
          <PageIntro title="MathHWP 로그인" description="수식 OCR 작업을 이어가기 위해 로그인하고, 이미지 수식을 편집 가능한 문서 흐름으로 연결하세요." badge={isLocalUiMock ? "로컬 mock" : "Google OAuth"} align="center" />
        </CardHeader>
        <CardContent className="space-y-4">
          {authErrorMessage ? <Alert variant="destructive"><AlertDescription>{authErrorMessage}</AlertDescription></Alert> : <Alert><AlertDescription>{isLocalUiMock ? "테스트용 로컬 프로필로 바로 진입합니다." : "로그인 후 OpenAI 연결 상태와 잔여 크레딧에 맞춰 다음 화면으로 이동합니다."}</AlertDescription></Alert>}
          <Separator />
          <Button type="button" variant="outline" className="w-full gap-3" disabled={Boolean(authErrorMessage)} onClick={() => void loginWithGoogle()}>
            <GoogleLogo />
            {isLocalUiMock ? "로컬 테스트로 로그인" : "Google 계정으로 로그인"}
          </Button>
          <LoginHint isLocalUiMock={isLocalUiMock} />
        </CardContent>
      </Card>
    </motion.div>
  );
}
