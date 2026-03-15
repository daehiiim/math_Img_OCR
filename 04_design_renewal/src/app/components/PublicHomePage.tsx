import { useNavigate } from "react-router";
import { motion } from "motion/react";
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
    title: "문제 이미지를 올립니다",
    body: "시험지, 프린트물, 풀이 메모를 그대로 가져와 다중 영역으로 나눌 준비를 합니다.",
    icon: FileImage,
  },
  {
    title: "수식과 도형을 정리합니다",
    body: "OCR 결과를 보고 SVG 편집기로 선, 점선, 곡선, 텍스트를 다듬어 HWPX 품질을 올립니다.",
    icon: Layers3,
  },
  {
    title: "HWPX로 바로 넘깁니다",
    body: "수업 자료, 학원 문서, 문제 은행 템플릿으로 곧바로 이어지게 구성합니다.",
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
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em] text-[#7c6f64]">
                Math OCR Studio
              </p>
              <p className="text-[15px] tracking-[-0.02em]">이미지에서 HWPX까지</p>
            </div>
          </button>

          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => navigate("/pricing")}>
              가격
            </Button>
            <Button
              variant={isAuthenticated ? "outline" : "default"}
              onClick={() => navigate(isAuthenticated ? "/workspace" : "/login")}
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
              수학 문서 변환에 맞춘 OCR 워크스테이션
            </div>
            <h1 className="max-w-3xl text-[40px] leading-[1.02] tracking-[-0.05em] lg:text-[68px]">
              로그인은 늦게,
              <br />
              문서 생산성은
              <br />
              바로 시작.
            </h1>
            <p className="mt-6 max-w-2xl text-[16px] leading-7 text-[#5b554f] lg:text-[18px]">
              먼저 홈페이지를 둘러보고, 새 작업을 눌러 이미지를 올리는 순간에만 로그인하도록
              흐름을 바꿉니다. 로그인 후에는 OpenAI API key 연결을 우선 제안하고,
              연결하지 않으면 크레딧 구매로 자연스럽게 이어집니다.
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
                Access Policy
              </p>
              <div className="mt-5 space-y-4">
                <div className="flex items-start gap-3">
                  <KeyRound className="mt-0.5 h-5 w-5 text-[#f6c17f]" />
                  <div>
                    <p className="text-[15px]">OpenAI API key 우선 연결</p>
                    <p className="mt-1 text-[13px] leading-6 text-white/65">
                      무료 처리 모드는 사용자 소유 키를 사용합니다.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-0.5 h-5 w-5 text-[#9bd2c5]" />
                  <div>
                    <p className="text-[15px]">성공 시점 과금</p>
                    <p className="mt-1 text-[13px] leading-6 text-white/65">
                      OCR 완료 및 결과 저장 성공 후에만 크레딧을 1회 차감합니다.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[30px] border border-black/5 bg-[#ebe4d7] p-7">
              <p className="text-[12px] uppercase tracking-[0.2em] text-[#7b6b58]">
                Editor Rule
              </p>
              <p className="mt-4 text-[20px] leading-8 tracking-[-0.03em]">
                SVG 편집기는 유지합니다.
                <br />
                선, 점선, 곡선, 텍스트 보정은 그대로.
              </p>
              <p className="mt-4 text-[14px] leading-6 text-[#645b53]">
                브라우저 편집 품질 자체는 후속 과제로 두고, 이번 단계는 저장 규칙과 HWPX 반영
                경로를 깨지 않는 데 집중합니다.
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
              <h2 className="mt-3 text-[24px] tracking-[-0.03em]">{step.title}</h2>
              <p className="mt-3 text-[14px] leading-6 text-[#615950]">{step.body}</p>
            </motion.div>
          ))}
        </section>
      </main>
    </div>
  );
}
