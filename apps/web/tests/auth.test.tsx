import { renderHook, act, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  authLogin: vi.fn(),
  authRefresh: vi.fn(),
  authLogout: vi.fn(),
  authSelectTenant: vi.fn(),
  configureApi: vi.fn(),
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

import { AuthProvider, useAuth } from "@/lib/auth";
import { authLogin, authRefresh, authLogout, authSelectTenant } from "@/lib/api";

const mockAuthLogin = authLogin as ReturnType<typeof vi.fn>;
const mockAuthRefresh = authRefresh as ReturnType<typeof vi.fn>;
const mockAuthLogout = authLogout as ReturnType<typeof vi.fn>;
const mockAuthSelectTenant = authSelectTenant as ReturnType<typeof vi.fn>;

function makeJwt(payload: Record<string, unknown>): string {
  return [
    "header",
    btoa(JSON.stringify(payload)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_"),
    "signature",
  ].join(".");
}

const FAKE_JWT = makeJwt({ sub: "user-1", email: "test@example.com", is_admin: false, exp: 9999999999 });

const LOGIN_RESPONSE = {
  access_token: FAKE_JWT,
  refresh_token: "rt-abc",
  token_type: "bearer" as const,
  expires_in: 900,
};

function wrapper({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

// ─── Login ────────────────────────────────────────────────────────────────────

describe("AuthContext / login", () => {
  it("transitions to unauthenticated when no tokens in localStorage", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));
  });

  it("successful login stores tokens and transitions to authenticated", async () => {
    mockAuthLogin.mockResolvedValue(LOGIN_RESPONSE);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "pass123" });
    });

    expect(result.current.status).toBe("authenticated");
    expect(result.current.user).toEqual({
      id: "user-1",
      email: "test@example.com",
      isAdmin: false,
      tokenKind: "full",
      companyId: null,
    });
    expect(result.current.accessToken).toBe(FAKE_JWT);
    expect(localStorage.getItem("tessera_access_token")).toBe(FAKE_JWT);
    expect(localStorage.getItem("tessera_refresh_token")).toBe("rt-abc");
    expect(localStorage.getItem("tessera_expires_at")).toBeTruthy();
  });

  it("failed login throws and does not store tokens", async () => {
    mockAuthLogin.mockRejectedValue(new Error("Invalid credentials"));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await expect(
      act(async () => {
        await result.current.login({ email: "bad@example.com", password: "wrong" });
      })
    ).rejects.toThrow("Invalid credentials");

    expect(result.current.status).toBe("unauthenticated");
    expect(localStorage.getItem("tessera_access_token")).toBeNull();
  });

  it("login calls authLogin with provided credentials", async () => {
    mockAuthLogin.mockResolvedValue(LOGIN_RESPONSE);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "secret" });
    });

    expect(mockAuthLogin).toHaveBeenCalledWith("test@example.com", "secret");
  });
});

// ─── Token kind decoding ──────────────────────────────────────────────────────

describe("AuthContext / token kind decoding", () => {
  it("surfaces tokenKind and companyId from the JWT claims on a full token", async () => {
    const jwt = makeJwt({
      sub: "user-1",
      email: "test@example.com",
      is_admin: true,
      token_kind: "full",
      company_id: "co-1",
      exp: 9999999999,
    });
    mockAuthLogin.mockResolvedValue({ ...LOGIN_RESPONSE, access_token: jwt });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "pass" });
    });

    expect(result.current.user?.tokenKind).toBe("full");
    expect(result.current.user?.companyId).toBe("co-1");
  });

  it("surfaces tokenKind 'select' with null companyId on a select token", async () => {
    const jwt = makeJwt({
      sub: "user-1",
      email: "test@example.com",
      is_admin: false,
      token_kind: "select",
      exp: 9999999999,
    });
    mockAuthLogin.mockResolvedValue({ ...LOGIN_RESPONSE, access_token: jwt });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "pass" });
    });

    expect(result.current.user?.tokenKind).toBe("select");
    expect(result.current.user?.companyId).toBeNull();
  });

  it("defaults tokenKind to 'full' when the claim is absent (legacy tokens)", async () => {
    mockAuthLogin.mockResolvedValue(LOGIN_RESPONSE); // FAKE_JWT has no token_kind

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "pass" });
    });

    expect(result.current.user?.tokenKind).toBe("full");
    expect(result.current.user?.companyId).toBeNull();
  });
});

// ─── Tenant selection ─────────────────────────────────────────────────────────

