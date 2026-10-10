import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { authService, readApiError } from "../services/auth";
import type { AuthUser, DonorType, UserRole } from "../types/models";

type AuthCtx = {
  user: AuthUser | null;
  loading: boolean;
  error: string;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    role: UserRole;
    donor_type?: DonorType;
    organization_name?: string;
  }) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    authService
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      loading,
      error,
      async login(email, password) {
        setError("");
        try {
          await authService.login(email, password);
          const me = await authService.me();
          setUser(me);
          return me;
        } catch (err) {
          const message = readApiError(err);
          setError(message);
          throw err;
        }
      },
      async register(payload) {
        setError("");
        try {
          return await authService.register(payload);
        } catch (err) {
          const message = readApiError(err);
          setError(message);
          throw err;
        }
      },
      async logout() {
        await authService.logout();
        setUser(null);
      },
      async refresh() {
        const me = await authService.me();
        setUser(me);
      },
    }),
    [user, loading, error],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
