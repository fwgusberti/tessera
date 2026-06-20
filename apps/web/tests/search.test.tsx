import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", email: "t@t.com", isAdmin: false },
    accessToken: "tok",
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as { post: ReturnType<typeof vi.fn> };

import SearchPage from "../app/search/page";

describe("SearchPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("does not show 'No results found' before any search is submitted", () => {
    render(<SearchPage />);
    expect(screen.queryByText(/no results found/i)).toBeNull();
  });

  it("shows 'No results found' message after a search returns an empty results array", async () => {
    mockApi.post.mockResolvedValueOnce({ results: [] });

    render(<SearchPage />);

    const input = screen.getByPlaceholderText(/search documentation/i);
    fireEvent.change(input, { target: { value: "nomatch" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(screen.getByText(/no results found/i)).toBeTruthy();
    });
  });
});
