import { motion } from "motion/react";
import { useState, type CSSProperties } from "react";
import { Link } from "react-router";

import heroTimelapseMp4 from "@/assets/home/hero-timelapse.mp4";
import heroTimelapsePoster from "@/assets/home/hero-timelapse-poster.jpg";
import heroTimelapseWebm from "@/assets/home/hero-timelapse.webm";
import homeOcrResultImage from "@/assets/home/home-ocr-result.png";
import homeSourceProblemImage from "@/assets/home/home-source-problem.png";

import { Button } from "./ui/button";

type NavigationItem = {
  href: string;
  label: string;
};

type BenefitItem = {
  description: string;
  title: string;
};

type FormatGroup = {
  items: string[];
  title: string;
};

type UseCaseItem = {
  description: string;
  title: string;
};

type FaqItem = {
  answer: string;
  question: string;
};

type PreviewCardProps = {
  alt: string;
  description: string;
  imageSrc: string;
  label: string;
  title: string;
};

type SectionHeadingProps = {
  description: string;
  eyebrow: string;
  id: string;
  title: string;
};

type ActionLinksProps = {
  alignCenter?: boolean;
};

const navigationItems: NavigationItem[] = [
  { href: "#features", label: "기능" },
  { href: "#formats", label: "지원 형식" },
  { href: "#faq", label: "FAQ" },
];

const benefitItems: BenefitItem[] = [
  {
    title: "수학 OCR",
    description:
      "분수, 적분, 기하 기호가 섞인 문제 사진도 구조를 유지한 채 읽어 학생과 교사가 다시 타이핑하는 시간을 줄입니다.",
  },
  {
    title: "수식 한글 변환",
    description:
      "수식 이미지 변환 결과를 편집 가능한 HWPX 흐름으로 이어 문서 수정, 배포용 유인물 제작, 시험지 편집을 빠르게 진행할 수 있습니다.",
  },
  {
    title: "영역 지정 작업실",
    description:
      "필요한 문제만 선택해 OCR, 해설, 이미지 생성 범위를 조절할 수 있어 수업 자료와 풀이 문서를 목적에 맞게 정리하기 쉽습니다.",
  },
];

const formatGroups: FormatGroup[] = [
  {
    title: "입력 형식",
    items: ["PNG", "JPG", "JPEG", "PDF에서 추출한 문제 이미지"],
  },
  {
    title: "출력 결과",
    items: ["편집 가능한 HWPX", "수식 OCR 결과", "영역별 해설 초안"],
  },
];

const useCaseItems: UseCaseItem[] = [
  {
    title: "학생",
    description:
      "풀이 정리, 오답노트, 과제 제출 문서를 만들 때 손글씨나 문제집 이미지를 수식 OCR로 빠르게 편집 가능한 문서로 정리합니다.",
  },
  {
    title: "교사",
    description:
      "시험지, 프린트, 수업용 슬라이드 원고를 만들 때 기존 문제 이미지를 다시 입력하지 않고 수식 한글 변환 workflow로 재활용합니다.",
  },
  {
    title: "문서 작성자",
    description:
      "학원 교재, 해설집, 수학 자료집을 만들 때 문제 사진에서 편집 가능한 수식 문서를 뽑아 반복 편집 비용을 줄입니다.",
  },
];

const faqItems: FaqItem[] = [
  {
    question: "PDF 수식 OCR도 가능한가요?",
    answer:
      "직접 PDF 업로드는 아직 지원하지 않지만, PDF 페이지를 이미지로 추출하면 같은 수식 OCR 흐름으로 작업할 수 있습니다.",
  },
  {
    question: "수식 한글 변환 결과는 수정할 수 있나요?",
    answer:
      "결과는 편집 가능한 HWPX 흐름을 기준으로 설계되어, 문제지나 해설 문서를 다시 입력하지 않고 수정하는 작업에 맞춰져 있습니다.",
  },
  {
    question: "로그인 없이도 미리 작업할 수 있나요?",
    answer:
      "로그인 전에도 파일 선택과 영역 지정은 가능하며, 실제 파이프라인 실행 시점에만 로그인 절차가 필요합니다.",
  },
  {
    question: "누가 가장 많이 활용하나요?",
    answer:
      "수학 자료를 준비하는 학생, 교사, 문서 작성자가 반복 입력 시간을 줄이기 위해 가장 많이 활용할 수 있는 흐름으로 설계했습니다.",
  },
];

