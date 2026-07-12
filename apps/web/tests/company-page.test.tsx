import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { CompanyProfile } from "@/lib/companies";

// --- next/navigation mock ---
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/settings/company",
  useSearchParams: () => new URLSearchParams(),
}));

// --- useAuth mock (authenticated so AuthGuard renders children) ---
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// --- company context mock (reloadCompanies observable for FR-007) ---
const mockReloadCompanies = vi.fn();
vi.mock("@/lib/company", () => ({
  useCompany: () => ({
    activeCompany: { id: "c1", name: "Acme Corp", role: "admin" },
    reloadCompanies: mockReloadCompanies,
  }),
}));

// --- companies lib mock ---
vi.mock("@/lib/companies", () => ({
  getCurrentCompany: vi.fn(),
  updateCurrentCompany: vi.fn(),
}));

import { getCurrentCompany, updateCurrentCompany } from "@/lib/companies";
const mockGetCurrentCompany = getCurrentCompany as unknown as ReturnType<typeof vi.fn>;
const mockUpdateCurrentCompany = updateCurrentCompany as unknown as ReturnType<typeof vi.fn>;

const adminProfile: CompanyProfile = {
  id: "c1",
  name: "Acme Corp",
  industry: "Technology",
  team_size: "11-50",
  created_at: "2026-03-14T09:26:53Z",
  role: "admin",
};

const memberProfile: CompanyProfile = { ...adminProfile, role: "member" };

async function renderPage() {
  const { default: CompanyPage } = await import("@/app/settings/company/page");
  render(<CompanyPage />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Company page — view mode (US1)", () => {
  it("renders name, industry, team size, and formatted creation date", async () => {
    mockGetCurrentCompany.mockResolvedValue(adminProfile);

    await renderPage();

    await waitFor(() => expect(screen.getByText("Acme Corp")).toBeInTheDocument());
    expect(screen.getByText("Technology")).toBeInTheDocument();
    expect(screen.getByText("11-50")).toBeInTheDocument();
    expect(screen.getByText("March 14, 2026")).toBeInTheDocument();
  });

  it("renders 'Not provided' for null industry and team size (FR-003)", async () => {
    mockGetCurrentCompany.mockResolvedValue({
      ...memberProfile,
      industry: null,
      team_size: null,
    });

    await renderPage();

    await waitFor(() => expect(screen.getByText("Acme Corp")).toBeInTheDocument());
    expect(screen.getAllByText("Not provided")).toHaveLength(2);
  });

  it("shows the creation date as display-only text (no form controls in view mode)", async () => {
    mockGetCurrentCompany.mockResolvedValue(memberProfile);

    await renderPage();

    await waitFor(() => expect(screen.getByText("March 14, 2026")).toBeInTheDocument());
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });
});

describe("Company page — edit mode (US2, admin)", () => {
  it("shows the Edit button when the caller's role is admin", async () => {
    mockGetCurrentCompany.mockResolvedValue(adminProfile);

    await renderPage();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument()
    );
  });

  it("prefills the form with current values using the shared option lists", async () => {
    mockGetCurrentCompany.mockResolvedValue(adminProfile);

    await renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));

    expect(screen.getByLabelText(/company name/i)).toHaveValue("Acme Corp");
    expect(screen.getByLabelText(/industry/i)).toHaveValue("Technology");
    expect(screen.getByLabelText(/team size/i)).toHaveValue("11-50");
    // Shared onboarding options are available in the selects.
    expect(screen.getByRole("option", { name: "Healthcare" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /201-1000/ })).toBeInTheDocument();
    // The creation date is never editable.
    expect(screen.queryByLabelText(/creat/i)).not.toBeInTheDocument();
  });

  it("saves, returns to view mode with response values, and reloads companies (FR-007)", async () => {
    mockGetCurrentCompany.mockResolvedValue(adminProfile);
    mockUpdateCurrentCompany.mockResolvedValue({
      ...adminProfile,
      name: "Acme Corporation",
      team_size: "51-200",
    });

    await renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.change(screen.getByLabelText(/company name/i), {
      target: { value: "Acme Corporation" },
    });
    fireEvent.change(screen.getByLabelText(/team size/i), { target: { value: "51-200" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(mockUpdateCurrentCompany).toHaveBeenCalledWith({
        name: "Acme Corporation",
        industry: "Technology",
        team_size: "51-200",
      })
    );
    await waitFor(() => expect(screen.getByText("Acme Corporation")).toBeInTheDocument());
    // Back in view mode.
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByText("51-200")).toBeInTheDocument();
    expect(mockReloadCompanies).toHaveBeenCalled();
  });

  it("cancel discards changes and restores original values (FR-006)", async () => {
    mockGetCurrentCompany.mockResolvedValue(adminProfile);

    await renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.change(screen.getByLabelText(/company name/i), {
      target: { value: "Discarded Name" },
    });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(mockUpdateCurrentCompany).not.toHaveBeenCalled();
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.queryByText("Discarded Name")).not.toBeInTheDocument();

    // Re-opening the form shows the original values again.
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    expect(screen.getByLabelText(/company name/i)).toHaveValue("Acme Corp");
  });

  it("blocks an empty name client-side with a message (FR-005)", async () => {
    mockGetCurrentCompany.mockResolvedValue(adminProfile);

    await renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(screen.getByText(/name is required/i)).toBeInTheDocument()
    );
    expect(mockUpdateCurrentCompany).not.toHaveBeenCalled();
  });

  it("stays in edit mode with entered values and shows a banner when the save fails", async () => {
    mockGetCurrentCompany.mockResolvedValue(adminProfile);
    mockUpdateCurrentCompany.mockRejectedValue(new Error("name must not be blank"));

    await renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.change(screen.getByLabelText(/company name/i), {
      target: { value: "Kept After Failure" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(screen.getByText(/name must not be blank/i)).toBeInTheDocument()
    );
    // Still in edit mode with the entered value intact.
    expect(screen.getByLabelText(/company name/i)).toHaveValue("Kept After Failure");
    expect(mockReloadCompanies).not.toHaveBeenCalled();
  });
});

describe("Company page — read-only for members (US3)", () => {
  it("renders no edit controls when the caller's role is member", async () => {
    mockGetCurrentCompany.mockResolvedValue(memberProfile);

    await renderPage();

    await waitFor(() => expect(screen.getByText("Acme Corp")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });
});
