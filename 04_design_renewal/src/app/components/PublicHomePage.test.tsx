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

  it("검색 의도형 소개와 주요 섹션을 노출한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getAllByText("MathHWP").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", {
        name: "수식 OCR로 이미지 수식을 편집 가능한 한글 수식으로 바꾸는 MathHWP",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/MathHWP는 수학 OCR, 수식 이미지 변환, 수식 한글 변환 워크플로를 하나의 작업실에서 연결합니다\./)
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "수학 OCR이 필요한 순간마다 바로 쓰는 핵심 기능" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "입력 형식과 결과물을 한눈에 확인하세요" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "학생, 교사, 문서 작성자에게 맞는 활용 방식" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "자주 묻는 질문" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "업로드 전 확인할 개인정보·작업 가이드" })).toBeInTheDocument();
    expect(screen.getByText("PDF 수식 OCR도 가능한가요?")).toBeInTheDocument();
  });

  it("홈 헤더와 CTA는 크롤 가능한 링크를 제공한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.getByRole("link", { name: "기능" })).toHaveAttribute("href", "#features");
    expect(screen.getByRole("link", { name: "지원 형식" })).toHaveAttribute("href", "#formats");
    expect(screen.getByRole("link", { name: "FAQ" })).toHaveAttribute("href", "#faq");
    expect(screen.getAllByRole("link", { name: "수식 변환 시작" })[0]).toHaveAttribute("href", "/new");
    expect(screen.getAllByRole("link", { name: "가격 보기" })[0]).toHaveAttribute("href", "/pricing");
    expect(screen.getByRole("link", { name: "로그인" })).toHaveAttribute("href", "/login");
  });

  it("현재 서비스 흐름에 맞는 CTA와 이미지 자산을 노출한다", () => {
    const { container } = render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(screen.getAllByRole("link", { name: "수식 변환 시작" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "가격 보기" })).toHaveLength(2);
    expect(screen.getByRole("link", { name: "로그인" })).toBeInTheDocument();

    const sourceImage = screen.getByAltText("원본 수학 문제 이미지");
    const resultImage = screen.getByAltText("OCR 이후 편집 가능한 HWPX 결과 미리보기");

    expect(sourceImage).toHaveAttribute("src", expect.stringContaining("home-source-problem"));
    expect(sourceImage).toHaveClass("object-contain");
    expect(resultImage).toHaveAttribute("src", expect.stringContaining("home-ocr-result"));
    expect(resultImage).toHaveClass("object-contain");
    expect(sourceImage).toHaveAttribute("loading", "lazy");
    expect(resultImage).toHaveAttribute("loading", "lazy");
    expect(container.querySelector(".public-home-hero-noise")).not.toBeInTheDocument();
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

    expect(container.querySelector(".public-home-hero-poster")).toBeInTheDocument();

    fireEvent.loadedData(heroVideo);

    expect(container.querySelector(".public-home-hero-poster")).not.toBeInTheDocument();

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

  it("FAQ와 개인정보 안내 문구를 노출한다", () => {
    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    expect(
      screen.getByText("직접 PDF 업로드는 아직 지원하지 않지만, PDF 페이지를 이미지로 추출하면 같은 수식 OCR 흐름으로 작업할 수 있습니다.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("파일 선택과 영역 지정은 로그인 없이 진행하고, 파이프라인 실행 직전에만 로그인합니다.")
    ).toBeInTheDocument();
  });

  it("링크 CTA를 클릭해도 기존 목적지로 이동한다", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <PublicHomePage />
      </MemoryRouter>
    );

    const heroTryLink = screen.getAllByRole("link", { name: "수식 변환 시작" })[0];
    const heroPricingLink = screen.getAllByRole("link", { name: "가격 보기" })[0];

    await user.click(heroTryLink);
    await user.click(heroPricingLink);

    expect(mockNavigate).not.toHaveBeenCalled();
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
