import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

// --- next/navigation mock ---

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/spaces",
  useSearchParams: () => new URLSearchParams(),
}));

// --- useAuth mock ---

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// --- useCompany mock (role drives the empty-state branch, FR-007) ---

let mockCompanyRole: "admin" | "member" = "member";

vi.mock("@/lib/company", () => ({
  useCompany: () => ({
    activeCompany: { id: "c1", name: "Acme", role: mockCompanyRole },
  }),
}));

// --- api mock ---

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn() },
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as { get: ReturnType<typeof vi.fn> };

const space = {
  id: "s1",
  slug: "eng",
  name: "Engineering",
  sector: "Tech",
  parent_space_id: null,
  default_language: "en",
  confidence_threshold: 0.7,
  retention_policy: {},
  effective_role: "viewer",
  is_direct: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockCompanyRole = "member";
});

describe("SpacesPage empty state (FR-007, SC-005)", () => {
  it("a non-admin member with zero spaces sees the 'not shared yet' explanation", async () => {
    mockCompanyRole = "member";
    mockApi.get.mockResolvedValue({ spaces: [] });
    const { default: SpacesPage } = await import("@/app/spaces/page");
    render(<SpacesPage />);

    await waitFor(() =>
      expect(
        screen.getByText(/no spaces have been shared with you yet/i)
      ).toBeInTheDocument()
    );
    expect(
      screen.getByText(/company administrator can grant you access/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/no spaces available in your company/i)
    ).not.toBeInTheDocument();
  });

  it("a company admin with zero spaces keeps the existing copy and Add Space", async () => {
    mockCompanyRole = "admin";
    mockApi.get.mockResolvedValue({ spaces: [] });
    const { default: SpacesPage } = await import("@/app/spaces/page");
    render(<SpacesPage />);

    await waitFor(() =>
      expect(
        screen.getByText(/no spaces available in your company/i)
      ).toBeInTheDocument()
    );
    expect(
      screen.queryByText(/no spaces have been shared with you yet/i)
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add space/i })).toBeInTheDocument();
  });

  it("no empty-state message renders once a space is listed", async () => {
    mockCompanyRole = "member";
    mockApi.get.mockResolvedValue({ spaces: [space] });
    const { default: SpacesPage } = await import("@/app/spaces/page");
    render(<SpacesPage />);

    await waitFor(() => expect(screen.getByText("Engineering")).toBeInTheDocument());
    expect(
      screen.queryByText(/no spaces have been shared with you yet/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/no spaces available in your company/i)
    ).not.toBeInTheDocument();
  });
});
