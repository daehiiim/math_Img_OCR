import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import { SeoManager } from "./SeoManager";

describe("SeoManager", () => {
  afterEach(() => {
    document.head.innerHTML = "";
  });

  it("홈 경로에서 title, canonical, 설명과 JSON-LD를 설정한다", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <SeoManager />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(document.title).toBe(
        "수식 OCR로 이미지 수식을 편집 가능한 한글 문서로 변환 | MathHWP"
      );
    });

    expect(
      document.head.querySelector('link[rel="canonical"]')
    )?.toHaveAttribute("href", "https://mathhwp.vercel.app/");
    expect(
      document.head.querySelector('meta[name="description"]')
    )?.toHaveAttribute(
      "content",
      expect.stringContaining("수학 OCR")
    );
    expect(
      document.head.querySelector('script[data-seo-structured-data="home"]')
    )?.toBeInTheDocument();
  });

  it("로그인 경로에서 noindex와 route canonical을 설정한다", async () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <SeoManager />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(document.title).toBe("로그인 | MathHWP");
    });

    expect(
      document.head.querySelector('meta[name="robots"]')
    )?.toHaveAttribute("content", "noindex,nofollow");
    expect(
      document.head.querySelector('link[rel="canonical"]')
    )?.toHaveAttribute("href", "https://mathhwp.vercel.app/login");
    expect(
      document.head.querySelector('script[data-seo-structured-data="home"]')
    ).not.toBeInTheDocument();
  });
});
