import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { CompanyMember } from "@/lib/companies";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/users",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Active-company role is admin → the add affordance must be visible (US4).
vi.mock("@/lib/company", () => ({
  useCompany: () => ({ activeCompany: { id: "c1", name: "Acme", role: "admin" } }),
}));

vi.mock("@/lib/companies", () => ({
  getCompanyMembers: vi.fn(),
  inviteCompanyMember: vi.fn(),
  searchAddableUsers: vi.fn(),
  addCompanyMember: vi.fn(),
}));

import { getCompanyMembers } from "@/lib/companies";
const mockGetCompanyMembers = getCompanyMembers as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("User Management page — admin add affordance (US4)", () => {
  it("shows the 'Add user' button for an admin of the active company", async () => {
    const members: CompanyMember[] = [
      { user_id: "u1", display_name: "Ada", email: "ada@acme.example", role: "admin" },
    ];
    mockGetCompanyMembers.mockResolvedValue(members);

    const { default: UsersPage } = await import("@/app/users/page");
    render(<UsersPage />);

    await waitFor(() => expect(screen.getByText("Ada")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /add user/i })).toBeInTheDocument();
  });
});
