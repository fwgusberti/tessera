import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { AuthStatus, TokenKind } from "@/lib/types";

const mockReplace = vi.fn();
let mockPathname = "/spaces";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => mockPathname,
}));

let mockStatus: AuthStatus = "authenticated";
let mockTokenKind: TokenKind = "select";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: mockStatus,
    user:
      mockStatus === "authenticated"
        ? {
            id: "user-1",
            email: "test@example.com",
            isAdmin: false,
            tokenKind: mockTokenKind,
            companyId: mockTokenKind === "full" ? "co-1" : null,
          }
        : null,
  }),
}));

import { TenantGuard } from "@/lib/auth-guard";

beforeEach(() => {
  vi.clearAllMocks();
  mockStatus = "authenticated";
  mockTokenKind = "select";
  mockPathname = "/spaces";
});

function renderGuard() {
  return render(
    <TenantGuard>
      <div data-testid="child">content</div>
    </TenantGuard>
  );
}

describe("TenantGuard", () => {
  it("redirects an authenticated select-kind session on a protected path and renders nothing", () => {
    mockPathname = "/spaces";
    renderGuard();

    expect(mockReplace).toHaveBeenCalledWith(
      "/select-company?redirect=" + encodeURIComponent("/spaces")
    );
    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
  });

  it("encodes nested paths in the redirect param", () => {
    mockPathname = "/documents/abc/edit";
    renderGuard();

    expect(mockReplace).toHaveBeenCalledWith(
      "/select-company?redirect=" + encodeURIComponent("/documents/abc/edit")
    );
  });

  it.each(["/login", "/register", "/select-company", "/forgot-password", "/reset-password"])(
    "passes through on exempt path %s",
    (path) => {
      mockPathname = path;
      renderGuard();

      expect(mockReplace).not.toHaveBeenCalled();
      expect(screen.getByTestId("child")).toBeInTheDocument();
    }
  );

  it("passes through full-token sessions", () => {
    mockTokenKind = "full";
    renderGuard();

    expect(mockReplace).not.toHaveBeenCalled();
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("passes through onboarding-token sessions", () => {
    mockTokenKind = "onboarding";
    renderGuard();

    expect(mockReplace).not.toHaveBeenCalled();
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("passes through unauthenticated sessions", () => {
    mockStatus = "unauthenticated";
    renderGuard();

    expect(mockReplace).not.toHaveBeenCalled();
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("passes through while auth status is loading", () => {
    mockStatus = "loading";
    renderGuard();

    expect(mockReplace).not.toHaveBeenCalled();
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });
});
