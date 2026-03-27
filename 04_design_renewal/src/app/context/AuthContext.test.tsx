import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getBillingProfileApiMock } = vi.hoisted(() => ({
  getBillingProfileApiMock: vi.fn(),
}));

const { saveOpenAiKeyApiMock, deleteOpenAiKeyApiMock } = vi.hoisted(() => ({
  saveOpenAiKeyApiMock: vi.fn(),
  deleteOpenAiKeyApiMock: vi.fn(),
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

const { supabaseState } = vi.hoisted(() => ({
  supabaseState: {
    hasSupabaseAuth: true,
  },
}));

vi.mock("../api/billingApi", () => ({
  getBillingProfileApi: getBillingProfileApiMock,
  saveOpenAiKeyApi: saveOpenAiKeyApiMock,
  deleteOpenAiKeyApi: deleteOpenAiKeyApiMock,
}));

vi.mock("../lib/supabase", () => ({
  get hasSupabaseAuth() {
    return supabaseState.hasSupabaseAuth;
  },
  get browserSupabase() {
    if (!supabaseState.hasSupabaseAuth) {
      return null;
    }

    return {
      auth: {
        getUser: getUserMock,
        onAuthStateChange: onAuthStateChangeMock,
        signInWithOAuth: signInWithOAuthMock,
        signOut: signOutMock,
      },
    };
  },
}));

import { AuthProvider, useAuth } from "./AuthContext";

function AuthHarness() {
  const { authErrorMessage, connectOpenAi, disconnectOpenAi, loginWithGoogle, user } = useAuth();

  return (
    <div>
      <button onClick={() => void loginWithGoogle()} type="button">
        로그인
      </button>
      <button onClick={() => void connectOpenAi("sk-user-1234567890")} type="button">
        연결
      </button>
      <button onClick={() => void disconnectOpenAi()} type="button">
        해제
      </button>
      <span data-testid="openai-state">{user?.openAiConnected ? "connected" : "disconnected"}</span>
      <span data-testid="masked-key">{user?.openAiMaskedKey ?? "none"}</span>
      <span data-testid="credits">{user?.credits ?? 0}</span>
      <span data-testid="email">{user?.email ?? "none"}</span>
      <span data-testid="auth-error">{authErrorMessage ?? "none"}</span>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    getBillingProfileApiMock.mockReset();
    signInWithOAuthMock.mockClear();
    signOutMock.mockClear();
    getUserMock.mockClear();
    onAuthStateChangeMock.mockClear();
    saveOpenAiKeyApiMock.mockReset();
    deleteOpenAiKeyApiMock.mockReset();
    supabaseState.hasSupabaseAuth = true;
    delete (globalThis as { __MATH_OCR_SITE_URL__?: string }).__MATH_OCR_SITE_URL__;
    delete (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__;
    vi.unstubAllEnvs();
    window.localStorage.clear();
  });

  it("Google OAuth redirectTo를 공개 앱 URL 기준으로 보낸다", async () => {
    const user = userEvent.setup();
    (globalThis as { __MATH_OCR_SITE_URL__?: string }).__MATH_OCR_SITE_URL__ =
      "https://mathhwp.vercel.app/".replace("mathhwp", "mathtohwp");

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
          redirectTo: "https://mathhwp.vercel.app/login",
        },
      })
    );
  });

  it("mock 모드에서는 OAuth 없이 로컬 테스트 사용자를 만든다", async () => {
    const user = userEvent.setup();
    vi.stubEnv("VITE_LOCAL_UI_MOCK", "true");

    render(
      <AuthProvider>
        <AuthHarness />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(signInWithOAuthMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("email")).toHaveTextContent("local-ui-mock@example.com");
    expect(screen.getByTestId("auth-error")).toHaveTextContent("none");
  });

  it("mock 모드가 아니고 인증 설정이 없으면 안내 메시지만 노출한다", async () => {
    supabaseState.hasSupabaseAuth = false;

    render(
      <AuthProvider>
        <AuthHarness />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-error")).toHaveTextContent(
        "로컬 UI mock 모드를 켜거나 Supabase 인증 환경값을 설정해주세요."
      );
    });
    expect(screen.getByTestId("email")).toHaveTextContent("none");
  });

  it("remote billing profile values override stale local OpenAI state", async () => {
    window.localStorage.setItem(
      "math-ocr:profiles",
      JSON.stringify({
        "math@example.com": {
          name: "김수학",
          email: "math@example.com",
          avatarInitials: "김",
          credits: 99,
          openAiConnected: true,
          openAiMaskedKey: "stale-mask",
          usedCredits: 0,
          chargedJobIds: [],
        },
      })
    );
    getUserMock.mockResolvedValueOnce({
      data: {
        user: {
          email: "math@example.com",
          user_metadata: { full_name: "김수학" },
        },
      },
    });
    getBillingProfileApiMock.mockResolvedValueOnce({
      credits_balance: 4,
      used_credits: 2,
      openai_connected: false,
      openai_key_masked: null,
    });

    render(
      <AuthProvider>
        <AuthHarness />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("openai-state")).toHaveTextContent("disconnected");
    });
    expect(screen.getByTestId("masked-key")).toHaveTextContent("none");
    expect(screen.getByTestId("credits")).toHaveTextContent("4");
  });

  it("connectOpenAi saves the key remotely and refreshes local state from server response", async () => {
    const user = userEvent.setup();
    getUserMock.mockResolvedValueOnce({
      data: {
        user: {
          email: "math@example.com",
          user_metadata: { full_name: "김수학" },
        },
      },
    });
    getBillingProfileApiMock.mockResolvedValueOnce({
      credits_balance: 4,
      used_credits: 1,
      openai_connected: false,
      openai_key_masked: null,
    });
    saveOpenAiKeyApiMock.mockResolvedValueOnce({
      credits_balance: 4,
      used_credits: 1,
      openai_connected: true,
      openai_key_masked: "sk-us••••7890",
    });

    render(
      <AuthProvider>
        <AuthHarness />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("openai-state")).toHaveTextContent("disconnected");
    });

    await user.click(screen.getByRole("button", { name: "연결" }));

    await waitFor(() => {
      expect(saveOpenAiKeyApiMock).toHaveBeenCalledWith("sk-user-1234567890");
    });
    expect(screen.getByTestId("openai-state")).toHaveTextContent("connected");
    expect(screen.getByTestId("masked-key")).toHaveTextContent("sk-us••••7890");
  });

  it("disconnectOpenAi clears OpenAI state from the backend response", async () => {
    const user = userEvent.setup();
    getUserMock.mockResolvedValueOnce({
      data: {
        user: {
          email: "math@example.com",
          user_metadata: { full_name: "김수학" },
        },
      },
    });
    getBillingProfileApiMock.mockResolvedValueOnce({
      credits_balance: 4,
      used_credits: 1,
      openai_connected: true,
      openai_key_masked: "sk-us••••7890",
    });
    deleteOpenAiKeyApiMock.mockResolvedValueOnce({
      credits_balance: 4,
      used_credits: 1,
      openai_connected: false,
      openai_key_masked: null,
    });

    render(
      <AuthProvider>
        <AuthHarness />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("openai-state")).toHaveTextContent("connected");
    });

    await user.click(screen.getByRole("button", { name: "해제" }));

    await waitFor(() => {
      expect(deleteOpenAiKeyApiMock).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByTestId("openai-state")).toHaveTextContent("disconnected");
    expect(screen.getByTestId("masked-key")).toHaveTextContent("none");
  });
});
