/**
 * Auth transport is isolated here.
 * Prompt 1 keeps the working short-lived access token and also sets an HttpOnly cookie.
 * Production hardening remaining: rotate refresh tokens, CSRF pairing, and drop in-memory token fallback.
 */
import api, { bindTokenReader, readApiError } from "./api";
import type { AuthUser, DonorType, UserRole } from "../types/models";

export function resolveLoginEmail(raw: string) {
  const value = raw.trim().toLowerCase();
  if (!value) return value;
  if (value.includes("@")) return value;
  if (/^[a-z0-9._-]{2,32}$/.test(value)) return `${value}@anuvarthan.test`;
  return value;
}

class AuthService {
  private accessToken: string | null = null;

  constructor() {
    bindTokenReader(() => this.accessToken);
  }

  getToken() {
    return this.accessToken;
  }

  clear() {
    this.accessToken = null;
  }

  async register(payload: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    role: UserRole;
    donor_type?: DonorType;
    organization_name?: string;
  }): Promise<AuthUser> {
    const { data } = await api.post<AuthUser>("/auth/register", payload);
    return data;
  }

  async login(email: string, password: string): Promise<string> {
    const { data } = await api.post<{ access_token: string }>("/auth/login", {
      email: resolveLoginEmail(email),
      password,
    });
    this.accessToken = data.access_token;
    return data.access_token;
  }

  async me(): Promise<AuthUser> {
    const { data } = await api.get<AuthUser>("/auth/me");
    if (!data || typeof data !== "object" || !data.id || !data.role) {
      throw new Error("Sign in to continue.");
    }
    return data;
  }

  async logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      this.clear();
    }
  }

  async updateProfile(payload: { full_name?: string; phone?: string }): Promise<AuthUser> {
    const { data } = await api.patch<AuthUser>("/users/me", payload);
    return data;
  }
}

export const authService = new AuthService();
export { readApiError };
