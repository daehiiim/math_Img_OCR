import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

vi.mock("../api/billingApi", () => ({
  getBillingCatalogApi: vi.fn(async () => []),
}));

import { PricingPage } from "./PricingPage";

describe("PricingPage", () => {
  it("USD 기준과 세금 안내를 노출한다", () => {
    render(
      <MemoryRouter>
        <PricingPage />
      </MemoryRouter>
    );

    expect(screen.getByText("모든 가격은 USD 기준입니다.")).toBeInTheDocument();
    expect(screen.getByText("세금은 checkout에서 국가별로 계산될 수 있습니다.")).toBeInTheDocument();
  });
});
