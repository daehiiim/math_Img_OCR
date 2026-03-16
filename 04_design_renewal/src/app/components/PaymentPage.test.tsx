import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getBillingCatalogApiMock } = vi.hoisted(() => ({
  getBillingCatalogApiMock: vi.fn(),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    refreshProfile: vi.fn(async () => undefined),
    isAuthenticated: true,
    isLoading: false,
    prepareLogin: vi.fn(),
  }),
}));

vi.mock("../api/billingApi", () => ({
  createCheckoutSessionApi: vi.fn(),
  createCustomerPortalApi: vi.fn(),
  getBillingCatalogApi: getBillingCatalogApiMock,
  getCheckoutSessionStatusApi: vi.fn(),
}));

import { PaymentPage } from "./PaymentPage";

describe("PaymentPage", () => {
  beforeEach(() => {
    getBillingCatalogApiMock.mockResolvedValue([
      { plan_id: "single", title: "Single", amount: 1000, currency: "krw", credits: 1 },
      { plan_id: "starter", title: "Starter", amount: 19000, currency: "krw", credits: 100 },
      { plan_id: "pro", title: "Pro", amount: 29000, currency: "krw", credits: 200 },
    ]);
  });

  it("결제 통화와 안내 문구를 catalog 기준으로 노출한다", async () => {
    render(
      <MemoryRouter initialEntries={["/payment/starter"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("₩19,000")).toBeInTheDocument();
    expect(screen.getByText("Polar checkout으로 안전하게 결제됩니다.")).toBeInTheDocument();
    expect(screen.getByText("실제 결제 통화와 세금은 checkout에서 최종 확정됩니다.")).toBeInTheDocument();
  });
});
