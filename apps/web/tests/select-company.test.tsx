import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { AuthUser, AuthStatus } from "@/lib/types";

const mockPush = vi.fn();
const mockReplace = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
  usePathname: () => "/select-company",
}));

const mockSelectTenant = vi.fn();
const mockLogout = vi.fn();
let mockStatus: AuthStatus = "authenticated";
let mockUser: AuthUser | null = null;

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: mockStatus,
    user: mockUser,
    selectTenant: mockSelectTenant,
    logout: mockLogout,
  }),
}));

const mockGetMyCompanies = vi.fn();
vi.mock("@/lib/companies", () => ({
  getMyCompanies: (...args: unknown[]) => mockGetMyCompanies(...args),
}));

import SelectCompanyPage from "@/app/select-company/page";
import { ApiError } from "@/lib/api";

const SELECT_USER: AuthUser = {
  id: "user-1",
  email: "test@example.com",
  isAdmin: false,
  tokenKind: "select",
  companyId: null,
};

const COMPANIES = [
  { id: "co-1", name: "Acme", role: "admin" as const },
  { id: "co-2", name: "Beta Corp", role: "member" as const },
];

beforeEach(() => {
  vi.clearAllMocks();
  mockStatus = "authenticated";
  mockUser = SELECT_USER;
  mockSearchParams = new URLSearchParams();
  mockGetMyCompanies.mockResolvedValue(COMPANIES);
});

describe("SelectCompanyPage / redirects", () => {
  it("redirects unauthenticated sessions to /login", async () => {
    mockStatus = "unauthenticated";
    mockUser = null;
    render(<SelectCompanyPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/login"));
  });

  it("redirects full-token sessions to the sanitized redirect destination", async () => {
    mockUser = { ...SELECT_USER, tokenKind: "full", companyId: "co-1" };
    mockSearchParams = new URLSearchParams("redirect=/documents");
    render(<SelectCompanyPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/documents"));
  });

  it("redirects full-token sessions to '/' when no redirect param", async () => {
    mockUser = { ...SELECT_USER, tokenKind: "full", companyId: "co-1" };
    render(<SelectCompanyPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/"));
  });

  it("ignores unsafe redirect values for full-token sessions (must start with '/', not '//')", async () => {
    mockUser = { ...SELECT_USER, tokenKind: "full", companyId: "co-1" };
    mockSearchParams = new URLSearchParams("redirect=//evil.example.com");
    render(<SelectCompanyPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/"));
  });

  it("redirects onboarding-token sessions to /onboarding", async () => {
    mockUser = { ...SELECT_USER, tokenKind: "onboarding" };
    render(<SelectCompanyPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/onboarding"));
  });
});

describe("SelectCompanyPage / picker", () => {
  it("renders one action per company showing name and role badge", async () => {
    render(<SelectCompanyPage />);

    expect(await screen.findByRole("button", { name: /acme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /beta corp/i })).toBeInTheDocument();
    expect(screen.getByText(/admin/i)).toBeInTheDocument();
    expect(screen.getByText(/member/i)).toBeInTheDocument();
  });

  it("picking a company calls selectTenant and navigates to the sanitized redirect", async () => {
    mockSearchParams = new URLSearchParams("redirect=/spaces");
    mockSelectTenant.mockResolvedValue(undefined);
    render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /acme/i }));

    await waitFor(() => expect(mockSelectTenant).toHaveBeenCalledWith("co-1"));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/spaces"));
  });

  it("picking a company navigates to '/' when no redirect param", async () => {
    mockSelectTenant.mockResolvedValue(undefined);
    render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /beta corp/i }));

    await waitFor(() => expect(mockSelectTenant).toHaveBeenCalledWith("co-2"));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/"));
  });

  it("ignores unsafe redirect values when navigating after a pick", async () => {
    mockSearchParams = new URLSearchParams("redirect=//evil.example.com");
    mockSelectTenant.mockResolvedValue(undefined);
    render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /acme/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/"));
  });
});

describe("SelectCompanyPage / selection failures", () => {
  it("shows the company-unavailable copy, keeps the picker interactive, and re-fetches on company_suspended", async () => {
    mockSelectTenant.mockRejectedValue(
      new ApiError("Company is suspended", "company_suspended", 403)
    );
    render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /acme/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/suspended/i);
    expect(mockPush).not.toHaveBeenCalled();
    await waitFor(() => expect(mockGetMyCompanies).toHaveBeenCalledTimes(2));

    // Picker stays interactive: the other company is still selectable
    const other = screen.getByRole("button", { name: /beta corp/i });
    expect(other).toBeEnabled();
  });

  it("shows the no-longer-have-access copy and the refreshed list drops the revoked company on not_a_member", async () => {
    mockSelectTenant.mockRejectedValue(
      new ApiError("Not a member of this company", "not_a_member", 403)
    );
    mockGetMyCompanies
      .mockResolvedValueOnce(COMPANIES)
      .mockResolvedValueOnce([COMPANIES[0]]); // Beta Corp revoked

    render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /beta corp/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/no longer have access/i);
    await waitFor(() => expect(mockGetMyCompanies).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /beta corp/i })).not.toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /acme/i })).toBeEnabled();
  });

  it("shows generic copy for unknown error codes", async () => {
    mockSelectTenant.mockRejectedValue(new ApiError("Boom", "some_unknown_code", 500));
    render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /acme/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/something went wrong/i);
  });

  it("never renders the raw credential_not_scoped backend message", async () => {
    mockSelectTenant.mockRejectedValue(
      new ApiError(
        "Credential is not scoped to a tenant; call /auth/select-tenant first",
        "credential_not_scoped",
        403
      )
    );
    const { container } = render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /acme/i }));

    await screen.findByRole("alert");
    expect(container.textContent).not.toContain("Credential is not scoped to a tenant");
  });
});

describe("SelectCompanyPage / sign out", () => {
  it("offers a Sign out action that calls logout() and routes to /login", async () => {
    mockLogout.mockResolvedValue(undefined);
    render(<SelectCompanyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /sign out/i }));

    await waitFor(() => expect(mockLogout).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/login"));
  });
});
