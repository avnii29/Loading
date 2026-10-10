import axios, { AxiosError } from "axios";

function apiBaseUrl() {
  const configured = (import.meta.env.VITE_API_URL || "").trim().replace(/\/$/, "");
  if (!configured) return "/api";
  if (import.meta.env.PROD && /localhost|127\.0\.0\.1/i.test(configured)) {
    throw new Error("Production API URL must not point at localhost.");
  }
  return configured;
}

const api = axios.create({
  baseURL: apiBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
  withCredentials: true,
});

type TokenReader = () => string | null;

let readToken: TokenReader = () => null;

export function bindTokenReader(reader: TokenReader) {
  readToken = reader;
}

api.interceptors.request.use((config) => {
  const token = readToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function readApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ error?: { message?: string }; detail?: string }>;
    const payload = axiosError.response?.data;
    if (payload?.error?.message) return payload.error.message;
    if (typeof payload?.detail === "string") return payload.detail;
    if (axiosError.code === "ERR_NETWORK") return "We couldn't reach the network. Try again when you're online.";
    if (axiosError.response?.status === 401) return "Sign in to continue.";
  }
  return "Something went wrong. Please try again.";
}

export default api;
