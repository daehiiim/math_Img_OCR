import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  createCheckoutSessionApiMock,
  createCustomerPortalApiMock,
  getBillingCatalogApiMock,
  getCheckoutSessionStatusApiMock,
  purchaseCreditsMock,
  refreshProfileMock,
} = vi.hoisted(() => ({
  createCheckoutSessionApiMock: vi.fn(),
  createCustomerPortalApiMock: vi.fn(),
  getBillingCatalogApiMock: vi.fn(),
  getCheckoutSessionStatusApiMock: vi.fn(),
  purchaseCreditsMock: vi.fn(),
  refreshProfileMock: vi.fn(async () => undefined),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    purchaseCredits: purchaseCreditsMock,
    refreshProfile: refreshProfileMock,
    isAuthenticated: true,
    isLoading: false,
    prepareLogin: vi.fn(),
  }),
}));

vi.mock("../api/billingApi", () => ({
  createCheckoutSessionApi: createCheckoutSessionApiMock,
  createCustomerPortalApi: createCustomerPortalApiMock,
  getBillingCatalogApi: getBillingCatalogApiMock,
  getCheckoutSessionStatusApi: getCheckoutSessionStatusApiMock,
}));

import { PaymentPage } from "./PaymentPage";

describe("PaymentPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    refreshProfileMock.mockClear();
    purchaseCreditsMock.mockClear();
    createCheckoutSessionApiMock.mockReset();
    createCustomerPortalApiMock.mockReset();
    getBillingCatalogApiMock.mockResolvedValue([
      { plan_id: "single", title: "Single", amount: 1000, currency: "krw", credits: 1 },
      { plan_id: "starter", title: "Starter", amount: 19000, currency: "krw", credits: 100 },
      { plan_id: "pro", title: "Pro", amount: 29000, currency: "krw", credits: 200 },
    ]);
    getCheckoutSessionStatusApiMock.mockReset();
    delete (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__;
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

  it("catalog 요청이 실패해도 KRW fallback 가격을 유지한다", async () => {
    getBillingCatalogApiMock.mockRejectedValueOnce(new Error("catalog blocked"));

    render(
      <MemoryRouter initialEntries={["/payment/starter"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("₩19,000")).toBeInTheDocument();
    expect(screen.getByText("KRW")).toBeInTheDocument();
  });

  it("checkout 리다이렉트 URL을 공개 앱 URL 기준으로 생성한다", async () => {
    const user = userEvent.setup();
    (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__ =
      "https://mathtohwp.vercel.app/";
    createCheckoutSessionApiMock.mockRejectedValueOnce(new Error("checkout blocked"));

    render(
      <MemoryRouter initialEntries={["/payment/starter"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText("₩19,000");
    await user.click(screen.getByRole("button", { name: /지금 결제/i }));

    await waitFor(() =>
      expect(createCheckoutSessionApiMock).toHaveBeenCalledWith({
        planId: "starter",
        successUrl: "https://mathtohwp.vercel.app/payment/starter?checkout=success&checkout_id={CHECKOUT_ID}",
        cancelUrl: "https://mathtohwp.vercel.app/payment/starter?checkout=cancel",
      })
    );
  });

  it("customer portal return URL을 공개 앱 URL 기준으로 생성한다", async () => {
    const user = userEvent.setup();
    (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__ =
      "https://mathtohwp.vercel.app/";
    getCheckoutSessionStatusApiMock.mockResolvedValue({
      checkout_id: "chk_test_123",
      status: "succeeded",
      credits_applied: true,
    });
    createCustomerPortalApiMock.mockRejectedValueOnce(new Error("portal blocked"));

    render(
      <MemoryRouter initialEntries={["/payment/starter?checkout=success&checkout_id=chk_test_123"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("결제가 완료되었습니다")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /주문\/영수증 관리/i }));

    await waitFor(() =>
      expect(createCustomerPortalApiMock).toHaveBeenCalledWith(
        "https://mathtohwp.vercel.app/payment/starter"
      )
    );
  });

  it("mock 모드 성공 결제는 크레딧을 한 번만 반영한다", async () => {
    vi.stubEnv("VITE_LOCAL_UI_MOCK", "true");
    getCheckoutSessionStatusApiMock.mockResolvedValue({
      checkout_id: "chk_mock_success",
      status: "succeeded",
      credits_applied: true,
    });

    const view = render(
      <MemoryRouter initialEntries={["/payment/starter?checkout=success&checkout_id=chk_mock_success"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("결제가 완료되었습니다")).toBeInTheDocument();
    await waitFor(() => {
      expect(purchaseCreditsMock).toHaveBeenCalledWith(100);
    });
    expect(refreshProfileMock).not.toHaveBeenCalled();

    view.unmount();

    render(
      <MemoryRouter initialEntries={["/payment/starter?checkout=success&checkout_id=chk_mock_success"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText("결제가 완료되었습니다");
    expect(purchaseCreditsMock).toHaveBeenCalledTimes(1);
  });

  it("mock 모드 취소 결제는 오류만 보여주고 크레딧은 바꾸지 않는다", async () => {
    vi.stubEnv("VITE_LOCAL_UI_MOCK", "true");

    render(
      <MemoryRouter initialEntries={["/payment/starter?checkout=cancel&checkout_id=chk_mock_cancel"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("결제가 취소되었습니다. 다시 시도해주세요.")).toBeInTheDocument();
    expect(purchaseCreditsMock).not.toHaveBeenCalled();
  });

  it("mock 모드 실패 결제는 오류만 보여주고 크레딧은 바꾸지 않는다", async () => {
    vi.stubEnv("VITE_LOCAL_UI_MOCK", "true");
    getCheckoutSessionStatusApiMock.mockResolvedValue({
      checkout_id: "chk_mock_fail",
      status: "failed",
      credits_applied: false,
    });

    render(
      <MemoryRouter initialEntries={["/payment/starter?checkout=success&checkout_id=chk_mock_fail"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("결제가 완료되지 않았습니다. 다시 시도해주세요.")).toBeInTheDocument();
    expect(purchaseCreditsMock).not.toHaveBeenCalled();
  });

  it("mock 모드에서는 portal 버튼을 비활성화하고 안내 문구를 노출한다", async () => {
    vi.stubEnv("VITE_LOCAL_UI_MOCK", "true");
    getCheckoutSessionStatusApiMock.mockResolvedValue({
      checkout_id: "chk_mock_portal",
      status: "succeeded",
      credits_applied: true,
    });

    render(
      <MemoryRouter initialEntries={["/payment/starter?checkout=success&checkout_id=chk_mock_portal"]}>
        <Routes>
          <Route path="/payment/:planId" element={<PaymentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("mock 모드에서는 주문/영수증 포털을 제공하지 않습니다.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /주문\/영수증 관리/i })).toBeDisabled();
  });
});
