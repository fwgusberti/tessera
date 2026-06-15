import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

const mockPush = vi.fn();
const mockReplace = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
  usePathname: () => "/register",
}));

const mockLogin = vi.fn();
let mockStatus: "unauthenticated" | "authenticated" | "loading" = "unauthenticated";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: mockStatus, login: mockLogin }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockAuthRegister = vi.fn();

vi.mock("@/lib/api", () => ({
  authRegister: (...args: unknown[]) => mockAuthRegister(...args),
}));

import RegisterPage from "@/app/register/page";

beforeEach(() => {
  vi.clearAllMocks();
  mockStatus = "unauthenticated";
  mockSearchParams = new URLSearchParams();
});

describe("RegisterPage", () => {
  it("renders display name, email, password inputs and submit button", () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText(/display name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("shows sign-in link", () => {
    render(<RegisterPage />);
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute("href", "/login");
  });

  // ── US1: Complete Registration Flow ─────────────────────────────────────────

  it("calls authRegister then login and redirects to / on success with no redirect param", async () => {
    mockAuthRegister.mockResolvedValue(undefined);
    mockLogin.mockResolvedValue(undefined);
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockAuthRegister).toHaveBeenCalledWith("Alice", "alice@example.com", "password123");
    });
    expect(mockLogin).toHaveBeenCalledWith({ email: "alice@example.com", password: "password123" });
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("redirects to ?redirect= destination after successful registration", async () => {
    mockSearchParams = new URLSearchParams("redirect=/documents");
    mockAuthRegister.mockResolvedValue(undefined);
    mockLogin.mockResolvedValue(undefined);
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Bob" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "bob@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/documents"));
  });

  it("ignores unsafe ?redirect= value and falls back to /", async () => {
    mockSearchParams = new URLSearchParams("redirect=//evil.com");
    mockAuthRegister.mockResolvedValue(undefined);
    mockLogin.mockResolvedValue(undefined);
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Carol" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "carol@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/"));
  });

  it("shows display name required error and blocks submission when name is empty", async () => {
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/display name is required/i)).toBeInTheDocument();
    });
    expect(mockAuthRegister).not.toHaveBeenCalled();
  });

  it("shows display name too long error when name exceeds 100 characters", async () => {
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "a".repeat(101) } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/100 characters or fewer/i)).toBeInTheDocument();
    });
    expect(mockAuthRegister).not.toHaveBeenCalled();
  });

  it("shows email required error and blocks submission when email is empty", async () => {
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
    expect(mockAuthRegister).not.toHaveBeenCalled();
  });

  it("shows invalid email error for malformed email", async () => {
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "notanemail" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/valid email/i)).toBeInTheDocument();
    });
    expect(mockAuthRegister).not.toHaveBeenCalled();
  });

  it("shows password required error when password is empty", async () => {
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
    expect(mockAuthRegister).not.toHaveBeenCalled();
  });

  it("shows password too short error when password is less than 8 characters", async () => {
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
    expect(mockAuthRegister).not.toHaveBeenCalled();
  });

  it("shows password strength indicator as user types", async () => {
    render(<RegisterPage />);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(passwordInput, { target: { value: "weakpas" } });
    // Too short — strength not shown (field not yet valid length)

    fireEvent.change(passwordInput, { target: { value: "password" } });
    await waitFor(() => {
      expect(screen.getByText(/password strength/i)).toBeInTheDocument();
    });
  });

  it("redirects already-authenticated user to / without rendering the form", async () => {
    mockStatus = "authenticated";
    render(<RegisterPage />);
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/"));
    expect(screen.queryByRole("button", { name: /create account/i })).not.toBeInTheDocument();
  });

  it("disables submit button while request is in flight", async () => {
    let resolve!: () => void;
    mockAuthRegister.mockReturnValue(new Promise<void>((r) => { resolve = r; }));
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /creating account/i })).toBeDisabled();
    });
    resolve();
  });

  // ── US2: Duplicate Email Handling ────────────────────────────────────────────

  it("shows email already registered error with sign-in link on 409 conflict", async () => {
    mockAuthRegister.mockRejectedValue(new Error("Email already registered"));
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "existing@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/already registered/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /sign in instead/i })).toHaveAttribute("href", "/login");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("shows generic error message for non-conflict server errors", async () => {
    mockAuthRegister.mockRejectedValue(new Error("Internal Server Error"));
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@example.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("link", { name: /sign in instead/i })).not.toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });

  // ── US3: Navigation — register page side ────────────────────────────────────

  it("renders a sign-in link pointing to /login", () => {
    render(<RegisterPage />);
    const link = screen.getByRole("link", { name: /sign in/i });
    expect(link).toHaveAttribute("href", "/login");
  });
});
