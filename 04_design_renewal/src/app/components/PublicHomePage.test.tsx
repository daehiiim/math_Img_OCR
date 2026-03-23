import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";

const mockNavigate = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
  }),
}));

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");

  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { PublicHomePage } from "./PublicHomePage";

const originalMatchMedia = window.matchMedia;
const originalInnerWidth = window.innerWidth;

/** 히어로 비디오 노출 여부를 테스트할 수 있도록 반응형 환경을 흉내 낸다. */
function mockHeroMediaEnvironment({ allowMotion, isDesktop }: { allowMotion: boolean; isDesktop: boolean }) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    value: isDesktop ? 1440 : 390,
    writable: true,
  });

  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches:
      query === "(min-width: 768px)"
        ? isDesktop
        : query === "(prefers-reduced-motion: no-preference)"
          ? allowMotion
          : false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

describe("PublicHomePage", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockHeroMediaEnvironment({ allowMotion: true, isDesktop: true });
  });

  it("다크 랜딩 카피와 주요 섹션을 노출한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.queryByRole("banner")).not.toBeInTheDocument();
    expect(screen.getAllByText("Math OCR")).toHaveLength(1);
    expect(screen.getByRole("heading", { name: /수학\s*수식을\s*HWPX로,\s*완벽한\s*감각으로\./ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /수학문제 직접 타이핑하느라\s*힘들지 않았나요\?/ })).toBeInTheDocument();
    expect(screen.getByText("사진을 올리세요")).toBeInTheDocument();
    expect(screen.getByText("결과를 확인하세요")).toBeInTheDocument();
    expect(screen.getByText("당신의 작업 방식을")).toBeInTheDocument();
    expect(screen.getByText("혁신할 준비가 되셨나요?")).toBeInTheDocument();
    expect(screen.queryByText("무료로 이용하세요")).not.toBeInTheDocument();
    expect(screen.queryByText("Photo to HWPX")).not.toBeInTheDocument();
    expect(screen.queryByText("사진에서 구조를 읽고, 최종 결과를 HWPX까지 연결하는 수학 OCR 워크플로우.")).not.toBeInTheDocument();
    expect(screen.queryByText("문제 사진이 곧,")).not.toBeInTheDocument();
  });

  it("중앙 하이라이트 헤드라인은 원하는 두 줄 구조를 명시한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    const featureHeading = screen.getByRole("heading", { name: /수학문제 직접 타이핑하느라\s*힘들지 않았나요\?/ });
    const headingLines = featureHeading.querySelectorAll("span");

    expect(headingLines).toHaveLength(2);
    expect(headingLines[0]).toHaveTextContent("수학문제 직접 타이핑하느라");
    expect(headingLines[0]).toHaveClass("block", "md:whitespace-nowrap");
    expect(headingLines[1]).toHaveTextContent("힘들지 않았나요?");
    expect(headingLines[1]).toHaveClass("block");
    expect(featureHeading).toHaveClass("break-keep");
  });

  it("현재 서비스 흐름에 맞는 CTA와 이미지 자산을 노출한다", () => {
    const { container } = render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.getAllByRole("button", { name: "사용해보기" })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "가격 보기" })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "로그인" })).not.toBeInTheDocument();

    const sourceImage = screen.getByAltText("원본 이미지");
    const resultImage = screen.getByAltText("OCR 결과");
    const featureImage = screen.getByAltText("디지털 작업 공간");

    expect(sourceImage).toHaveAttribute("src", expect.stringContaining("home-source-problem"));
    expect(sourceImage).toHaveClass("object-contain");
    expect(resultImage).toHaveAttribute("src", expect.stringContaining("home-ocr-result"));
    expect(resultImage).toHaveClass("object-contain");
    expect(featureImage).toHaveClass("object-cover");
    expect(featureImage).not.toHaveClass("object-contain");
    expect(container.querySelector(".public-home-hero-noise")).not.toBeInTheDocument();
    expect(screen.queryByAltText("출력 형식")).not.toBeInTheDocument();
  });

  it("히어로 장식 비디오는 환경과 무관하게 렌더되고 기본 루프 재생을 유지한다", async () => {
    const { container } = render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    const heroVideo = await waitFor(() => {
      const videoElement = container.querySelector("video");
      expect(videoElement).not.toBeNull();
      return videoElement as HTMLVideoElement;
    });

    expect(heroVideo.autoplay).toBe(true);
    expect(heroVideo.muted).toBe(true);
    expect(heroVideo.loop).toBe(true);
    expect(heroVideo.playsInline).toBe(true);
    expect(heroVideo).toHaveAttribute("aria-hidden", "true");
    expect(heroVideo).toHaveAttribute("poster", expect.stringContaining("hero-timelapse-poster"));
    expect(heroVideo).toHaveAttribute("preload", "metadata");
    expect(heroVideo.querySelector('source[type="video/webm"]')).toHaveAttribute("src", expect.stringContaining("hero-timelapse"));
    expect(heroVideo.querySelector('source[type="video/mp4"]')).toHaveAttribute("src", expect.stringContaining("hero-timelapse"));

    const heroMedia = container.querySelector(".public-home-hero-media");

    expect(heroMedia).toHaveStyle({
      "--hero-media-position": "32% center",
      "--hero-poster-opacity": "0.46",
      "--hero-video-opacity": "0.9",
    });

    fireEvent.loadedMetadata(heroVideo);

    expect(heroVideo.currentTime).toBeCloseTo(0);
    expect(heroVideo.playbackRate).toBeCloseTo(1);

    heroVideo.currentTime = 5.8;
    fireEvent.timeUpdate(heroVideo);

    expect(heroVideo.currentTime).toBeCloseTo(5.8);
  });

  it("모바일 환경에서도 히어로 장식 비디오를 계속 렌더링한다", () => {
    mockHeroMediaEnvironment({ allowMotion: true, isDesktop: false });

    const { container } = render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(container.querySelector("video")).toBeInTheDocument();
  });

  it("감속 모드여도 히어로 장식 비디오를 계속 렌더링한다", () => {
    mockHeroMediaEnvironment({ allowMotion: false, isDesktop: true });

    const { container } = render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(container.querySelector("video")).toBeInTheDocument();
  });

  it("히어로와 하단 CTA가 기존 목적지로 이동한다", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    const heroTryButton = screen.getAllByRole("button", { name: "사용해보기" })[0];
    const heroPricingButton = screen.getAllByRole("button", { name: "가격 보기" })[0];

    await user.click(heroTryButton);
    await user.click(heroPricingButton);

    expect(mockNavigate).toHaveBeenCalledWith("/new");
    expect(mockNavigate).toHaveBeenCalledWith("/pricing");
  });

  it("외부 이미지가 실패하면 fallback 플레이스홀더를 보여준다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    fireEvent.error(screen.getByAltText("디지털 작업 공간"));

    expect(screen.getByAltText("Error loading image")).toBeInTheDocument();
  });
});

afterAll(() => {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    value: originalInnerWidth,
    writable: true,
  });
  window.matchMedia = originalMatchMedia;
});
