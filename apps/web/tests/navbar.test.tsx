import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

const mockReplace = vi.fn();
let mockPathname = "/";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => mockPathname,
  useSearchParams: () => new URLSearchParams(),
}));

const mockLogout = vi.fn();
let mockNavStatus = "authenticated" as "authenticated" | "unauthenticated" | "loading";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: mockNavStatus, logout: mockLogout }),
}));

let mockCompanies: Array<{ id: string; name: string; role: "admin" | "member" }> = [];
let mockActiveCompany: { id: string; name: string; role: "admin" | "member" } | null = null;

vi.mock("@/lib/company", () => ({
  useCompany: () => ({
    companies: mockCompanies,
    activeCompany: mockActiveCompany,
    isLoading: false,
    setActiveCompany: vi.fn(),
    createAndSetActive: vi.fn(),
    reloadCompanies: vi.fn(),
  }),
}));

import { NavBar } from "@/components/NavBar";

beforeEach(() => {
  vi.clearAllMocks();
  mockNavStatus = "authenticated";
  mockPathname = "/";
  mockLogout.mockResolvedValue(undefined);
  mockCompanies = [];
  mockActiveCompany = null;
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

// ─── US2: Chat / Documents nav links ─────────────────────────────────────────

describe("NavBar — Chat/Documents nav links (US2)", () => {
  it("renders a Chat link pointing to /", () => {
    render(<NavBar />);
    const chatLinks = screen.getAllByRole("link", { name: /^chat$/i });
    expect(chatLinks.length).toBeGreaterThan(0);
    expect(chatLinks[0]).toHaveAttribute("href", "/");
  });

  it("renders a Documents link pointing to /documents", () => {
    render(<NavBar />);
    const docLinks = screen.getAllByRole("link", { name: /^documents$/i });
    expect(docLinks.length).toBeGreaterThan(0);
    expect(docLinks[0]).toHaveAttribute("href", "/documents");
  });

  it("Chat link is visible in the desktop nav", () => {
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector(".hidden.md\\:flex");
    expect(desktopNav).toBeInTheDocument();
    const chatLink = desktopNav!.querySelector('a[href="/"]');
    expect(chatLink).toBeInTheDocument();
    expect(chatLink!.textContent).toBe("Chat");
  });

  it("Documents link is visible in the desktop nav", () => {
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector(".hidden.md\\:flex");
    const docLink = desktopNav!.querySelector('a[href="/documents"]');
    expect(docLink).toBeInTheDocument();
    expect(docLink!.textContent).toBe("Documents");
  });

  it("mobile menu contains Chat entry", () => {
    render(<NavBar />);
    fireEvent.click(screen.getByRole("button", { name: /open menu/i }));
    const chatLinks = screen.getAllByRole("link", { name: /^chat$/i });
    expect(chatLinks.length).toBeGreaterThanOrEqual(2);
  });

  it("mobile menu contains Documents entry", () => {
    render(<NavBar />);
    fireEvent.click(screen.getByRole("button", { name: /open menu/i }));
    const docLinks = screen.getAllByRole("link", { name: /^documents$/i });
    expect(docLinks.length).toBeGreaterThanOrEqual(2);
  });

  it("Chat link has active styling when pathname is /", () => {
    mockPathname = "/";
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector(".hidden.md\\:flex");
    const chatLink = desktopNav!.querySelector('a[href="/"]');
    expect(chatLink!.className).toContain("text-indigo-600");
    expect(chatLink!.className).toContain("font-medium");
  });

  it("Chat link has inactive styling when pathname is /documents", () => {
    mockPathname = "/documents";
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector(".hidden.md\\:flex");
    const chatLink = desktopNav!.querySelector('a[href="/"]');
    expect(chatLink!.className).toContain("text-slate-600");
    expect(chatLink!.className).not.toContain("text-indigo-600");
  });

  it("Documents link has active styling when pathname is /documents", () => {
    mockPathname = "/documents";
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector(".hidden.md\\:flex");
    const docLink = desktopNav!.querySelector('a[href="/documents"]');
    expect(docLink!.className).toContain("text-indigo-600");
    expect(docLink!.className).toContain("font-medium");
  });

  it("Documents link has inactive styling when pathname is /", () => {
    mockPathname = "/";
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector(".hidden.md\\:flex");
    const docLink = desktopNav!.querySelector('a[href="/documents"]');
    expect(docLink!.className).toContain("text-slate-600");
    expect(docLink!.className).not.toContain("text-indigo-600");
  });
});

// ─── CompanyMenu presence in NavBar ──────────────────────────────────────────

describe("NavBar — CompanyMenu presence", () => {
  it("shows company name in desktop bar when authenticated and has companies", () => {
    mockNavStatus = "authenticated";
    mockCompanies = [{ id: "1", name: "Acme Corp", role: "admin" }];
    mockActiveCompany = { id: "1", name: "Acme Corp", role: "admin" };
    render(<NavBar />);
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("does not show company menu when unauthenticated", () => {
    mockNavStatus = "unauthenticated";
    mockCompanies = [{ id: "1", name: "Acme Corp", role: "admin" }];
    mockActiveCompany = { id: "1", name: "Acme Corp", role: "admin" };
    render(<NavBar />);
    expect(screen.queryByText("Acme Corp")).not.toBeInTheDocument();
  });

  it("shows company menu in mobile menu when authenticated", () => {
    mockNavStatus = "authenticated";
    mockCompanies = [{ id: "1", name: "Acme Corp", role: "admin" }];
    mockActiveCompany = { id: "1", name: "Acme Corp", role: "admin" };
    render(<NavBar />);
    fireEvent.click(screen.getByRole("button", { name: /open menu/i }));
    const acmeTexts = screen.getAllByText("Acme Corp");
    expect(acmeTexts.length).toBeGreaterThanOrEqual(1);
  });
});
