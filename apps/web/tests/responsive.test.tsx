/**
 * Responsive layout smoke tests (vitest + jsdom).
 * Verifies that the correct responsive Tailwind classes are applied to elements.
 * Full overflow validation (scrollWidth === innerWidth) requires Playwright + real browser.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", logout: vi.fn() }),
}));

vi.mock("@/lib/company", () => ({
  useCompany: () => ({
    companies: [],
    activeCompany: null,
    isLoading: false,
    setActiveCompany: vi.fn(),
    createAndSetActive: vi.fn(),
    reloadCompanies: vi.fn(),
  }),
}));

import { SpaceSelector } from "@/components/SpaceSelector";
import { ProgressStepper } from "@/components/onboarding/ProgressStepper";
import { AddDocumentModal } from "@/components/documents/AddDocumentModal";
import { NavBar } from "@/components/NavBar";

describe("SpaceSelector – responsive", () => {
  it("select has w-full class", () => {
    const { container } = render(
      <SpaceSelector spaces={[]} selectedId={null} onChange={() => {}} />
    );
    const select = container.querySelector("select");
    expect(select?.classList.contains("w-full")).toBe(true);
  });
});

describe("ProgressStepper – responsive", () => {
  it("connector divs have w-6 sm:w-12 and mx-1 sm:mx-2 classes", () => {
    const { container } = render(
      <ProgressStepper currentStep="profile" completedSteps={[]} />
    );
    const connectorDivs = Array.from(
      container.querySelectorAll<HTMLElement>("div[aria-hidden]")
    );
    expect(connectorDivs.length).toBeGreaterThan(0);
    connectorDivs.forEach((div) => {
      expect(div.classList.contains("w-6")).toBe(true);
      expect(div.classList.contains("sm:w-12")).toBe(true);
      expect(div.classList.contains("mx-1")).toBe(true);
      expect(div.classList.contains("sm:mx-2")).toBe(true);
    });
  });

  it("step labels have text-[10px] sm:text-xs classes", () => {
    const { container } = render(
      <ProgressStepper currentStep="profile" completedSteps={[]} />
    );
    const labels = Array.from(container.querySelectorAll<HTMLElement>("span")).filter(
      (s) => s.classList.contains("text-[10px]")
    );
    expect(labels.length).toBeGreaterThan(0);
    labels.forEach((label) => {
      expect(label.classList.contains("sm:text-xs")).toBe(true);
    });
  });
});

describe("AddDocumentModal – responsive", () => {
  const spaces = [{ id: "s1", name: "Test Space", slug: "test", sector: "Tech", default_language: "pt-BR", confidence_threshold: 0.7, retention_policy: {} }];

  it("Language/Confidentiality grid uses grid-cols-1 sm:grid-cols-2", () => {
    const { container } = render(
      <AddDocumentModal
        open={true}
        spaces={spaces}
        onClose={() => {}}
        onCreated={() => {}}
      />
    );
    const grid = container.querySelector(".grid");
    expect(grid?.classList.contains("grid-cols-1")).toBe(true);
    expect(grid?.classList.contains("sm:grid-cols-2")).toBe(true);
  });
});

describe("NavBar – responsive", () => {
  beforeEach(() => vi.clearAllMocks());

  it("hamburger button has 44px touch target classes", () => {
    render(<NavBar />);
    const hamburger = screen.getByRole("button", { name: /open menu/i });
    expect(hamburger.classList.contains("min-h-[44px]")).toBe(true);
    expect(hamburger.classList.contains("min-w-[44px]")).toBe(true);
  });

  it("desktop link container has hidden md:flex classes", () => {
    const { container } = render(<NavBar />);
    const desktopNav = container.querySelector("div.hidden.md\\:flex");
    expect(desktopNav).not.toBeNull();
  });

  it("hamburger button has md:hidden class", () => {
    render(<NavBar />);
    const hamburger = screen.getByRole("button", { name: /open menu/i });
    expect(hamburger.classList.contains("md:hidden")).toBe(true);
  });

  it("mobile menu opens on hamburger click and shows nav links", () => {
    render(<NavBar />);
    fireEvent.click(screen.getByRole("button", { name: /open menu/i }));
    const allDocLinks = screen.getAllByRole("link", { name: /documents/i });
    expect(allDocLinks.length).toBeGreaterThan(1);
  });

  it("mobile menu closes on Escape", () => {
    render(<NavBar />);
    const hamburger = screen.getByRole("button", { name: /open menu/i });
    fireEvent.click(hamburger);
    expect(hamburger.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(hamburger.getAttribute("aria-expanded")).toBe("false");
  });
});
