import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import Home from "@/app/page";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "t@t.com", isAdmin: false }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn> };

describe("Home dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders stat cards with data from API", async () => {
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: [{}, {}, {}] });
      if (path === "/v1/metrics") return Promise.resolve({ total_queries: 42, documents_with_drift: 7 });
      return Promise.resolve({});
    });

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
    });

    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("shows dash placeholders when both API calls fail", async () => {
    mockApi.get.mockRejectedValue(new Error("Network error"));

    render(<Home />);

    await waitFor(() => {
      const dashes = screen.getAllByText("–");
      expect(dashes.length).toBeGreaterThanOrEqual(3);
    });
  });

  it("renders quick-nav links for all major sections", async () => {
    mockApi.get.mockResolvedValue({ spaces: [], total_queries: 0, documents_with_drift: 0 });

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /search/i })).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: /proposals/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /metrics/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /admin/i })).toBeInTheDocument();
  });

  it("does not render the Next.js boilerplate deploy button", async () => {
    mockApi.get.mockResolvedValue({ spaces: [], total_queries: 0, documents_with_drift: 0 });

    render(<Home />);

    await waitFor(() => {
      expect(screen.queryByText(/deploy now/i)).not.toBeInTheDocument();
    });
  });
});