const heroMediaVisualTokens = {
  "--hero-media-position": "32% center",
  "--hero-overlay-background":
    "linear-gradient(180deg, rgba(1, 3, 4, 0.48) 0%, rgba(1, 3, 4, 0.16) 38%, rgba(0, 0, 0, 0.66) 100%), radial-gradient(circle at top center, rgba(255, 255, 255, 0.05) 0%, transparent 34%)",
  "--hero-poster-filter": "grayscale(1) brightness(1.16) contrast(1.22)",
  "--hero-poster-opacity": "0.46",
  "--hero-video-filter": "grayscale(1) brightness(1.42) contrast(1.46)",
  "--hero-video-opacity": "0.9",
} as CSSProperties;

const primaryButtonClassName =
  "h-12 rounded-full bg-white px-7 text-[13px] font-semibold tracking-[0.16em] text-black hover:bg-neutral-200";

const secondaryButtonClassName =
  "h-12 rounded-full border border-[var(--home-border-strong)] bg-transparent px-7 text-[13px] font-semibold text-white hover:bg-white hover:text-black";

/** 섹션 진입 애니메이션 공통값을 만든다. */
function getRevealMotion(delay = 0, distance = 24) {
  return {
    initial: { opacity: 0, y: distance },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.85, delay, ease: [0.16, 1, 0.3, 1] },
  } as const;
}

/** 섹션 상단에 공통적으로 쓰는 제목 블록을 렌더링한다. */
function SectionHeading({ description, eyebrow, id, title }: SectionHeadingProps) {
  return (
    <div className="mx-auto mb-12 max-w-3xl text-center">
      <p className="text-[11px] font-semibold uppercase tracking-[0.34em] text-[var(--home-ink-soft)]">
        {eyebrow}
      </p>
      <h2 id={id} className="mt-4 text-[clamp(2rem,4.2vw,3.4rem)] font-black tracking-[-0.05em] text-[var(--home-ink)]">
        {title}
      </h2>
      <p className="mt-4 text-[15px] leading-8 text-[var(--home-ink-muted)]">{description}</p>
    </div>
  );
}

/** 상단 네비게이션에 홈/섹션/로그인 링크를 노출한다. */
function TopNavigation() {
  return (
    <header className="glass-nav sticky top-0 z-40 border-b border-white/10 px-6 py-4" role="banner">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
        <Link to="/" className="text-sm font-semibold uppercase tracking-[0.34em] text-[var(--home-ink)]">
          MathHWP
        </Link>
        <nav className="flex items-center gap-5 text-[13px] text-[var(--home-ink-muted)]">
          {navigationItems.map((item) => (
            <a key={item.href} href={item.href} className="transition-colors hover:text-[var(--home-ink)]">
              {item.label}
            </a>
          ))}
          <Link to="/pricing" className="transition-colors hover:text-[var(--home-ink)]">
            가격
          </Link>
          <Link to="/login" className="transition-colors hover:text-[var(--home-ink)]">
            로그인
          </Link>
        </nav>
      </div>
    </header>
  );
}

/** 주요 전환 CTA를 anchor 기반 내부 링크로 렌더링한다. */
function ActionLinks({ alignCenter = false }: ActionLinksProps) {
  const wrapperClassName = alignCenter ? "justify-center" : "justify-center md:justify-start";

  return (
    <div className={`flex flex-col gap-4 sm:flex-row ${wrapperClassName}`}>
      <Button asChild className={primaryButtonClassName}>
        <Link to="/new">수식 변환 시작</Link>
      </Button>
      <Button asChild variant="outline" className={secondaryButtonClassName}>
        <Link to="/pricing">가격 보기</Link>
      </Button>
    </div>
  );
}

/** 히어로 섹션의 배경 비디오와 포스터를 관리한다. */
function HeroBackgroundMedia() {
  const [hasVideoError, setHasVideoError] = useState(false);
  const [isVideoReady, setIsVideoReady] = useState(false);
  const shouldShowPoster = hasVideoError || !isVideoReady;

  return (
    <div className="public-home-hero-media" aria-hidden="true" style={heroMediaVisualTokens}>
      {shouldShowPoster ? (
        <div className="public-home-hero-poster" style={{ backgroundImage: `url(${heroTimelapsePoster})` }} />
      ) : null}
      {!hasVideoError ? (
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          aria-hidden="true"
          className="public-home-hero-video"
          poster={heroTimelapsePoster}
          onLoadedData={() => setIsVideoReady(true)}
          onError={() => setHasVideoError(true)}
        >
          <source src={heroTimelapseWebm} type="video/webm" />
          <source src={heroTimelapseMp4} type="video/mp4" />
        </video>
      ) : null}
      <div className="public-home-hero-overlay" />
    </div>
  );
}

