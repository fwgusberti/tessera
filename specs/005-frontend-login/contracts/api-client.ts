/**
 * Contract: Updated api.ts interface
 *
 * This is a design contract — not runnable code. It documents how lib/api.ts
 * must change to support authenticated requests.
 */

// ─── Initialization ──────────────────────────────────────────────────────────

/**
 * api.ts must be updated to accept an auth context reference so it can:
 * 1. Inject "Authorization: Bearer <token>" on every request
 * 2. Call refreshIfNeeded() before each request
 * 3. Retry once on 401 after a successful refresh
 *
 * Preferred approach: `configureApi(authContext: AuthContextValue): void`
 * Called once from AuthProvider after the context is ready.
 *
 * The existing `api.get` / `api.post` surface remains unchanged — callers
 * do not need to pass tokens manually.
 */

export interface ApiConfig {
  /** Set by AuthProvider once context is available */
  getAccessToken: () => string | null;
  refreshIfNeeded: () => Promise<string>;
  onUnauthorized: () => void; // triggers logout flow
}

export declare function configureApi(config: ApiConfig): void;

// ─── Unchanged public surface ─────────────────────────────────────────────────

/**
 * These signatures are unchanged. Callers continue using api.get / api.post
 * exactly as before; auth injection is transparent.
 */
export declare const api: {
  get: <T>(path: string) => Promise<T>;
  post: <T>(path: string, body: unknown) => Promise<T>;
  delete: <T>(path: string) => Promise<T>;
};

// ─── Auth-specific API calls ──────────────────────────────────────────────────

/**
 * These are thin wrappers around api.post used only by AuthContext.
 * They bypass the auth injection (no Bearer header) because they are
 * called to obtain or renew tokens, not to use them.
 */

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number; // seconds
}

export interface RefreshResponse extends LoginResponse {}

export declare function authLogin(email: string, password: string): Promise<LoginResponse>;
export declare function authRefresh(refreshToken: string): Promise<RefreshResponse>;
export declare function authLogout(accessToken: string, refreshToken: string): Promise<void>;
