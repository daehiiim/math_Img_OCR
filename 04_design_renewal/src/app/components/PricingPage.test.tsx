import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getBillingCatalogApiMock } = vi.hoisted(() => ({
  getBillingCatalogApiMock: vi.fn(),
}));

vi.mock("../api/billingApi", () => ({
  getBillingCatalogApi: getBillingCatalogApiMock,
}));

import { PricingPage } from "./PricingPage";

describe("PricingPage", () => {
  beforeEach(() => {
    getBillingCatalogApiMock.mockResolvedValue([
      { plan_id: "single", title: "Single", amount: 100, currency: "krw", credits: 1 },
      { plan_id: "starter", title: "Starter", amount: 9900, currency: "krw", credits: 100 },
      { plan_id: "pro", title: "Pro", amount: 19000, currency: "krw", credits: 200 },
    ]);
  });

  it("catalog 기준 통화와 checkout 안내를 노출한다", async () => {
    render(
      <MemoryRouter>
        <PricingPage />
      </MemoryRouter>
    );

    expect(screen.getByRole("region", { name: "상단 안내 surface" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "plan surface" })).toBeInTheDocument();
    expect(await screen.findByText("₩9,900")).toBeInTheDocument();
    expect(screen.getAllByText("KRW").length).toBeGreaterThan(0);
    expect(screen.getByText("실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.")).toBeInTheDocument();
  });

  it("비홈 결제 페이지 셸에 글라스 과금 스코프를 적용한다", async () => {
    render(
      <MemoryRouter>
        <PricingPage />
      </MemoryRouter>
    );

    const title = await screen.findByRole("heading", { name: "이미지 구매" });

    expect(title.closest(".liquid-page-shell")).toHaveClass(
      "liquid-page-shell",
      "liquid-page-shell--billing"
    );
    expect(screen.getByRole("region", { name: "상단 안내 surface" })).toHaveClass("liquid-frost-panel");
  });

  it("catalog 요청이 실패하면 live fallback을 숨기고 점검 안내만 보여준다", async () => {
    getBillingCatalogApiMock.mockRejectedValueOnce(new Error("catalog blocked"));

    render(
      <MemoryRouter>
        <PricingPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("결제 설정 점검 중")).toBeInTheDocument();
    expect(screen.queryByText("₩9,900")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "구매" })).not.toBeInTheDocument();
  });

  it("catalog가 빈 배열이어도 live fallback을 노출하지 않는다", async () => {
    getBillingCatalogApiMock.mockResolvedValueOnce([]);

    render(
      <MemoryRouter>
        <PricingPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("결제 설정 점검 중")).toBeInTheDocument();
    expect(screen.queryByText("₩9,900")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "구매" })).not.toBeInTheDocument();
  });
});
