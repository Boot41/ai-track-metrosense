import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { getMe, postLogin, postLogout, postSignup, type AuthPayload, type UserResponse } from "@/lib/api";

type AuthContextValue = {
  user: UserResponse | null;
  loading: boolean;
  login: (payload: AuthPayload) => Promise<void>;
  signup: (payload: AuthPayload) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const current = await getMe();
      setUser(current);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const login = async (payload: AuthPayload) => {
    const current = await postLogin(payload);
    setUser(current);
  };

  const signup = async (payload: AuthPayload) => {
    const current = await postSignup(payload);
    setUser(current);
  };

  const logout = async () => {
    await postLogout();
    setUser(null);
  };

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, signup, logout, refresh }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
