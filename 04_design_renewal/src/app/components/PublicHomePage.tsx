import { ArrowRight } from "lucide-react";
import { motion } from "motion/react";
import { useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { Button } from "./ui/button";

type UsageItem = {
  label: string;
  body: string;
};

type LandingBand = {
  step: string;
  title: string;
  body: string;
  artifactLabel: string;
  artifactNote: string;
  accentClassName: string;
};

const usageItems: UsageItem[] = [
  {
    label: "OCR·해설은 본인 OpenAI API key로 처리",
    body: "문항 인식과 해설 생성은 본인 키로 돌리고, 서비스는 작업 흐름만 정돈합니다.",
  },
  {
    label: "이미지 생성은 충전한 크레딧으로 진행",
    body: "로그인 후 크레딧을 연결하면 이미지 생성과 전체 자동 처리를 바로 이어갈 수 있습니다.",
  },
];

const landingBands: LandingBand[] = [
  {
    step: "01",
    title: "사진을 올리면 정리됩니다.",
    body: "시험지, 프린트물, 풀이를 올리면 문항과 해설, 이미지가 한 흐름으로 정돈됩니다.",
    artifactLabel: "Source Sheet",
    artifactNote: "Photo to structure",
    accentClassName: "from-black/10 via-black/0 to-transparent",
  },
  {
    step: "02",
    title: "결과를 보고 다듬습니다.",
    body: "자동으로 정리된 결과를 검토하고, 필요한 부분만 짧게 수정해 문서 톤을 맞춥니다.",
    artifactLabel: "Review Pass",
    artifactNote: "Quiet adjustments",
    accentClassName: "from-black/0 via-black/10 to-transparent",
  },
  {
    step: "03",
    title: "끝은 한글 문서입니다.",
    body: "마지막에는 HWPX로 내보내어 바로 배포할 수 있는 결과물로 마무리합니다.",
    artifactLabel: "HWPX Output",
    artifactNote: "Ready to hand off",
    accentClassName: "from-transparent via-black/10 to-black/0",
  },
];

type HomeHeaderProps = {
  accountLabel: string;
  onAccount: () => void;
  onHome: () => void;
};

/** 공개 홈 상단의 조용한 네비게이션을 렌더링한다. */
function HomeHeader({ accountLabel, onAccount, onHome }: HomeHeaderProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-[var(--landing-border)] bg-[color:rgba(244,239,230,0.84)] backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
        <button onClick={onHome} className="flex items-center gap-3 text-left">
          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[var(--landing-border-strong)] text-[11px] uppercase tracking-[0.3em] text-[var(--landing-ink)]">
            M
          </div>
          <div className="space-y-1">
            <p className="landing-heading text-[21px] font-semibold leading-none tracking-[-0.035em] text-[var(--landing-ink)]">MATH OCR</p>
            <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--landing-ink-soft)]">Image to HWPX</p>
          </div>
        </button>

        <Button
          variant="outline"
          onClick={onAccount}
          className="h-10 rounded-full border-[var(--landing-border)] bg-transparent px-4 text-[13px] font-medium text-[var(--landing-ink)] shadow-none hover:bg-black/[0.03]"
        >
          {accountLabel}
        </Button>
      </div>
    </header>
  );
}

type HeroSectionProps = {
  onNewJob: () => void;
  onPricing: () => void;
};

/** 공개 홈 첫 화면의 핵심 카피와 CTA를 렌더링한다. */
function HeroSection({ onNewJob, onPricing }: HeroSectionProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55 }}
      className="pt-8 lg:pt-14"
    >
      <p className="text-[11px] uppercase tracking-[0.34em] text-[var(--landing-ink-soft)]">Editorial OCR Flow</p>
      <h1 className="mt-7 max-w-5xl landing-heading landing-tracking-display text-[clamp(2.7rem,11vw,6.1rem)] font-semibold leading-[0.92] text-[var(--landing-ink)]">
        문제 사진이 곧,{" "}
        <span className="block">한글 문서가 됩니다.</span>
      </h1>
      <p className="mt-8 max-w-2xl text-[16px] leading-7 text-[var(--landing-ink-muted)] sm:text-[18px]">
        <span className="block">로그인 없이 첫 작업을 시작하고,</span>
        <span className="block">사진에서 HWPX까지 한 흐름으로 이어갑니다.</span>
      </p>
      <div className="mt-10 flex flex-wrap gap-3">
        <Button
          onClick={onNewJob}
          className="h-11 rounded-full bg-[var(--landing-ink)] px-5 text-[13px] font-medium text-[var(--landing-background)] hover:bg-black"
        >
          새 작업 시작
          <ArrowRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          onClick={onPricing}
          className="h-11 rounded-full border-[var(--landing-border)] bg-transparent px-5 text-[13px] font-medium text-[var(--landing-ink)] shadow-none hover:bg-black/[0.03]"
        >
          가격 보기
        </Button>
      </div>
    </motion.section>
  );
}

