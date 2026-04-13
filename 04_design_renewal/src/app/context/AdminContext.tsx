import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

import { createAdminSessionApi } from "../api/adminApi";
import {
  clearAdminSession,
  readAdminSession,
  saveAdminSession,
  type StoredAdminSession,
} from "../lib/adminSessionStorage";

interface AdminContextType {
  adminSession: StoredAdminSession | null;
  isAdminAuthenticated: boolean;
  enterAdminMode: (password: string) => Promise<StoredAdminSession>;
  exitAdminMode: () => void;
}

const AdminContext = createContext<AdminContextType | null>(null);

/** 앱 전체에서 공유하는 관리자 세션 상태를 관리한다. */
export function AdminProvider({ children }: { children: React.ReactNode }) {
  const [adminSession, setAdminSession] = useState<StoredAdminSession | null>(() => readAdminSession());

  /** 관리자 비밀번호를 검증하고 세션을 저장한 뒤 컨텍스트 상태를 갱신한다. */
  const enterAdminMode = useCallback(async (password: string) => {
    const response = await createAdminSessionApi(password.trim());
    const nextSession = {
      sessionToken: response.session_token,
      expiresAt: response.expires_at,
    };
    saveAdminSession(nextSession);
    setAdminSession(nextSession);
    return nextSession;
  }, []);

  /** 관리자 세션을 메모리와 sessionStorage에서 함께 제거한다. */
  const exitAdminMode = useCallback(() => {
    clearAdminSession();
    setAdminSession(null);
  }, []);

  const value = useMemo(
    () => ({
      adminSession,
      isAdminAuthenticated: !!adminSession,
      enterAdminMode,
      exitAdminMode,
    }),
    [adminSession, enterAdminMode, exitAdminMode]
  );

  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
}

/** 관리자 세션 컨텍스트를 안전하게 읽는다. */
export function useAdmin() {
  const ctx = useContext(AdminContext);
  if (!ctx) {
    throw new Error("useAdmin must be used within AdminProvider");
  }
  return ctx;
}
