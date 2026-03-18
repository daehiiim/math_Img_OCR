import { useNavigate } from "react-router";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BadgeCheck,
  FileImage,
  KeyRound,
  Layers3,
  ScanText,
  ShieldCheck,
} from "lucide-react";

import { Button } from "./ui/button";
import { useAuth } from "../context/AuthContext";

const steps = [
  {
    title: "사진을 찍으세요.",
    body: "시험지, 프린트물, 풀이를 업로드하세요.\n자동으로 문항, 해설, 이미지를 만들어줍니다.",
    icon: FileImage,
  },
  {
    title: "검토하세요.",
    body: "결과를 보고 내용을 검토하세요.\n필요하면 수정하세요.",
    icon: Layers3,
  },
  {
    title: "변환하세요.",
    body: "HWPX로 자료를 출력하세요.\n버튼 한 번이면 사진이 한글파일로 완성됩니다.",
    icon: ScanText,
  },
];

export function PublicHomePage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-[#f5f1ea] text-[#171717]">
      <header className="sticky top-0 z-20 border-b border-black/5 bg-[#f5f1ea]/90 backdrop-blur px-5 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-3 text-left"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#171717] text-white">
              M
            </div>
            <div className="space-y-1">
              <p className="text-[15px] font-semibold uppercase tracking-[0.18em] text-[#5f5246] sm:text-[16px]">
                MATH OCR
              </p>
              <p className="text-[13px] tracking-[-0.02em] text-[#4c453e] sm:text-[14px]">
                이미지에서 HWPX까지
              </p>
            </div>
          </button>

          <div className="flex items-center gap-2">
            <Button
              variant={isAuthenticated ? "outline" : "default"}
              onClick={() =>
                navigate(isAuthenticated ? "/workspace" : "/login")
              }
            >
              {isAuthenticated ? "내 작업실" : "로그인"}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl flex-col gap-14 px-5 py-10 lg:px-8 lg:py-14">
        <section className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="rounded-[36px] border border-black/5 bg-white p-8 shadow-[0_25px_80px_rgba(0,0,0,0.06)] lg:p-12"
          >
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#d2c7bc] bg-[#f6eee4] px-3 py-1 text-[12px] text-[#7c5e44]">
              <BadgeCheck className="h-3.5 w-3.5" />
              어떤 문제 사진이라도 한글 파일로
            </div>
            <h1 className="max-w-[900px] text-[26px] leading-[1.08] tracking-[-0.05em] sm:text-[42px] lg:text-[56px]">
              컴퓨터에서도, 휴대폰에서도 문제를 한글로.
            </h1>
            <p className="mt-6 max-w-2xl text-[16px] leading-7 text-[#5b554f] lg:text-[18px]">
              <span className="block">
                로그인 없이 시작하고, 문서 제작도 간단히.
              </span>
              <span className="block">바로 결과를 만들어내는 워크스테이션</span>
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button onClick={() => navigate("/new")} className="gap-2">
                새 작업 시작
                <ArrowRight className="h-4 w-4" />
              </Button>
              <Button variant="outline" onClick={() => navigate("/pricing")}>
                가격 보기
              </Button>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.08 }}
            className="grid gap-4"
          >
            <div className="rounded-[30px] bg-[#171717] p-7 text-white shadow-[0_28px_80px_rgba(23,23,23,0.22)]">
              <p className="text-[12px] uppercase tracking-[0.2em] text-white/50">
                이용 정책
              </p>
              <div className="mt-5 space-y-4">
                <div className="flex items-start gap-3">
                  <KeyRound className="mt-0.5 h-5 w-5 text-[#f6c17f]" />
                  <div>
                    <p className="text-[15px]">누구나 무료 이용</p>
                    <p className="mt-1 text-[13px] leading-6 text-white/65">
                      본인의 OpenAI API key를 가지고 있다면 무료로 사용하십시오
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-0.5 h-5 w-5 text-[#9bd2c5]" />
                  <div>
                    <p className="text-[15px]">더 편하게</p>
                    <p className="mt-1 text-[13px] leading-6 text-white/65">
                      간편하게 로그인하고 모든 기능을 사용하고 싶으면 크레딧을
                      구매하세요
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[30px] border border-black/5 bg-[#ebe4d7] p-7">
              <p className="text-[12px] uppercase tracking-[0.2em] text-[#7b6b58]">
                이미지 제작
              </p>
              <p className="mt-4 text-[20px] leading-8 tracking-[-0.03em]">
                어떤 이미지라도 완벽하게 추출하니까.
              </p>
              <p className="mt-4 text-[14px] leading-6 text-[#645b53]">
                이제는 캡쳐해서 만들지 마세요. 직접 만든 것 처럼 생성되는
                이미지.
              </p>
            </div>
          </motion.div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          {steps.map((step, index) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.14 + index * 0.06 }}
              className="rounded-[28px] border border-black/5 bg-white p-6 shadow-[0_14px_40px_rgba(0,0,0,0.04)]"
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#171717] text-white">
                <step.icon className="h-5 w-5" />
              </div>
              <p className="text-[13px] uppercase tracking-[0.18em] text-[#8a8176]">
                Step 0{index + 1}
              </p>
              <h2 className="mt-3 text-[24px] tracking-[-0.03em]">
                {step.title}
              </h2>
              <p className="mt-3 whitespace-pre-line text-[14px] leading-6 text-[#615950]">
                {step.body}
              </p>
            </motion.div>
          ))}
        </section>
      </main>
    </div>
  );
}
