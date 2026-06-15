"use client";

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { AuthStatus, AuthUser, LoginCredentials } from "./types";
import { authLogin, authLogout, authRefresh, configureApi } from "./api";

const LS_ACCESS_TOKEN = "tessera_access_token";
const LS_REFRESH_TOKEN = "tessera_refresh_token";
const LS_EXPIRES_AT = "tessera_expires_at";
const REFRESH_BUFFER_MS = 60_000;

export interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  accessToken: string | null;
  login(credentials: LoginCredentials): Promise<void>;
  logout(): Promise<void>;
  refreshIfNeeded(): Promise<string>;
}

function decodeJwtUser(token: string): AuthUser | null {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(b64));
    return { id: payload.sub, email: payload.email, isAdmin: payload.is_admin ?? false };
  } catch {
    return null;
  }
}

function readStorage(): { accessToken: string | null; refreshToken: string | null; expiresAt: number | null } {
  try {
    return {
      accessToken: localStorage.getItem(LS_ACCESS_TOKEN),
      refreshToken: localStorage.getItem(LS_REFRESH_TOKEN),
      expiresAt: Number(localStorage.getItem(LS_EXPIRES_AT)) || null,
    };
  } catch {
    return { accessToken: null, refreshToken: null, expiresAt: null };
  }
}

function writeStorage(accessToken: string, refreshToken: string, expiresIn: number): number {
  const expiresAt = Date.now() + expiresIn * 1000;
  try {
    localStorage.setItem(LS_ACCESS_TOKEN, accessToken);
    localStorage.setItem(LS_REFRESH_TOKEN, refreshToken);
    localStorage.setItem(LS_EXPIRES_AT, String(expiresAt));
  } catch {
    // localStorage may be blocked (private mode, storage quota)
  }
  return expiresAt;
}

function clearStorage(): void {
  try {
    localStorage.removeItem(LS_ACCESS_TOKEN);
    localStorage.removeItem(LS_REFRESH_TOKEN);
    localStorage.removeItem(LS_EXPIRES_AT);
  } catch {
    // ignore
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const accessTokenRef = useRef<string | null>(null);
  const refreshTokenRef = useRef<string | null>(null);
  const expiresAtRef = useRef<number | null>(null);
  const refreshLockRef = useRef<Promise<string> | null>(null);

  const updateState = useCallback((tok: string, rt: string, exp: number) => {
    accessTokenRef.current = tok;
    refreshTokenRef.current = rt;
    expiresAtRef.current = exp;
    setAccessToken(tok);
    setUser(decodeJwtUser(tok));
    setStatus("authenticated");
  }, []);

  const clearState = useCallback(() => {
    accessTokenRef.current = null;
    refreshTokenRef.current = null;
    expiresAtRef.current = null;
    setAccessToken(null);
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  useEffect(() => {
    const { accessToken: tok, refreshToken: rt, expiresAt: exp } = readStorage();
    if (tok && rt && exp) {
      updateState(tok, rt, exp);
    } else {
      setStatus("unauthenticated");
    }
  }, [updateState]);

  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === LS_ACCESS_TOKEN && e.newValue === null) {
        clearState();
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [clearState]);

  const performRefresh = useCallback(async (): Promise<string> => {
    const rt = refreshTokenRef.current;
    if (!rt) throw new Error("No refresh token");
    try {
      const data = await authRefresh(rt);
      const exp = writeStorage(data.access_token, data.refresh_token, data.expires_in);
      updateState(data.access_token, data.refresh_token, exp);
      return data.access_token;
    } catch (err) {
      clearStorage();
      clearState();
      throw err;
    }
  }, [updateState, clearState]);

  const refreshIfNeeded = useCallback(async (): Promise<string> => {
    const tok = accessTokenRef.current;
    const exp = expiresAtRef.current;

    if (tok && exp && exp - Date.now() > REFRESH_BUFFER_MS) {
      return tok;
    }

    if (!refreshLockRef.current) {
      refreshLockRef.current = performRefresh().finally(() => {
        refreshLockRef.current = null;
      });
    }
    return refreshLockRef.current;
  }, [performRefresh]);

  const login = useCallback(async ({ email, password }: LoginCredentials) => {
    const data = await authLogin(email, password);
    const exp = writeStorage(data.access_token, data.refresh_token, data.expires_in);
    updateState(data.access_token, data.refresh_token, exp);
  }, [updateState]);

  const logout = useCallback(async () => {
    const tok = accessTokenRef.current;
    const rt = refreshTokenRef.current;
    try {
      if (tok && rt) await authLogout(tok, rt);
    } catch {
      // best-effort server revocation
    } finally {
      clearStorage();
      clearState();
    }
  }, [clearState]);

  // Stable callback refs for api.ts (avoids stale closures)
  const performRefreshRef = useRef(performRefresh);
  const refreshIfNeededRef = useRef(refreshIfNeeded);
  const logoutRef = useRef(logout);
  useEffect(() => { performRefreshRef.current = performRefresh; }, [performRefresh]);
  useEffect(() => { refreshIfNeededRef.current = refreshIfNeeded; }, [refreshIfNeeded]);
  useEffect(() => { logoutRef.current = logout; }, [logout]);

  useEffect(() => {
    configureApi({
      getAccessToken: () => accessTokenRef.current,
      refreshIfNeeded: () => refreshIfNeededRef.current(),
      forceRefresh: () => performRefreshRef.current(),
      onUnauthorized: () => logoutRef.current(),
    });
  }, []);

  const value: AuthContextValue = { status, user, accessToken, login, logout, refreshIfNeeded };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