/** 히어로 영역에 핵심 문구와 상단 CTA를 배치한다. */
function HeroSection() {
  return (
    <section className="public-home-hero-section relative flex min-h-[calc(100vh-73px)] items-center justify-center px-6 py-20 text-center">
      <HeroBackgroundMedia />
      <div className="glow-bg left-1/2 top-10 z-10 h-[34rem] w-[34rem] -translate-x-1/2" />
      <motion.div {...getRevealMotion(0.05, 18)} className="reveal relative z-20 mx-auto flex max-w-5xl flex-col items-center gap-8">
        <p className="rounded-full border border-white/12 bg-black/35 px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.32em] text-[var(--home-ink-soft)]">
          수학 OCR · 수식 이미지 변환 · 수식 한글 변환
        </p>
        <h1 aria-label="수식 OCR로 이미지 수식을 편집 가능한 한글 수식으로 바꾸는 MathHWP" className="hero-title text-[clamp(2.8rem,7.6vw,5.8rem)] font-black leading-[1.02] tracking-[-0.06em] text-[var(--home-ink)]">
          <span className="block">수식 OCR로 이미지 수식을</span>
          <span className="block">편집 가능한 한글 수식으로</span>
          <span className="block">바꾸는 MathHWP</span>
        </h1>
        <p className="max-w-3xl text-[15px] leading-8 text-[var(--home-ink-muted)] md:text-[17px]">
          MathHWP는 수학 OCR, 수식 이미지 변환, 수식 한글 변환 워크플로를 하나의 작업실에서 연결합니다. 문제 사진을 올리고 영역을 고르면 편집 가능한 HWPX 결과까지 빠르게 이어집니다.
        </p>
        <ActionLinks alignCenter />
      </motion.div>
    </section>
  );
}

/** 로컬 자산 기반의 입력/출력 예시 카드를 렌더링한다. */
function PreviewCard({ alt, description, imageSrc, label, title }: PreviewCardProps) {
  return (
    <div className="cosmos-card overflow-hidden rounded-[30px] border border-[var(--home-border)] bg-[var(--home-surface)] p-5">
      <div className="rounded-[24px] border border-[var(--home-border)] bg-black/70 p-5">
        <img alt={alt} src={imageSrc} loading="lazy" decoding="async" className="h-72 w-full object-contain" />
      </div>
      <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--home-ink-soft)]">{label}</p>
      <h3 className="mt-3 text-[1.5rem] font-black tracking-[-0.04em] text-[var(--home-ink)]">{title}</h3>
      <p className="mt-3 text-[14px] leading-7 text-[var(--home-ink-muted)]">{description}</p>
    </div>
  );
}

