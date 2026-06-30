import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { Space } from "@/lib/types";

// --- next/navigation mock (usePathname returns /spaces so AuthGuard redirects there) ---

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  usePathname: () => "/spaces",
  useSearchParams: () => new URLSearchParams(),
}));

// --- useAuth mock ---

let mockAuthStatus: "authenticated" | "unauthenticated" | "loading" = "authenticated";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: mockAuthStatus }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// --- api mock ---

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn() },
}));

// NOTE: @/lib/auth-guard is NOT mocked — the real AuthGuard is used so that
// the redirect test exercises the actual guard behaviour.

import { api } from "@/lib/api";
const mockApi = api as unknown as { get: ReturnType<typeof vi.fn> };

// --- Fixtures ---

const space1: Space = {
  id: "s1",
  slug: "zebra",
  name: "Zebra Space",
  sector: "Tech",
  default_language: "en",
  confidence_threshold: 0.7,
  retention_policy: {},
};

const space2: Space = {
  id: "s2",
  slug: "alpha",
  name: "Alpha Space",
  sector: "Finance",
  default_language: "en",
  confidence_threshold: 0.7,
  retention_policy: {},
};

// --- Setup ---

beforeEach(() => {
  vi.clearAllMocks();
  mockAuthStatus = "authenticated";
});

// --- Tests ---

describe("SpacesPage", () => {
  it("shows a loading indicator immediately after mount", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockReturnValue(new Promise(() => {}));
    render(<SpacesPage />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows empty-state message when API returns an empty list", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockResolvedValue({ spaces: [] });
    render(<SpacesPage />);
    await waitFor(() => expect(screen.getByText(/no spaces/i)).toBeInTheDocument());
  });

  it("shows error message when GET /v1/spaces fails", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockRejectedValue(new Error("Network error"));
    render(<SpacesPage />);
    await waitFor(() => expect(screen.getByText(/network error/i)).toBeInTheDocument());
  });

  it("renders the correct number of space cards", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: [space1, space2] });
      return Promise.reject(Object.assign(new Error("Not found"), { status: 404 }));
    });
    render(<SpacesPage />);
    await waitFor(() => expect(screen.getAllByRole("article").length).toBe(2));
  });

  it("renders space cards sorted alphabetically by name", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    // API returns spaces in reverse alphabetical order; page must sort them
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: [space1, space2] });
      return Promise.reject(Object.assign(new Error("Not found"), { status: 404 }));
    });
    render(<SpacesPage />);
    await waitFor(() => {
      const cards = screen.getAllByRole("article");
      expect(cards[0]).toHaveTextContent("Alpha Space");
      expect(cards[1]).toHaveTextContent("Zebra Space");
    });
  });

  it("redirects unauthenticated users to /login?redirect=%2Fspaces", async () => {
    mockAuthStatus = "unauthenticated";
    const { default: SpacesPage } = await import("@/app/spaces/page");
    render(<SpacesPage />);
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login?redirect=%2Fspaces");
    });
  });
});
