import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const mockLogout = vi.fn();
let mockNavStatus = "authenticated" as "authenticated" | "unauthenticated" | "loading";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: mockNavStatus, logout: mockLogout }),
}));

import { NavBar } from "@/components/NavBar";

beforeEach(() => {
  vi.clearAllMocks();
  mockNavStatus = "authenticated";
  mockLogout.mockResolvedValue(undefined);
});

describe("NavBar", () => {
  it("renders navigation links", () => {
    render(<NavBar />);
    expect(screen.getByRole("link", { name: /search/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /documents/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /proposals/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /metrics/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /admin/i })).toBeInTheDocument();
  });

  it("shows Sign out button when authenticated", () => {
    mockNavStatus = "authenticated";
    render(<NavBar />);
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
  });

  it("does not show Sign out button when unauthenticated", () => {
    mockNavStatus = "unauthenticated";
    render(<NavBar />);
    expect(screen.queryByRole("button", { name: /sign out/i })).not.toBeInTheDocument();
  });

  it("does not show Sign out button while loading", () => {
    mockNavStatus = "loading";
    render(<NavBar />);
    expect(screen.queryByRole("button", { name: /sign out/i })).not.toBeInTheDocument();
  });

  it("clicking Sign out calls logout() and navigates to /login", async () => {
    mockNavStatus = "authenticated";
    render(<NavBar />);

    fireEvent.click(screen.getByRole("button", { name: /sign out/i }));

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });
});