/** 입력 예시와 결과물 포맷을 한 화면에서 보여준다. */
function FormatsSection() {
  return (
    <section id="formats" className="mx-auto max-w-7xl px-6 py-24">
      <SectionHeading
        id="formats-heading"
        eyebrow="Formats"
        title="입력 형식과 결과물을 한눈에 확인하세요"
        description="현재 공개 작업실은 PNG, JPG, JPEG 이미지를 지원합니다. PDF 수식 OCR이 필요한 경우에는 페이지를 이미지로 추출해 같은 방식으로 작업을 이어갈 수 있습니다."
      />
      <div className="grid gap-8 lg:grid-cols-2">
        <PreviewCard
          alt="원본 수학 문제 이미지"
          imageSrc={homeSourceProblemImage}
          label="입력 예시"
          title="원본 수학 문제 이미지"
          description="문제집, 프린트, 손글씨 정리본처럼 다양한 수식 이미지에서 필요한 영역만 선택해 OCR 대상을 명확하게 잡을 수 있습니다."
        />
        <PreviewCard
          alt="OCR 이후 편집 가능한 HWPX 결과 미리보기"
          imageSrc={homeOcrResultImage}
          label="출력 예시"
          title="OCR 이후 편집 가능한 HWPX 결과"
          description="OCR 결과를 바로 확인하고, 편집 가능한 HWPX 흐름으로 이어 문서 작업과 해설 정리를 같은 컨텍스트에서 관리할 수 있습니다."
        />
      </div>
      <div className="mt-8 grid gap-6 md:grid-cols-2">
        {formatGroups.map((group) => (
          <div key={group.title} className="rounded-[28px] border border-[var(--home-border)] bg-[var(--home-surface)] p-6">
            <h3 className="text-[1.2rem] font-black tracking-[-0.03em] text-[var(--home-ink)]">{group.title}</h3>
            <ul className="mt-4 space-y-3 text-[14px] leading-7 text-[var(--home-ink-muted)]">
              {group.items.map((item) => (
                <li key={item} className="rounded-2xl border border-white/6 bg-black/20 px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

/** 검색 의도에 맞는 핵심 기능 카드를 카드 그리드로 보여준다. */
function FeaturesSection() {
  return (
    <section id="features" className="mx-auto max-w-7xl px-6 py-24">
      <SectionHeading
        id="features-heading"
        eyebrow="Features"
        title="수학 OCR이 필요한 순간마다 바로 쓰는 핵심 기능"
        description="MathHWP는 수식 OCR 결과만 보여주는 데서 멈추지 않고, 편집 가능한 문서 작업까지 연결되는 흐름에 맞춰 공개 홈과 작업실을 구성했습니다."
      />
      <div className="grid gap-6 md:grid-cols-3">
        {benefitItems.map((item, index) => (
          <motion.article key={item.title} {...getRevealMotion(0.06 + index * 0.08)} className="cosmos-card reveal rounded-[28px] border border-[var(--home-border)] bg-[var(--home-surface)] p-6">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--home-ink-soft)]">
              0{index + 1}
            </p>
            <h3 className="mt-4 text-[1.55rem] font-black tracking-[-0.04em] text-[var(--home-ink)]">{item.title}</h3>
            <p className="mt-4 text-[14px] leading-7 text-[var(--home-ink-muted)]">{item.description}</p>
          </motion.article>
        ))}
      </div>
    </section>
  );
}

/** 학생·교사·문서 작성자별 활용 사례를 분리해 보여준다. */
function UseCasesSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <SectionHeading
        id="use-cases-heading"
        eyebrow="Use Cases"
        title="학생, 교사, 문서 작성자에게 맞는 활용 방식"
        description="같은 수식 이미지라도 쓰는 목적은 다르기 때문에, 결과를 다시 손보는 사람들의 실제 문서 workflow를 기준으로 주요 활용 장면을 정리했습니다."
      />
      <div className="grid gap-6 md:grid-cols-3">
        {useCaseItems.map((item) => (
          <div key={item.title} className="rounded-[28px] border border-[var(--home-border)] bg-[var(--home-surface)] p-6">
            <h3 className="text-[1.45rem] font-black tracking-[-0.04em] text-[var(--home-ink)]">{item.title}</h3>
            <p className="mt-4 text-[14px] leading-7 text-[var(--home-ink-muted)]">{item.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/** FAQ 섹션에 검색 의도형 질문과 답변을 그대로 노출한다. */
function FaqSection() {
  return (
    <section id="faq" className="mx-auto max-w-7xl px-6 py-24">
      <SectionHeading
        id="faq-heading"
        eyebrow="FAQ"
        title="자주 묻는 질문"
        description="실제 사용 전에 가장 많이 확인하는 지원 범위, 출력 형태, 로그인 흐름, 활용 대상 질문을 한 번에 정리했습니다."
      />
      <div className="grid gap-5 md:grid-cols-2">
        {faqItems.map((item) => (
          <article key={item.question} className="rounded-[28px] border border-[var(--home-border)] bg-[var(--home-surface)] p-6">
            <h3 className="text-[1.15rem] font-black tracking-[-0.03em] text-[var(--home-ink)]">{item.question}</h3>
            <p className="mt-4 text-[14px] leading-7 text-[var(--home-ink-muted)]">{item.answer}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

/** 업로드 전 확인할 개인정보와 작업 범위 안내를 노출한다. */
function PrivacySection() {
  return (
    <section id="privacy" className="mx-auto max-w-7xl px-6 py-24">
      <SectionHeading
        id="privacy-heading"
        eyebrow="Privacy"
        title="업로드 전 확인할 개인정보·작업 가이드"
        description="민감한 수업 자료나 시험지 이미지를 다룰 때는, 필요한 범위만 선택하고 실행 전에 작업 범위를 점검하는 흐름이 중요합니다."
      />
      <div className="grid gap-6 md:grid-cols-3">
        <div className="rounded-[28px] border border-[var(--home-border)] bg-[var(--home-surface)] p-6">
          <h3 className="text-[1.2rem] font-black tracking-[-0.03em] text-[var(--home-ink)]">로그인 시점 최소화</h3>
          <p className="mt-4 text-[14px] leading-7 text-[var(--home-ink-muted)]">
            파일 선택과 영역 지정은 로그인 없이 진행하고, 파이프라인 실행 직전에만 로그인합니다.
          </p>
        </div>
        <div className="rounded-[28px] border border-[var(--home-border)] bg-[var(--home-surface)] p-6">
          <h3 className="text-[1.2rem] font-black tracking-[-0.03em] text-[var(--home-ink)]">필요한 문제만 선택</h3>
          <p className="mt-4 text-[14px] leading-7 text-[var(--home-ink-muted)]">
            업로드 전에 영역을 먼저 지정해 필요한 문제만 선택하면, 수식 OCR 대상과 해설 생성 범위를 문서 목적에 맞게 줄일 수 있습니다.
          </p>
        </div>
        <div className="rounded-[28px] border border-[var(--home-border)] bg-[var(--home-surface)] p-6">
          <h3 className="text-[1.2rem] font-black tracking-[-0.03em] text-[var(--home-ink)]">사전 점검 권장</h3>
          <p className="mt-4 text-[14px] leading-7 text-[var(--home-ink-muted)]">
            민감한 문서는 샘플 이미지로 먼저 workflow를 확인한 뒤 실제 수업 자료나 시험지 범위를 최소화해 적용하는 방식을 권장합니다.
          </p>
        </div>
      </div>
    </section>
  );
}

/** 하단 CTA에서 공개 작업실 진입을 다시 안내한다. */
function ClosingSection() {
  return (
    <section className="relative border-t border-[var(--home-border)] px-6 py-28 text-center">
      <div className="glow-bg left-1/2 top-1/2 h-[26rem] w-[26rem] -translate-x-1/2 -translate-y-1/2" />
      <motion.div {...getRevealMotion(0.05)} className="reveal relative mx-auto flex max-w-5xl flex-col items-center gap-8">
        <p className="text-[12px] font-semibold uppercase tracking-[0.72em] text-[var(--home-ink-soft)]">MathHWP workflow</p>
        <h2 className="text-[clamp(2.4rem,6vw,4.8rem)] font-black leading-[1.04] tracking-[-0.05em] text-[var(--home-ink)]">
          시험지, 프린트, 해설지 문서 작업을
          <span className="block">더 빠르게 이어가세요</span>
        </h2>
        <ActionLinks alignCenter />
      </motion.div>
    </section>
  );
}

/** 푸터에 브랜드와 보조 내부 링크를 남긴다. */
function HomeFooter() {
  return (
    <footer className="border-t border-[var(--home-border)] px-6 py-14">
      <motion.div {...getRevealMotion(0.05, 12)} className="reveal mx-auto flex max-w-7xl flex-col gap-4 text-[var(--home-ink-soft)] md:flex-row md:items-center md:justify-between">
        <p className="text-sm font-semibold uppercase tracking-[0.34em] text-[var(--home-ink)]">MathHWP</p>
        <div className="flex flex-wrap gap-x-8 gap-y-3 text-[12px] leading-6">
          <a href="#privacy" className="transition-colors hover:text-[var(--home-ink)]">개인정보 안내</a>
          <a href="#faq" className="transition-colors hover:text-[var(--home-ink)]">FAQ 바로가기</a>
          <Link to="/pricing" className="transition-colors hover:text-[var(--home-ink)]">가격</Link>
        </div>
      </motion.div>
    </footer>
  );
}

/** 공개 홈 랜딩 페이지 전체를 SEO 중심 구조로 조합한다. */
export function PublicHomePage() {
  return (
    <div className="public-home-page min-h-screen overflow-hidden bg-[var(--home-background)] text-[var(--home-ink)] selection:bg-white selection:text-black">
      <TopNavigation />
      <main className="relative">
        <HeroSection />
        <FeaturesSection />
        <FormatsSection />
        <UseCasesSection />
        <FaqSection />
        <PrivacySection />
        <ClosingSection />
      </main>
      <HomeFooter />
    </div>
  );
}
