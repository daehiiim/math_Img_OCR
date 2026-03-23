import { motion } from "motion/react";
import { useState, type CSSProperties } from "react";
import { useNavigate } from "react-router";

import heroTimelapseMp4 from "@/assets/home/hero-timelapse.mp4";
import heroTimelapsePoster from "@/assets/home/hero-timelapse-poster.jpg";
import heroTimelapseWebm from "@/assets/home/hero-timelapse.webm";
import homeOcrResultImage from "@/assets/home/home-ocr-result.png";
import homeSourceProblemImage from "@/assets/home/home-source-problem.png";

import { ImageWithFallback } from "./figma/ImageWithFallback";
import { Button } from "./ui/button";

type LandingCard = {
  badge: string;
  title: string;
  description: string;
  imageAlt: string;
  imageSrc: string;
};

type ActionButtonsProps = {
  alignCenter?: boolean;
  onPricing: () => void;
  onTry: () => void;
};

type LandingCardImageProps = {
  card: LandingCard;
};

type LandingCardPanelProps = {
  card: LandingCard;
  index: number;
};

const heroWordRows = [
  ["수학", "수식을", "HWPX로,"],
  ["완벽한", "감각으로."],
];

const heroMediaVisualTokens = {
  "--hero-media-position": "32% center",
  "--hero-poster-opacity": "0.46",
  "--hero-poster-filter": "grayscale(1) brightness(1.16) contrast(1.22)",
  "--hero-video-opacity": "0.9",
  "--hero-video-filter": "grayscale(1) brightness(1.42) contrast(1.46)",
  "--hero-overlay-background":
    "linear-gradient(180deg, rgba(1, 3, 4, 0.48) 0%, rgba(1, 3, 4, 0.16) 38%, rgba(0, 0, 0, 0.66) 100%), radial-gradient(circle at top center, rgba(255, 255, 255, 0.05) 0%, transparent 34%)",
} as CSSProperties;

const middleFeatureImage =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuAUbOoVIra_wGGc0Y8fJTDtAOB9SyewR6KJw8YY4wtSdtUGyuuGDuHn189WHLiEKF0DQOAKabwg3dkUTBnFrJZYXKEIZix6MT8pS9aRoEV3kxHqe70hAuaDfhyhVrdfdJ_R-bRa1DE976ej6IJMY4DON08gdbhmeJF3c-jZauCXcfQmB6N96Vz72LIXZ06_8Ad64iZLdDHBRFCnLuPgjyhpateoHa88_Flu2s7X43bR07VocdjO98rKU8l5LxursfAiKrO8pWbVjLE";

const mainFeatureHeadingLines = ["수학문제 직접 타이핑하느라", "힘들지 않았나요?"] as const;

const landingCards: LandingCard[] = [
  {
    badge: "원본 사진",
    title: "사진을 올리세요",
    description:
      "어떤 필기나 복잡한 인쇄물이라도 원본의 의도를 완벽하게 파악합니다. 수학적 구조를 이해하는 인공지능이 텍스트 이상의 의미를 읽어냅니다.",
    imageAlt: "원본 이미지",
    imageSrc: homeSourceProblemImage,
  },
  {
    badge: "출력 결과",
    title: "결과를 확인하세요",
    description:
      "복잡한 적분이나 분수 등 수식 형태를 hwpx 형식으로 즉각 변환하여 한글에서 편집 가능한 상태로 제공합니다.",
    imageAlt: "OCR 결과",
    imageSrc: homeOcrResultImage,
  },
];

const primaryButtonClassName =
  "h-12 rounded-full bg-white px-7 text-[13px] font-semibold tracking-[0.16em] text-black hover:bg-neutral-200";

const secondaryButtonClassName =
  "h-12 rounded-full border border-[var(--home-border-strong)] bg-transparent px-7 text-[13px] font-semibold text-white hover:bg-white hover:text-black";

/** 모션 컴포넌트에 공통으로 사용할 진입 애니메이션 속성을 만든다. */
function getRevealMotion(delay = 0, distance = 24) {
  return {
    initial: { opacity: 0, y: distance },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.85, delay, ease: [0.16, 1, 0.3, 1] },
  } as const;
}

