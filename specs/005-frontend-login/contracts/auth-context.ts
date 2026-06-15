/**
 * Contract: AuthContext public interface
 *
 * This is a design contract — not runnable code. It documents the exact TypeScript
 * interface that lib/auth.tsx must implement. Implementations must satisfy this shape.
 */

// ─── Types ──────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  isAdmin: boolean;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthState {
  status: AuthStatus;
  user: AuthUser | null;
  accessToken: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

// ─── Context value shape ─────────────────────────────────────────────────────

export interface AuthContextValue extends AuthState {
  /**
   * Authenticate with email + password.
   * On success: stores tokens, updates state to "authenticated".
   * On failure: throws with a user-readable message (e.g. "Invalid credentials").
   */
  login(credentials: LoginCredentials): Promise<void>;

  /**
   * Revoke the current session server-side and clear local tokens.
   * Always transitions state to "unauthenticated", even if the server call fails.
   */
  logout(): Promise<void>;

  /**
   * Check if the access token is expiring soon (within 60 s) and silently
   * request a new pair from /v1/auth/refresh.
   * Returns the current (or newly issued) access token string.
   * Throws if refresh fails (caller should treat as logout).
   * Concurrent callers receive the same in-flight promise (no double-refresh).
   */
  refreshIfNeeded(): Promise<string>;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

/**
 * useAuth() is the only public API for consuming AuthContext.
 * Throws if called outside <AuthProvider>.
 */
export declare function useAuth(): AuthContextValue;

// ─── Provider ────────────────────────────────────────────────────────────────

/**
 * <AuthProvider> must be a "use client" component.
 * It hydrates auth state from localStorage on mount and listens for the
 * 'storage' event to synchronise logout across tabs.
 */
export interface AuthProviderProps {
  children: React.ReactNode;
}
