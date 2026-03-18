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
      { plan_id: "single", title: "Single", amount: 1000, currency: "krw", credits: 1 },
      { plan_id: "starter", title: "Starter", amount: 19000, currency: "krw", credits: 100 },
      { plan_id: "pro", title: "Pro", amount: 29000, currency: "krw", credits: 200 },
    ]);
  });

  it("catalog 기준 통화와 checkout 안내를 노출한다", async () => {
    render(
      <MemoryRouter>
        <PricingPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("₩19,000")).toBeInTheDocument();
    expect(screen.getAllByText("KRW").length).toBeGreaterThan(0);
    expect(screen.getByText("실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.")).toBeInTheDocument();
  });

  it("catalog 요청이 실패해도 KRW fallback 가격을 유지한다", async () => {
    getBillingCatalogApiMock.mockRejectedValueOnce(new Error("catalog blocked"));

    render(
      <MemoryRouter>
        <PricingPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("₩19,000")).toBeInTheDocument();
    expect(screen.getAllByText("KRW").length).toBeGreaterThan(0);
  });
});
