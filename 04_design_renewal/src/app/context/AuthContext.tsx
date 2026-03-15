import React, { createContext, useContext, useState, useCallback } from "react";

export interface User {
  name: string;
  email: string;
  avatarInitials: string;
  credits: number;
  chatGptConnected: boolean;
  usedCredits: number; // Track total credits used
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loginWithGoogle: () => void;
  connectChatGpt: () => void;
  disconnectChatGpt: () => void;
  purchaseCredits: (amount: number) => void;
  consumeCredit: () => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const loginWithGoogle = useCallback(() => {
    setUser({
      name: "김수학",
      email: "mathkim@example.com",
      avatarInitials: "김",
      credits: 0, // Start with 0 credits
      chatGptConnected: false,
      usedCredits: 0, // Initialize used credits
    });
  }, []);

  const connectChatGpt = useCallback(() => {
    setUser((prev) => (prev ? { ...prev, chatGptConnected: true } : prev));
  }, []);

  const disconnectChatGpt = useCallback(() => {
    setUser((prev) => (prev ? { ...prev, chatGptConnected: false } : prev));
  }, []);

  const purchaseCredits = useCallback((amount: number) => {
    setUser((prev) => (prev ? { ...prev, credits: prev.credits + amount } : prev));
  }, []);

  const consumeCredit = useCallback((): boolean => {
    let consumed = false;
    setUser((prev) => {
      if (!prev) return prev;
      if (prev.chatGptConnected || prev.credits > 0) {
        consumed = true;
        if (!prev.chatGptConnected) {
          return { ...prev, credits: prev.credits - 1, usedCredits: prev.usedCredits + 1 };
        } else {
          // ChatGPT connected - no credit deduction, but still track usage
          return { ...prev, usedCredits: prev.usedCredits + 1 };
        }
      }
      return prev;
    });
    return consumed;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
  }, []);

  const value = React.useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      loginWithGoogle,
      connectChatGpt,
      disconnectChatGpt,
      purchaseCredits,
      consumeCredit,
      logout,
    }),
    [user, loginWithGoogle, connectChatGpt, disconnectChatGpt, purchaseCredits, consumeCredit, logout]
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