/** 공개 홈의 추상적 문서 오브제를 렌더링한다. */
function HeroArtifact() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 22 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, delay: 0.08 }}
      className="relative overflow-hidden rounded-[34px] border border-[var(--landing-border)] bg-[linear-gradient(145deg,rgba(255,255,255,0.78),rgba(255,255,255,0.46))] p-7"
    >
      <div className="absolute inset-x-8 top-7 h-px bg-[var(--landing-border)]" />
      <div className="absolute -right-10 top-14 h-44 w-44 rounded-full border border-[var(--landing-border)]" />
      <div className="absolute left-12 top-16 h-52 w-40 rounded-[26px] border border-[var(--landing-border)] bg-[rgba(255,255,255,0.58)]" />
      <div className="absolute right-8 top-24 h-48 w-40 rounded-[30px] border border-[var(--landing-border)] bg-[rgba(20,17,13,0.04)]" />
      <div className="relative flex min-h-[280px] flex-col justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--landing-ink-soft)]">Quiet Object</p>
          <p className="mt-5 landing-heading text-[52px] font-semibold leading-none tracking-[-0.05em] text-[var(--landing-ink)]">OCR</p>
          <p className="mt-2 text-[13px] leading-6 text-[var(--landing-ink-muted)]">Photo in. Structure first.</p>
        </div>
        <div className="ml-auto w-full max-w-[220px] rounded-[26px] border border-[var(--landing-border)] bg-[rgba(255,255,255,0.62)] p-5">
          <p className="landing-heading text-[39px] font-semibold leading-none tracking-[-0.05em] text-[var(--landing-ink)]">HWPX</p>
          <p className="mt-2 text-[12px] uppercase tracking-[0.22em] text-[var(--landing-ink-soft)]">Document Out</p>
        </div>
      </div>
    </motion.div>
  );
}

