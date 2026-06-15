import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

const mockPush = vi.fn();
const mockReplace = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
  usePathname: () => "/login",
}));

const mockLogin = vi.fn();
let mockStatus: "unauthenticated" | "authenticated" | "loading" = "unauthenticated";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: mockStatus, login: mockLogin }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import LoginPage from "@/app/login/page";

beforeEach(() => {
  vi.clearAllMocks();
  mockStatus = "unauthenticated";
  mockSearchParams = new URLSearchParams();
});

describe("LoginPage", () => {
  it("renders email input, password input, and submit button", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows validation error for empty email without making a network request", async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("shows validation error for empty password without making a network request", async () => {
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("calls login and redirects to '/' on success when no redirect param", async () => {
    mockSearchParams = new URLSearchParams(); // no redirect
    mockLogin.mockResolvedValue(undefined);
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({ email: "user@example.com", password: "password123" });
    });
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("redirects to the ?redirect param path after successful login", async () => {
    mockSearchParams = new URLSearchParams("redirect=/documents");
    mockLogin.mockResolvedValue(undefined);
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "pass123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/documents"));
  });

  it("shows an error message when login returns invalid credentials", async () => {
    mockLogin.mockRejectedValue(new Error("Invalid credentials"));
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "bad@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("shows generic error message for service errors (non-credentials failures)", async () => {
    mockLogin.mockRejectedValue(new Error("Internal Server Error"));
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "pass123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });

  it("redirects to '/' when status is already authenticated on mount", async () => {
    mockStatus = "authenticated";
    render(<LoginPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/"));
  });

  it("renders a 'Create account' link pointing to /register", () => {
    render(<LoginPage />);
    expect(screen.getByRole("link", { name: /create account/i })).toHaveAttribute("href", "/register");
  });

  it("includes redirect param in 'Create account' link when ?redirect is present", () => {
    mockSearchParams = new URLSearchParams("redirect=/documents");
    render(<LoginPage />);
    expect(screen.getByRole("link", { name: /create account/i })).toHaveAttribute(
      "href",
      "/register?redirect=%2Fdocuments"
    );
  });
});
