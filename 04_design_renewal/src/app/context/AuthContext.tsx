import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { User as SupabaseUser } from "@supabase/supabase-js";

import {
  clearPendingPath,
  createDefaultProfile,
  readPendingPath,
  readStoredProfile,
  savePendingPath,
  saveStoredProfile,
  type StoredProfile,
} from "../lib/authStorage";
import {
  deleteOpenAiKeyApi,
  getBillingProfileApi,
  saveOpenAiKeyApi,
  type BillingProfileResponse,
} from "../api/billingApi";
import { buildPublicAppUrl } from "../lib/publicAppUrl";
import { browserSupabase, hasSupabaseAuth } from "../lib/supabase";

export type User = StoredProfile;

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isSupabaseEnabled: boolean;
  prepareLogin: (nextPath?: string) => void;
  loginWithGoogle: () => Promise<User | null>;
  connectOpenAi: (apiKey: string) => Promise<void>;
  disconnectOpenAi: () => Promise<void>;
  purchaseCredits: (amount: number) => void;
  consumeCredit: (jobId?: string) => boolean;
  refreshProfile: () => Promise<void>;
  readPostLoginPath: () => string;
  clearPostLoginPath: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

function mapSupabaseUser(user: SupabaseUser) {
  const email = user.email ?? "unknown@example.com";
  const displayName =
    user.user_metadata.full_name ??
    user.user_metadata.name ??
    email.split("@")[0] ??
    "Math OCR 사용자";

  return readStoredProfile(email) ?? createDefaultProfile(displayName, email);
}

function mergeRemoteProfile(localProfile: User, remoteProfile: Awaited<ReturnType<typeof getBillingProfileApi>>): User {
  return {
    ...localProfile,
    credits: remoteProfile.credits_balance,
    usedCredits: remoteProfile.used_credits,
    openAiConnected: remoteProfile.openai_connected,
    openAiMaskedKey: remoteProfile.openai_key_masked ?? null,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const syncRemoteProfile = useCallback(async (fallbackProfile?: User | null) => {
    if (!browserSupabase) {
      return;
    }

    try {
      const remoteProfile = await getBillingProfileApi();
      setUser((prev) => {
        const baseProfile = prev ?? fallbackProfile ?? null;
        if (!baseProfile) {
          return baseProfile;
        }

        const nextProfile = mergeRemoteProfile(baseProfile, remoteProfile);
        saveStoredProfile(nextProfile);
        return nextProfile;
      });
    } catch {
      // 프로필 동기화 실패 시 기존 로컬 상태를 유지한다.
    }
  }, []);

  useEffect(() => {
    if (!browserSupabase) {
      setIsLoading(false);
      return;
    }

    let active = true;

    // 현재 브라우저 세션이 있으면 로컬 프로필과 합쳐 복원한다.
    void browserSupabase.auth.getUser().then(({ data }) => {
      if (!active) {
        return;
      }

      setUser(data.user ? mapSupabaseUser(data.user) : null);
      setIsLoading(false);

      if (data.user) {
        const profile = mapSupabaseUser(data.user);
        void syncRemoteProfile(profile);
      }
    });

    const {
      data: { subscription },
    } = browserSupabase.auth.onAuthStateChange((_event, session) => {
      if (!active) {
        return;
      }

      if (!session?.user) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      const profile = mapSupabaseUser(session.user);
      saveStoredProfile(profile);
      setUser(profile);
      setIsLoading(false);
      void syncRemoteProfile(profile);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [syncRemoteProfile]);

  const updateUser = useCallback((updater: (prev: User) => User) => {
    setUser((prev) => {
      if (!prev) {
        return prev;
      }

      const next = updater(prev);
      saveStoredProfile(next);
      return next;
    });
  }, []);

  const applyRemoteProfile = useCallback(
    (remoteProfile: BillingProfileResponse) => {
      setUser((prev) => {
        if (!prev) {
          return prev;
        }

        const nextProfile = mergeRemoteProfile(prev, remoteProfile);
        saveStoredProfile(nextProfile);
        return nextProfile;
      });
    },
    []
  );

  const prepareLogin = useCallback((nextPath = "/workspace") => {
    savePendingPath(nextPath);
  }, []);

  const loginWithGoogle = useCallback(async () => {
    if (browserSupabase) {
      await browserSupabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: buildPublicAppUrl("/login"),
        },
      });
      return null;
    }

    const profile = createDefaultProfile("김수학", "mathkim@example.com");
    saveStoredProfile(profile);
    setUser(profile);
    return profile;
  }, []);

  const connectOpenAi = useCallback(
    async (apiKey: string) => {
      const remoteProfile = await saveOpenAiKeyApi(apiKey.trim());
      applyRemoteProfile(remoteProfile);
    },
    [applyRemoteProfile]
  );

  const disconnectOpenAi = useCallback(async () => {
    const remoteProfile = await deleteOpenAiKeyApi();
    applyRemoteProfile(remoteProfile);
  }, [applyRemoteProfile]);

  const purchaseCredits = useCallback(
    (amount: number) => {
      updateUser((prev) => ({
        ...prev,
        credits: prev.credits + amount,
      }));
    },
    [updateUser]
  );

  const consumeCredit = useCallback((jobId?: string): boolean => {
    let consumed = false;

    updateUser((prev) => {
      if (jobId && prev.chargedJobIds.includes(jobId)) {
        consumed = true;
        return prev;
      }

      const chargedJobIds = jobId ? [...prev.chargedJobIds, jobId] : prev.chargedJobIds;

      if (prev.openAiConnected) {
        consumed = true;
        return {
          ...prev,
          chargedJobIds,
        };
      }

      if (prev.credits <= 0) {
        return prev;
      }

      consumed = true;
      return {
        ...prev,
        credits: prev.credits - 1,
        usedCredits: prev.usedCredits + 1,
        chargedJobIds,
      };
    });

    return consumed;
  }, [updateUser]);

  const refreshProfile = useCallback(async () => {
    await syncRemoteProfile();
  }, [syncRemoteProfile]);

  const logout = useCallback(async () => {
    if (browserSupabase) {
      await browserSupabase.auth.signOut();
    }

    setUser((prev) => {
      if (!prev) return prev;
      saveStoredProfile({
        ...prev,
        openAiConnected: false,
        openAiMaskedKey: null,
      });
      return null;
    });
  }, []);

  const readPostLoginPath = useCallback(() => readPendingPath(), []);
  const clearPostLoginPath = useCallback(() => clearPendingPath(), []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      isSupabaseEnabled: hasSupabaseAuth,
      prepareLogin,
      loginWithGoogle,
      connectOpenAi,
      disconnectOpenAi,
      purchaseCredits,
      consumeCredit,
      refreshProfile,
      readPostLoginPath,
      clearPostLoginPath,
      logout,
    }),
    [
      user,
      isLoading,
      prepareLogin,
      loginWithGoogle,
      connectOpenAi,
      disconnectOpenAi,
      purchaseCredits,
      consumeCredit,
      refreshProfile,
      readPostLoginPath,
      clearPostLoginPath,
      logout,
    ]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