/** 헤더와 하단 CTA에서 공통으로 쓰는 버튼 그룹을 렌더링한다. */
function ActionButtons({ alignCenter = false, onPricing, onTry }: ActionButtonsProps) {
  const wrapperClassName = alignCenter ? "justify-center" : "justify-center md:justify-start";

  return (
    <div className={`flex flex-col gap-4 sm:flex-row ${wrapperClassName}`}>
      <Button onClick={onTry} className={primaryButtonClassName}>
        사용해보기
      </Button>
      <Button variant="outline" onClick={onPricing} className={secondaryButtonClassName}>
        가격 보기
      </Button>
    </div>
  );
}

/** 히어로 섹션 전용 배경 포스터와 조건부 비디오 레이어를 렌더링한다. */
function HeroBackgroundMedia() {
  const [hasVideoError, setHasVideoError] = useState(false);
  const fallbackReason = hasVideoError ? "video-unavailable" : null;

  return (
    <div className="public-home-hero-media" aria-hidden="true" data-hero-media-fallback={fallbackReason ?? undefined} style={heroMediaVisualTokens}>
      <div className="public-home-hero-poster" style={{ backgroundImage: `url(${heroTimelapsePoster})` }} />
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

/** 풀스크린 히어로 섹션과 대표 CTA를 렌더링한다. */
function HeroSection({ onPricing, onTry }: ActionButtonsProps) {
  return (
    <section className="public-home-hero-section relative flex min-h-screen items-center justify-center px-6 py-20 text-center">
      <HeroBackgroundMedia />
      <div className="glow-bg left-1/2 top-10 z-10 h-[34rem] w-[34rem] -translate-x-1/2" />
      <motion.div {...getRevealMotion(0.05, 18)} className="reveal relative z-20 mx-auto flex max-w-6xl flex-col items-center gap-12">
        <h1 className="hero-title text-[clamp(3.2rem,11vw,9rem)] font-black leading-[0.94] text-[var(--home-ink)]">
          {heroWordRows.map((wordRow, rowIndex) => (
            <span key={wordRow.join("-")} className="block">
              {wordRow.map((word, wordIndex) => (
                <span
                  key={word}
                  className="hero-word mr-[0.18em] inline-block last:mr-0"
                  style={{ "--word-delay": `${0.18 + rowIndex * 0.24 + wordIndex * 0.1}s` } as CSSProperties}
                >
                  {word}
                </span>
              ))}
            </span>
          ))}
        </h1>
        <ActionButtons onTry={onTry} onPricing={onPricing} alignCenter />
      </motion.div>
    </section>
  );
}

/** 중앙 하이라이트 섹션에 외부 대표 이미지를 안전하게 배치한다. */
function MainFeatureSection() {
  return (
    <section className="w-full px-6 pb-28">
      <motion.div {...getRevealMotion(0.05)} className="cosmos-card reveal mx-auto max-w-[1800px] overflow-hidden rounded-[42px] border border-[var(--home-border)] bg-[rgba(7,10,12,0.92)]">
        <div className="glow-bg left-1/2 top-1/2 h-[30rem] w-[30rem] -translate-x-1/2 -translate-y-1/2" />
        <div className="relative overflow-hidden border-y border-white/10">
          <ImageWithFallback
            alt="디지털 작업 공간"
            src={middleFeatureImage}
            className="h-[420px] w-full object-cover opacity-40 grayscale contrast-125"
          />
          <div className="absolute inset-0 flex items-center justify-center bg-black/48 px-8 text-center">
            <div className="max-w-3xl space-y-8">
              <h2 className="break-keep text-[clamp(2.2rem,5vw,4.5rem)] font-black leading-[1.04] tracking-[-0.05em] text-white">
                <span className="block md:whitespace-nowrap">{mainFeatureHeadingLines[0]}</span>
                <span className="block">{mainFeatureHeadingLines[1]}</span>
              </h2>
              <p className="text-sm font-medium leading-8 tracking-[0.08em] text-neutral-300 md:text-base">사진만 찍으면 바로 출력가능한 한글파일로 변환해줍니다.</p>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

/** 카드 이미지를 원본 비율이 유지되도록 안전하게 렌더링한다. */
function LandingCardImage({ card }: LandingCardImageProps) {
  const imageClassName = "h-80 w-full object-contain p-4 opacity-90 transition-opacity duration-500 group-hover:opacity-100";

  return <img alt={card.imageAlt} src={card.imageSrc} className={imageClassName} />;
}

/** 랜딩 카드 한 장의 이미지와 설명을 렌더링한다. */
function LandingCardPanel({ card, index }: LandingCardPanelProps) {
  return (
    <motion.article {...getRevealMotion(0.08 + index * 0.08)} className="cosmos-card reveal rounded-[32px] border border-[var(--home-border)] bg-[var(--home-surface)] p-4 sm:p-5">
      <div className="group relative overflow-hidden rounded-[26px] border border-[var(--home-border)] bg-black/70">
        <div className="glow-bg" />
        <LandingCardImage card={card} />
        <span className="absolute left-5 top-5 rounded-full border border-white/12 bg-black/40 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-white/70 backdrop-blur">{card.badge}</span>
      </div>
      <div className="mt-6 space-y-4 px-1 pb-1">
        <h3 className="text-[1.65rem] font-black leading-[1.08] tracking-[-0.05em] text-[var(--home-ink)]">{card.title}</h3>
        <p className="text-sm leading-7 text-[var(--home-ink-muted)]">{card.description}</p>
      </div>
    </motion.article>
  );
}

/** 세 장의 핵심 카드로 업로드부터 결과 확인까지의 흐름을 보여준다. */
function LandingCardsSection() {
  return (
    <section className="mx-auto max-w-[1400px] px-6 pb-32">
      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 xl:gap-10">
        {landingCards.map((card, index) => (
          <LandingCardPanel key={card.title} card={card} index={index} />
        ))}
      </div>
    </section>
  );
}

/** 하단 전환 섹션에서 동일한 CTA를 다시 노출한다. */
function ClosingSection({ onPricing, onTry }: ActionButtonsProps) {
  return (
    <section className="relative border-t border-[var(--home-border)] px-6 py-32 text-center">
      <div className="glow-bg left-1/2 top-1/2 h-[28rem] w-[28rem] -translate-x-1/2 -translate-y-1/2" />
      <motion.div {...getRevealMotion(0.05)} className="reveal relative mx-auto flex max-w-5xl flex-col items-center gap-8">
        <span className="text-[12px] font-semibold uppercase tracking-[0.72em] text-[var(--home-ink-soft)]">사진만 찍으면 끝이니까</span>
        <h2 className="text-[clamp(2.6rem,6vw,5.8rem)] font-black leading-[1.02] tracking-[-0.05em] text-[var(--home-ink)]">
          당신의 작업 방식을
          <span className="block">혁신할 준비가 되셨나요?</span>
        </h2>
        <ActionButtons onTry={onTry} onPricing={onPricing} alignCenter />
      </motion.div>
    </section>
  );
}

/** 공개 홈 마지막 영역에 서비스명과 안내 문구를 배치한다. */
function HomeFooter() {
  return (
    <footer className="border-t border-[var(--home-border)] px-6 py-14">
      <motion.div {...getRevealMotion(0.05, 12)} className="reveal mx-auto flex max-w-[1800px] flex-col gap-6 text-[var(--home-ink-soft)] md:flex-row md:items-center md:justify-between">
        <p className="text-sm font-semibold uppercase tracking-[0.34em] text-[var(--home-ink)]">Math OCR</p>
        <div className="flex flex-wrap gap-x-10 gap-y-3 text-[11px] font-medium uppercase tracking-[0.28em]">
          <span>개인정보 처리방침</span>
          <span>이용약관</span>
        </div>
      </motion.div>
    </footer>
  );
}

/** 공개 홈 랜딩 페이지 전체를 다크 풀스크린 구조로 조합한다. */
export function PublicHomePage() {
  const navigate = useNavigate();

  return (
    <div className="public-home-page min-h-screen overflow-hidden bg-[var(--home-background)] text-[var(--home-ink)] selection:bg-white selection:text-black">
      <main className="relative">
        <HeroSection onTry={() => navigate("/new")} onPricing={() => navigate("/pricing")} />
        <MainFeatureSection />
        <LandingCardsSection />
        <ClosingSection onTry={() => navigate("/new")} onPricing={() => navigate("/pricing")} />
      </main>
      <HomeFooter />
    </div>
  );
}
