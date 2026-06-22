import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import Home from "@/app/page";

vi.mock("@/lib/chat", () => ({
  askAssistant: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "t@t.com", isAdmin: false }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("Home dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the chat interface as the primary content element", () => {
    render(<Home />);

    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask/i })).toBeInTheDocument();
  });

  it("renders the Tessera heading on the welcome screen", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: /tessera/i })).toBeInTheDocument();
  });

  it("renders starter prompt chips on the welcome screen", () => {
    render(<Home />);
    expect(screen.getByText("What's in our product roadmap?")).toBeInTheDocument();
  });

  it("does not render stat cards", () => {
    render(<Home />);
    expect(screen.queryByText(/spaces/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/total queries/i)).not.toBeInTheDocument();
  });

  it("does not render the Next.js boilerplate deploy button", () => {
    render(<Home />);
    expect(screen.queryByText(/deploy now/i)).not.toBeInTheDocument();
  });
});
