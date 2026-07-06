import type { LoginResponse, RefreshResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Error thrown for a non-2xx API response. Extends `Error` (so existing
 * `err instanceof Error` / `err.message` callers keep working) while also
 * carrying the server's machine-readable `code` and HTTP `status` for callers
 * that need to distinguish outcomes (e.g. already_member vs already_invited).
 */
export class ApiError extends Error {
  code: string | null;
  status: number;

  constructor(message: string, code: string | null, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

interface ApiConfig {
  getAccessToken(): string | null;
  refreshIfNeeded(): Promise<string>;
  forceRefresh(): Promise<string>;
  onUnauthorized(): void;
}

let authConfig: ApiConfig | null = null;

export function configureApi(config: ApiConfig): void {
  authConfig = config;
}

async function request<T>(path: string, options?: RequestInit, isRetry = false): Promise<T> {
  let token: string | null = authConfig?.getAccessToken() ?? null;

  if (authConfig && !isRetry) {
    try {
      token = await authConfig.refreshIfNeeded();
    } catch {
      // Proceed with whatever token we have; let the server decide
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      headers,
    });
  } catch (err) {
    if (err instanceof TypeError) {
      throw new Error("Could not reach the server. Please check your connection and try again.");
    }
    throw err;
  }

  if (!res.ok) {
    if (res.status === 401 && authConfig) {
      if (!isRetry) {
        try {
          await authConfig.forceRefresh();
          return request<T>(path, options, true);
        } catch {
          authConfig.onUnauthorized();
          throw new Error("Session expired. Please log in again.");
        }
      }
      // Retry also got 401 — token is definitively invalid
      authConfig.onUnauthorized();
      throw new Error("Session expired. Please log in again.");
    }
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new ApiError(err?.error?.message ?? res.statusText, err?.error?.code ?? null, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "DELETE",
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    }),
};

// ─── Raw auth functions (bypass auth injection) ──────────────────────────────

async function rawPost<T>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body: JSON.stringify(body),
    headers: {
      "Content-Type": "application/json",
      ...extraHeaders,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err?.error?.message ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function authLogin(email: string, password: string): Promise<LoginResponse> {
  return rawPost<LoginResponse>("/v1/auth/login", { email, password });
}

export async function authRefresh(refreshToken: string): Promise<RefreshResponse> {
  return rawPost<RefreshResponse>("/v1/auth/refresh", { refresh_token: refreshToken });
}

export async function authLogout(accessToken: string, refreshToken: string): Promise<void> {
  return rawPost<void>("/v1/auth/logout", { refresh_token: refreshToken }, {
    Authorization: `Bearer ${accessToken}`,
  });
}

export async function authRegister(displayName: string, email: string, password: string): Promise<void> {
  await rawPost<unknown>("/v1/auth/register", { display_name: displayName, email, password });
}

export async function authChangePassword(params: {
  currentPassword: string;
  newPassword: string;
  confirmNewPassword: string;
  refreshToken: string;
  accessToken: string;
}): Promise<{ access_token: string; refresh_token: string; token_type: string; expires_in: number }> {
  return rawPost(
    "/v1/auth/change-password",
    {
      current_password: params.currentPassword,
      new_password: params.newPassword,
      confirm_new_password: params.confirmNewPassword,
      refresh_token: params.refreshToken,
    },
    { Authorization: `Bearer ${params.accessToken}` },
  );
}

export async function authForgotPassword(email: string): Promise<void> {
  await rawPost<unknown>("/v1/auth/forgot-password", { email });
}

export async function authResetPassword(params: {
  token: string;
  newPassword: string;
  confirmNewPassword: string;
}): Promise<void> {
  await rawPost<unknown>("/v1/auth/reset-password", {
    token: params.token,
    new_password: params.newPassword,
    confirm_new_password: params.confirmNewPassword,
  });
}
