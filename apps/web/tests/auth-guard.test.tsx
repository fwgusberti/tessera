import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => "/protected",
  useSearchParams: () => new URLSearchParams(),
}));

let mockAuthStatus = "unauthenticated" as "unauthenticated" | "authenticated" | "loading";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: mockAuthStatus }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { AuthGuard } from "@/lib/auth-guard";

beforeEach(() => {
  vi.clearAllMocks();
  mockAuthStatus = "unauthenticated";
});

describe("AuthGuard", () => {
  it("renders null and redirects to /login?redirect= when unauthenticated", async () => {
    mockAuthStatus = "unauthenticated";
    render(
      <AuthGuard>
        <p>Protected Content</p>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login?redirect=%2Fprotected");
    });
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    mockAuthStatus = "authenticated";
    render(
      <AuthGuard>
        <p>Protected Content</p>
      </AuthGuard>
    );
    expect(screen.getByText("Protected Content")).toBeInTheDocument();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("renders null without redirecting when loading", () => {
    mockAuthStatus = "loading";
    render(
      <AuthGuard>
        <p>Protected Content</p>
      </AuthGuard>
    );
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("redirects when status transitions from loading to unauthenticated", async () => {
    mockAuthStatus = "loading";
    const { rerender } = render(
      <AuthGuard>
        <p>Protected Content</p>
      </AuthGuard>
    );

    expect(mockReplace).not.toHaveBeenCalled();

    mockAuthStatus = "unauthenticated";
    rerender(
      <AuthGuard>
        <p>Protected Content</p>
      </AuthGuard>
    );

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/login?redirect=%2Fprotected"));
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });
});

// ─── Post-logout behaviour ────────────────────────────────────────────────────

describe("AuthGuard / post-logout", () => {
  it("redirects to /login when status transitions from authenticated to unauthenticated", async () => {
    mockAuthStatus = "authenticated";
    const { rerender } = render(
      <AuthGuard>
        <p>Dashboard</p>
      </AuthGuard>
    );
    expect(screen.getByText("Dashboard")).toBeInTheDocument();

    mockAuthStatus = "unauthenticated";
    rerender(
      <AuthGuard>
        <p>Dashboard</p>
      </AuthGuard>
    );

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/login?redirect=%2Fprotected"));
    expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
  });
});