/** 공개 홈의 사용 방식을 세로 정보 블록으로 요약한다. */
function UsagePanel() {
  return (
    <section className="rounded-[34px] border border-[var(--landing-border)] bg-[rgba(255,255,255,0.54)] p-6">
      <p className="text-[11px] uppercase tracking-[0.3em] text-[var(--landing-ink-soft)]">사용 방식</p>
      <div className="mt-6 divide-y divide-[var(--landing-border)]">
        {usageItems.map((item, index) => (
          <div key={item.label} className="grid gap-3 py-4 sm:grid-cols-[54px_1fr]">
            <p className="landing-heading text-[27px] font-semibold leading-none tracking-[-0.04em] text-[var(--landing-ink)]">{`0${index + 1}`}</p>
            <div className="space-y-2">
              <p className="text-[15px] leading-6 text-[var(--landing-ink)]">{item.label}</p>
              <p className="text-[13px] leading-6 text-[var(--landing-ink-muted)]">{item.body}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/** 공개 홈의 보조 하이라이트 메시지를 렌더링한다. */
function HighlightPanel() {
  return (
    <section className="rounded-[34px] border border-[var(--landing-border-strong)] bg-[var(--landing-ink)] p-6 text-[var(--landing-background)]">
      <p className="text-[11px] uppercase tracking-[0.28em] text-white/45">출력 감각</p>
      <h2 className="mt-5 landing-heading landing-tracking-title text-[31px] font-semibold leading-[1.05]">
        붙여넣기보다,{" "}
        <span className="block">문서에 가깝게.</span>
      </h2>
      <p className="mt-4 text-[14px] leading-7 text-white/68">
        캡처를 옮겨 붙인 결과가 아니라, 바로 전달 가능한 문서의 결을 남기도록 화면을 정리합니다.
      </p>
    </section>
  );
}

type BandArtifactProps = Pick<LandingBand, "accentClassName" | "artifactLabel" | "artifactNote">;

/** 정보 밴드 안의 종이형 시각 요소를 렌더링한다. */
function BandArtifact({ accentClassName, artifactLabel, artifactNote }: BandArtifactProps) {
  return (
    <div className="relative min-h-[220px] overflow-hidden rounded-[30px] border border-[var(--landing-border)] bg-[rgba(255,255,255,0.56)]">
      <div className={`absolute inset-0 bg-[linear-gradient(135deg,var(--tw-gradient-stops))] ${accentClassName}`} />
      <div className="absolute left-6 top-6 h-32 w-24 rounded-[20px] border border-[var(--landing-border)] bg-[rgba(255,255,255,0.7)]" />
      <div className="absolute right-6 top-12 h-36 w-28 rounded-[24px] border border-[var(--landing-border)] bg-[rgba(255,255,255,0.44)]" />
      <div className="absolute bottom-6 left-6 right-6 rounded-[22px] border border-[var(--landing-border)] bg-[rgba(20,17,13,0.04)] p-5">
        <p className="landing-heading text-[30px] font-semibold leading-none tracking-[-0.045em] text-[var(--landing-ink)]">{artifactLabel}</p>
        <p className="mt-2 text-[11px] uppercase tracking-[0.24em] text-[var(--landing-ink-soft)]">{artifactNote}</p>
      </div>
    </div>
  );
}

type LandingBandCardProps = {
  band: LandingBand;
  index: number;
};

/** 공개 홈의 단계별 정보 밴드를 렌더링한다. */
function LandingBandCard({ band, index }: LandingBandCardProps) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: 0.14 + index * 0.08 }}
      className="grid gap-8 rounded-[36px] border border-[var(--landing-border)] bg-[rgba(255,255,255,0.58)] p-6 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-center lg:p-10"
    >
      <div>
        <p className="text-[12px] uppercase tracking-[0.28em] text-[var(--landing-ink-soft)]">{`Step ${band.step}`}</p>
        <h3 className="mt-4 landing-heading landing-tracking-title text-[clamp(2rem,4vw,3.5rem)] font-semibold leading-[1.02] text-[var(--landing-ink)]">
          {band.title}
        </h3>
        <p className="mt-5 max-w-xl text-[15px] leading-7 text-[var(--landing-ink-muted)]">{band.body}</p>
      </div>
      <BandArtifact
        accentClassName={band.accentClassName}
        artifactLabel={band.artifactLabel}
        artifactNote={band.artifactNote}
      />
    </motion.article>
  );
}

/** 공개 홈의 전체 랜딩 구조를 조합한다. */
export function PublicHomePage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const accountLabel = isAuthenticated ? "내 작업실" : "로그인";
  const accountTarget = isAuthenticated ? "/workspace" : "/login";

  return (
    <div className="min-h-screen bg-[var(--landing-background)] text-[var(--landing-ink)]">
      <HomeHeader accountLabel={accountLabel} onAccount={() => navigate(accountTarget)} onHome={() => navigate("/")} />
      <main className="mx-auto flex max-w-7xl flex-col gap-14 px-5 pb-16 lg:px-8 lg:pb-24">
        <section className="grid gap-10 border-b border-[var(--landing-border)] pb-16 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:gap-14 lg:pb-20">
          <HeroSection onNewJob={() => navigate("/new")} onPricing={() => navigate("/pricing")} />
          <div className="grid gap-4 lg:pt-16">
            <HeroArtifact />
            <UsagePanel />
            <HighlightPanel />
          </div>
        </section>

        <section className="space-y-6">
          <div className="flex flex-col gap-4 border-b border-[var(--landing-border)] pb-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.3em] text-[var(--landing-ink-soft)]">How It Moves</p>
              <h2 className="mt-4 max-w-3xl landing-heading landing-tracking-title text-[clamp(2.2rem,5vw,4.2rem)] font-semibold leading-[1.02] text-[var(--landing-ink)]">
                길게 설명하지 않아도{" "}
                <span className="block">흐름은 분명합니다.</span>
              </h2>
            </div>
            <p className="max-w-md text-[14px] leading-7 text-[var(--landing-ink-muted)]">
              업로드, 검토, HWPX 출력까지 공개 홈에서 보여주는 흐름만 더 조용하고 크게 드러냅니다.
            </p>
          </div>

          {landingBands.map((band, index) => (
            <LandingBandCard key={band.step} band={band} index={index} />
          ))}
        </section>
      </main>
    </div>
  );
}
