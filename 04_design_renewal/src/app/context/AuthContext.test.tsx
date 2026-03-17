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

vi.mock("../api/billingApi", () => ({
  getBillingProfileApi: getBillingProfileApiMock,
  saveOpenAiKeyApi: saveOpenAiKeyApiMock,
  deleteOpenAiKeyApi: deleteOpenAiKeyApiMock,
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
  const { loginWithGoogle, connectOpenAi, disconnectOpenAi, user } = useAuth();

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
    delete (globalThis as { __MATH_OCR_PUBLIC_APP_URL__?: string }).__MATH_OCR_PUBLIC_APP_URL__;
    window.localStorage.clear();
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
