import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";

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
  getBillingCatalogApi: vi.fn(async () => []),
  getCheckoutSessionStatusApi: vi.fn(),
}));

import { PaymentPage } from "./PaymentPage";

describe("PaymentPage", () => {
  it("Polar checkout 안내 문구를 노출한다", () => {
    render(
      <MemoryRouter initialEntries={["/payment/starter"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Polar checkout으로 안전하게 결제됩니다.")).toBeInTheDocument();
  });
});
