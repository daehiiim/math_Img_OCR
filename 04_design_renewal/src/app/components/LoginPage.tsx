import { useNavigate, Navigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import { motion } from "motion/react";

export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, loginWithGoogle } = useAuth();

  // Already logged in → go to workspace (or pricing if no credits)
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleLogin = () => {
    loginWithGoogle();
    // After login, Layout will handle redirect to pricing if no credits
    navigate("/");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-[380px]"
    >
      <div className="bg-white rounded-2xl shadow-[0_2px_20px_rgba(0,0,0,0.06)] border border-black/[0.04] p-10 flex flex-col items-center text-center">
        {/* Logo */}
        <div className="w-14 h-14 rounded-xl bg-[#111] flex items-center justify-center mb-7">
          <span className="text-[18px] text-white tracking-tight">M</span>
        </div>

        <h1 className="text-[22px] tracking-[-0.02em] text-[#111] mb-2">Math OCR</h1>
        <p className="text-[14px] text-[#71717a] leading-relaxed mb-9 max-w-[300px]">수학 이미지를 업로드하여 HWPX 문서로 자동 변환합니다.</p>

        {/* Google Sign In Button */}
        <button
          onClick={handleLogin}
          className="w-full flex items-center justify-center gap-3 h-11 rounded-lg bg-white border border-[#e4e4e7] hover:bg-[#fafafa] hover:border-[#d4d4d8] active:scale-[0.99] transition-all cursor-pointer shadow-[0_1px_2px_rgba(0,0,0,0.05)]"
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
          <span className="text-[14px] text-[#3f3f46]">Google 계정으로 로그인</span>
        </button>

        <p className="text-[12px] text-[#a1a1aa] mt-5">
          계속하려면 Google 계정 로그인이 필요합니다.
        </p>
      </div>
    </motion.div>
  );
}