describe("AuthContext / selectTenant", () => {
  const SELECT_JWT = makeJwt({
    sub: "user-1",
    email: "test@example.com",
    is_admin: false,
    token_kind: "select",
    exp: 9999999999,
  });
  const FULL_JWT = makeJwt({
    sub: "user-1",
    email: "test@example.com",
    is_admin: true,
    token_kind: "full",
    company_id: "co-1",
    exp: 9999999999,
  });

  function seedSelectSession() {
    localStorage.setItem("tessera_access_token", SELECT_JWT);
    localStorage.setItem("tessera_refresh_token", "rt-select");
    localStorage.setItem("tessera_expires_at", String(Date.now() + 900_000));
  }

  it("login resolves { tenantSelectionRequired: true } when the response carries the flag", async () => {
    mockAuthLogin.mockResolvedValue({
      ...LOGIN_RESPONSE,
      access_token: SELECT_JWT,
      tenant_selection_required: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    let outcome: { tenantSelectionRequired: boolean } | undefined;
    await act(async () => {
      outcome = await result.current.login({ email: "test@example.com", password: "pass" });
    });

    expect(outcome).toEqual({ tenantSelectionRequired: true });
  });

  it("login resolves { tenantSelectionRequired: false } when the flag is absent", async () => {
    mockAuthLogin.mockResolvedValue(LOGIN_RESPONSE);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    let outcome: { tenantSelectionRequired: boolean } | undefined;
    await act(async () => {
      outcome = await result.current.login({ email: "test@example.com", password: "pass" });
    });

    expect(outcome).toEqual({ tenantSelectionRequired: false });
  });

  it("selectTenant exchanges the current access token via authSelectTenant and persists the pair", async () => {
    seedSelectSession();
    mockAuthSelectTenant.mockResolvedValue({
      access_token: FULL_JWT,
      refresh_token: "rt-full",
      token_type: "bearer",
      expires_in: 900,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    await act(async () => {
      await result.current.selectTenant("co-1");
    });

    expect(mockAuthSelectTenant).toHaveBeenCalledWith(SELECT_JWT, "co-1");
    expect(localStorage.getItem("tessera_access_token")).toBe(FULL_JWT);
    expect(localStorage.getItem("tessera_refresh_token")).toBe("rt-full");
    expect(result.current.accessToken).toBe(FULL_JWT);
    expect(result.current.user?.tokenKind).toBe("full");
    expect(result.current.user?.companyId).toBe("co-1");
    expect(result.current.status).toBe("authenticated");
  });

  it("selectTenant leaves stored tokens and state untouched when the exchange fails", async () => {
    seedSelectSession();
    mockAuthSelectTenant.mockRejectedValue(new Error("Company is suspended"));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    await expect(
      act(async () => {
        await result.current.selectTenant("co-suspended");
      })
    ).rejects.toThrow("Company is suspended");

    expect(localStorage.getItem("tessera_access_token")).toBe(SELECT_JWT);
    expect(localStorage.getItem("tessera_refresh_token")).toBe("rt-select");
    expect(result.current.accessToken).toBe(SELECT_JWT);
    expect(result.current.user?.tokenKind).toBe("select");
    expect(result.current.status).toBe("authenticated");
  });
});

// ─── Session persistence ──────────────────────────────────────────────────────

describe("AuthContext / session persistence", () => {
  it("hydrates authenticated state from localStorage on mount", async () => {
    const expiresAt = Date.now() + 900_000;
    localStorage.setItem("tessera_access_token", FAKE_JWT);
    localStorage.setItem("tessera_refresh_token", "rt-stored");
    localStorage.setItem("tessera_expires_at", String(expiresAt));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    expect(result.current.user?.email).toBe("test@example.com");
    expect(result.current.accessToken).toBe(FAKE_JWT);
    expect(mockAuthRefresh).not.toHaveBeenCalled();
  });

  it("refreshIfNeeded returns current token when expiry is far in the future", async () => {
    const expiresAt = Date.now() + 900_000;
    localStorage.setItem("tessera_access_token", FAKE_JWT);
    localStorage.setItem("tessera_refresh_token", "rt-stored");
    localStorage.setItem("tessera_expires_at", String(expiresAt));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    const token = await act(async () => result.current.refreshIfNeeded());
    expect(token).toBe(FAKE_JWT);
    expect(mockAuthRefresh).not.toHaveBeenCalled();
  });

  it("refreshIfNeeded refreshes when token is expiring within 60s", async () => {
    const expiresAt = Date.now() + 30_000; // 30s — within the 60s buffer
    localStorage.setItem("tessera_access_token", FAKE_JWT);
    localStorage.setItem("tessera_refresh_token", "rt-stored");
    localStorage.setItem("tessera_expires_at", String(expiresAt));

    const NEW_JWT = FAKE_JWT + "-new";
    mockAuthRefresh.mockResolvedValue({
      ...LOGIN_RESPONSE,
      access_token: NEW_JWT,
      refresh_token: "rt-new",
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    const token = await act(async () => result.current.refreshIfNeeded());
    expect(mockAuthRefresh).toHaveBeenCalledWith("rt-stored");
    expect(token).toBe(NEW_JWT);
    expect(result.current.accessToken).toBe(NEW_JWT);
  });

  it("concurrent refreshIfNeeded calls share the same in-flight promise (no double-refresh)", async () => {
    const expiresAt = Date.now() + 30_000;
    localStorage.setItem("tessera_access_token", FAKE_JWT);
    localStorage.setItem("tessera_refresh_token", "rt-stored");
    localStorage.setItem("tessera_expires_at", String(expiresAt));

    let resolveRefresh!: (v: typeof LOGIN_RESPONSE) => void;
    mockAuthRefresh.mockReturnValue(new Promise((res) => { resolveRefresh = res; }));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    let t1: string | undefined, t2: string | undefined;
    act(() => {
      result.current.refreshIfNeeded().then((t) => { t1 = t; });
      result.current.refreshIfNeeded().then((t) => { t2 = t; });
    });

    await act(async () => {
      resolveRefresh({ ...LOGIN_RESPONSE, access_token: "new-tok", refresh_token: "new-rt" });
    });

    await waitFor(() => t1 !== undefined && t2 !== undefined);
    expect(mockAuthRefresh).toHaveBeenCalledTimes(1);
    expect(t1).toBe("new-tok");
    expect(t2).toBe("new-tok");
  });

  it("failed refresh clears localStorage and transitions to unauthenticated", async () => {
    const expiresAt = Date.now() + 30_000;
    localStorage.setItem("tessera_access_token", FAKE_JWT);
    localStorage.setItem("tessera_refresh_token", "rt-stored");
    localStorage.setItem("tessera_expires_at", String(expiresAt));

    mockAuthRefresh.mockRejectedValue(new Error("Invalid or expired refresh token"));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    await act(async () => {
      try {
        await result.current.refreshIfNeeded();
      } catch {
        // expected
      }
    });

    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));
    expect(localStorage.getItem("tessera_access_token")).toBeNull();
  });
});

// ─── Logout ───────────────────────────────────────────────────────────────────

describe("AuthContext / logout", () => {
  beforeEach(async () => {
    mockAuthLogin.mockResolvedValue(LOGIN_RESPONSE);
  });

  it("logout calls authLogout with access and refresh tokens", async () => {
    mockAuthLogout.mockResolvedValue(undefined);
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "pass" });
    });
    expect(result.current.status).toBe("authenticated");

    await act(async () => {
      await result.current.logout();
    });

    expect(mockAuthLogout).toHaveBeenCalledWith(FAKE_JWT, "rt-abc");
  });

  it("logout clears localStorage and transitions to unauthenticated", async () => {
    mockAuthLogout.mockResolvedValue(undefined);
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "pass" });
    });
    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.status).toBe("unauthenticated");
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem("tessera_access_token")).toBeNull();
    expect(localStorage.getItem("tessera_refresh_token")).toBeNull();
    expect(localStorage.getItem("tessera_expires_at")).toBeNull();
  });

  it("logout transitions to unauthenticated even when server call fails (best-effort)", async () => {
    mockAuthLogout.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));

    await act(async () => {
      await result.current.login({ email: "test@example.com", password: "pass" });
    });
    await act(async () => {
      await result.current.logout(); // should NOT throw even though server fails
    });

    expect(result.current.status).toBe("unauthenticated");
  });

  it("storage event with null access token causes cross-tab logout", async () => {
    const expiresAt = Date.now() + 900_000;
    localStorage.setItem("tessera_access_token", FAKE_JWT);
    localStorage.setItem("tessera_refresh_token", "rt-stored");
    localStorage.setItem("tessera_expires_at", String(expiresAt));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("authenticated"));

    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: "tessera_access_token", newValue: null })
      );
    });

    await waitFor(() => expect(result.current.status).toBe("unauthenticated"));
  });
});
