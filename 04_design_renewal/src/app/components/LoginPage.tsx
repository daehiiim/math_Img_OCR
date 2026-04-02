import { useEffect } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import { motion } from "motion/react";
import { resolvePostLoginPath } from "../lib/authFlow";
import { BrandLogo } from "./BrandLogo";

/** 로그인 진입 화면과 인증 버튼을 렌더링한다. */
export function LoginPage() {
  const navigate = useNavigate();
  const {
    authErrorMessage,
    clearPostLoginPath,
    isAuthenticated,
    isLoading,
    isLocalUiMock,
    loginWithGoogle,
    readPostLoginPath,
    user,
  } = useAuth();

  useEffect(() => {
    if (!isAuthenticated || !user) {
      return;
    }

    const nextPath = readPostLoginPath();
    // mock 모드에서는 로그인 직전 요청 경로를 그대로 복원해 UI 흐름을 검증한다.
    const destination = isLocalUiMock
      ? nextPath
      : resolvePostLoginPath(
          {
            openAiConnected: user.openAiConnected,
            credits: user.credits,
          },
          nextPath
        );

    clearPostLoginPath();
    navigate(destination, { replace: true });
  }, [clearPostLoginPath, isAuthenticated, isLocalUiMock, navigate, readPostLoginPath, user]);

  if (isLoading) {
    return null;
  }

  if (isAuthenticated) {
    return null;
  }

  const handleLogin = async () => {
    if (authErrorMessage) {
      return;
    }

    await loginWithGoogle();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="liquid-page-shell liquid-page-shell--auth w-full max-w-[400px]"
    >
      <div className="liquid-frost-panel flex flex-col items-center rounded-[32px] p-10 text-center">
        <BrandLogo className="mb-7 h-14 w-14 rounded-[20px]" />

        <h1 className="mb-2 text-[22px] tracking-[-0.02em] text-foreground">MathHWP</h1>
        <p className="mb-9 max-w-[300px] text-[14px] leading-relaxed text-muted-foreground">
          수학 이미지를 업로드하여 HWPX 문서로 자동 변환합니다.
        </p>

        <button
          type="button"
          onClick={handleLogin}
          disabled={Boolean(authErrorMessage)}
          className="liquid-chip flex h-12 w-full cursor-pointer items-center justify-center gap-3 rounded-2xl px-4 transition-[transform,background-color,border-color,box-shadow] duration-200 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:cursor-not-allowed disabled:opacity-60"
        >
          <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          <span className="text-[14px] text-foreground/80">
            {isLocalUiMock ? "로컬 테스트로 로그인" : "Google 계정으로 로그인"}
          </span>
        </button>

        {authErrorMessage && (
          <p className="mt-4 text-[12px] text-rose-600">
            {authErrorMessage}
          </p>
        )}
        <p className="mt-5 text-[12px] text-muted-foreground">
          {isLocalUiMock
            ? "Google 없이 로컬 프로필로 바로 진입합니다."
            : "이미지를 올리는 순간에만 로그인하도록 동작합니다."}
        </p>
      </div>
    </motion.div>
  );
}
