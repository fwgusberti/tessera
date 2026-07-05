import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { CompanyMember } from "@/lib/companies";

// --- next/navigation mock ---
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/users",
  useSearchParams: () => new URLSearchParams(),
}));

// --- useAuth mock (authenticated so AuthGuard renders children) ---
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// --- companies lib mock ---
vi.mock("@/lib/companies", () => ({
  getCompanyMembers: vi.fn(),
}));

import { getCompanyMembers } from "@/lib/companies";
const mockGetCompanyMembers = getCompanyMembers as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("User Management page", () => {
  it("renders a row per member with name, email, and a role badge", async () => {
    const members: CompanyMember[] = [
      {
        user_id: "u1",
        display_name: "Ada Lovelace",
        email: "ada@acme.example",
        role: "admin",
      },
      {
        user_id: "u2",
        display_name: "Grace Hopper",
        email: "grace@acme.example",
        role: "member",
      },
    ];
    mockGetCompanyMembers.mockResolvedValue(members);

    const { default: UsersPage } = await import("@/app/users/page");
    render(<UsersPage />);

    await waitFor(() => expect(screen.getByText("Ada Lovelace")).toBeInTheDocument());
    expect(screen.getByText("ada@acme.example")).toBeInTheDocument();
    expect(screen.getByText("Grace Hopper")).toBeInTheDocument();
    expect(screen.getByText("grace@acme.example")).toBeInTheDocument();
    // Role badges render the human labels.
    expect(screen.getByText("administrator")).toBeInTheDocument();
    expect(screen.getByText("member")).toBeInTheDocument();
  });

  it("falls back to email when display_name is empty", async () => {
    const members: CompanyMember[] = [
      { user_id: "u3", display_name: "", email: "nameless@acme.example", role: "member" },
    ];
    mockGetCompanyMembers.mockResolvedValue(members);

    const { default: UsersPage } = await import("@/app/users/page");
    render(<UsersPage />);

    // The email appears as the primary identifier (and no blank row).
    await waitFor(() =>
      expect(screen.getAllByText("nameless@acme.example").length).toBeGreaterThan(0)
    );
  });

  it("shows an access-denied message and no roster when the API returns 403", async () => {
    mockGetCompanyMembers.mockRejectedValue(new Error("Access denied"));

    const { default: UsersPage } = await import("@/app/users/page");
    render(<UsersPage />);

    await waitFor(() => expect(screen.getByText(/access denied/i)).toBeInTheDocument());
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
