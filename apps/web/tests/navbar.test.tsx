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

  it("hamburger button is visible and has accessible label", () => {
    render(<NavBar />);
    const hamburger = screen.getByRole("button", { name: /open menu/i });
    expect(hamburger).toBeInTheDocument();
    expect(hamburger.className).toContain("min-h-[44px]");
    expect(hamburger.className).toContain("min-w-[44px]");
  });

  it("desktop link row has hidden md:flex classes", () => {
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector(".hidden.md\\:flex");
    expect(desktopNav).toBeInTheDocument();
  });

  it("mobile menu opens when hamburger is clicked", () => {
    render(<NavBar />);
    const hamburger = screen.getByRole("button", { name: /open menu/i });
    expect(hamburger.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(hamburger);

    expect(hamburger.getAttribute("aria-expanded")).toBe("true");
    // Mobile menu links appear (there are now two sets of nav links — desktop hidden + mobile visible)
    const searchLinks = screen.getAllByRole("link", { name: /search/i });
    expect(searchLinks.length).toBeGreaterThan(1);
  });

  it("mobile menu closes when a nav link is clicked", () => {
    render(<NavBar />);
    const hamburger = screen.getByRole("button", { name: /open menu/i });
    fireEvent.click(hamburger);

    // Find and click a mobile menu link
    const searchLinks = screen.getAllByRole("link", { name: /search/i });
    fireEvent.click(searchLinks[searchLinks.length - 1]);

    expect(hamburger.getAttribute("aria-expanded")).toBe("false");
  });

  it("mobile menu closes when Escape key is pressed", () => {
    render(<NavBar />);
    const hamburger = screen.getByRole("button", { name: /open menu/i });
    fireEvent.click(hamburger);
    expect(hamburger.getAttribute("aria-expanded")).toBe("true");

    fireEvent.keyDown(document, { key: "Escape" });

    expect(hamburger.getAttribute("aria-expanded")).toBe("false");
  });
});
