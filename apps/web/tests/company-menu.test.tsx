import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

let mockCompanies: Array<{ id: string; name: string; role: "admin" | "member" }> = [];
let mockActiveCompany: { id: string; name: string; role: "admin" | "member" } | null = null;
const mockSetActiveCompany = vi.fn();
const mockCreateAndSetActive = vi.fn();

vi.mock("@/lib/company", () => ({
  useCompany: () => ({
    companies: mockCompanies,
    activeCompany: mockActiveCompany,
    isLoading: false,
    setActiveCompany: mockSetActiveCompany,
    createAndSetActive: mockCreateAndSetActive,
    reloadCompanies: vi.fn(),
  }),
}));

import { CompanyMenu } from "@/components/company/CompanyMenu";
import { CreateCompanyModal } from "@/components/company/CreateCompanyModal";

beforeEach(() => {
  vi.clearAllMocks();
  mockCompanies = [];
  mockActiveCompany = null;
});

describe("CompanyMenu", () => {
  describe("0 companies", () => {
    it("shows a prompt to create or join a company", () => {
      mockCompanies = [];
      mockActiveCompany = null;
      render(<CompanyMenu />);
      expect(screen.getByText(/create or join/i)).toBeInTheDocument();
    });
  });

  describe("1 company", () => {
    it("shows company name as static text with no dropdown button", () => {
      mockCompanies = [{ id: "1", name: "Solo Corp", role: "admin" }];
      mockActiveCompany = { id: "1", name: "Solo Corp", role: "admin" };
      render(<CompanyMenu />);
      expect(screen.getByText("Solo Corp")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /solo corp/i })).not.toBeInTheDocument();
    });
  });

  describe("2+ companies", () => {
    beforeEach(() => {
      mockCompanies = [
        { id: "1", name: "Acme Corp", role: "admin" },
        { id: "2", name: "Beta LLC", role: "member" },
      ];
      mockActiveCompany = { id: "1", name: "Acme Corp", role: "admin" };
    });

    it("renders active company name as a button", () => {
      render(<CompanyMenu />);
      expect(screen.getByRole("button", { name: /acme corp/i })).toBeInTheDocument();
    });

    it("opens dropdown when button is clicked", () => {
      render(<CompanyMenu />);
      fireEvent.click(screen.getByRole("button", { name: /acme corp/i }));
      expect(screen.getByText("Beta LLC")).toBeInTheDocument();
    });

    it("closes dropdown on Escape key", () => {
      render(<CompanyMenu />);
      fireEvent.click(screen.getByRole("button", { name: /acme corp/i }));
      expect(screen.getByText("Beta LLC")).toBeInTheDocument();
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByText("Beta LLC")).not.toBeInTheDocument();
    });

    it("calls setActiveCompany when selecting a company", () => {
      render(<CompanyMenu />);
      fireEvent.click(screen.getByRole("button", { name: /acme corp/i }));
      fireEvent.click(screen.getByText("Beta LLC"));
      expect(mockSetActiveCompany).toHaveBeenCalledWith("2");
    });

    it("shows admin-only settings link when role is admin", () => {
      render(<CompanyMenu />);
      fireEvent.click(screen.getByRole("button", { name: /acme corp/i }));
      expect(screen.getByRole("link", { name: /company settings/i })).toBeInTheDocument();
    });

    it("hides settings link when role is member", () => {
      mockActiveCompany = { id: "2", name: "Beta LLC", role: "member" };
      render(<CompanyMenu />);
      fireEvent.click(screen.getByRole("button", { name: /beta llc/i }));
      expect(screen.queryByRole("link", { name: /company settings/i })).not.toBeInTheDocument();
    });
  });
});

describe("CreateCompanyModal", () => {
  it("renders when open is true", () => {
    render(<CreateCompanyModal open={true} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("does not render when open is false", () => {
    render(<CreateCompanyModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows inline error when submitting with empty name", async () => {
    render(<CreateCompanyModal open={true} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /create/i }));
    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    });
  });

  it("calls createAndSetActive with valid name and closes on success", async () => {
    mockCreateAndSetActive.mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(<CreateCompanyModal open={true} onClose={onClose} />);
    fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: "New Corp" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));
    await waitFor(() => {
      expect(mockCreateAndSetActive).toHaveBeenCalledWith(expect.objectContaining({ name: "New Corp" }));
    });
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("stays open and shows error on failure", async () => {
    mockCreateAndSetActive.mockRejectedValue(new Error("Server error"));
    const onClose = vi.fn();
    render(<CreateCompanyModal open={true} onClose={onClose} />);
    fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: "New Corp" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));
    await waitFor(() => {
      expect(screen.getByText(/failed to create/i)).toBeInTheDocument();
    });
    expect(onClose).not.toHaveBeenCalled();
  });
});
