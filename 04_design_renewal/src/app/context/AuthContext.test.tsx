import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getBillingProfileApiMock } = vi.hoisted(() => ({
  getBillingProfileApiMock: vi.fn(),
}));

const { signInWithOAuthMock, signOutMock, getUserMock, onAuthStateChangeMock } = vi.hoisted(() => ({
  signInWithOAuthMock: vi.fn(async () => ({ data: {}, error: null })),
  signOutMock: vi.fn(async () => undefined),
  getUserMock: vi.fn(async () => ({ data: { user: null } })),
  onAuthStateChangeMock: vi.fn(() => ({
    data: {
      subscription: {
        unsubscribe: vi.fn(),
      },
    },
  })),
}));

vi.mock("../api/billingApi", () => ({
  getBillingProfileApi: getBillingProfileApiMock,
}));

vi.mock("../lib/supabase", () => ({
  hasSupabaseAuth: true,
  browserSupabase: {
    auth: {
      getUser: getUserMock,
      onAuthStateChange: onAuthStateChangeMock,
      signInWithOAuth: signInWithOAuthMock,
      signOut: signOutMock,
    },
  },
}));

import { AuthProvider, useAuth } from "./AuthContext";

function AuthHarness() {
  const { loginWithGoogle } = useAuth();

  return (
    <button onClick={() => void loginWithGoogle()} type="button">
      로그인
    </button>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    getBillingProfileApiMock.mockReset();
    signInWithOAuthMock.mockClear();
    signOutMock.mockClear();
    getUserMock.mockClear();
    onAuthStateChangeMock.mockClear();
    delete (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__;
  });

  it("Google OAuth redirectTo를 공개 앱 URL 기준으로 보낸다", async () => {
    const user = userEvent.setup();
    (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__ =
      "https://mathtohwp.vercel.app/";

    render(
      <AuthProvider>
        <AuthHarness />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: "로그인" }));

    await waitFor(() =>
      expect(signInWithOAuthMock).toHaveBeenCalledWith({
        provider: "google",
        options: {
          redirectTo: "https://mathtohwp.vercel.app/login",
        },
      })
    );
  });
});
