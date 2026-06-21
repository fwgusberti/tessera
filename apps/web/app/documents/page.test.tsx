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
  useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "t@t.com", isAdmin: false }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

const mockSpaces = [
  { id: "s1", slug: "eng", name: "Engineering", sector: "Tech", default_language: "en", confidence_threshold: 0.7, retention_policy: {} },
  { id: "s2", slug: "hr", name: "HR", sector: "People", default_language: "en", confidence_threshold: 0.7, retention_policy: {} },
];

const s1Docs = [
  { id: "d1", space_id: "s1", title: "Eng Doc", language: "en", confidentiality: "internal", tags: [], state: "published", current_version_id: "v1", owner_user_id: "u1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
];

const allDocs = [
  ...s1Docs,
  { id: "d2", space_id: "s2", title: "HR Doc", language: "en", confidentiality: "internal", tags: [], state: "published", current_version_id: "v2", owner_user_id: "u1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
];

describe("DocumentsPage — US2: space-scoped filtering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  it("selecting a space calls the API with space_id and shows only that space's documents", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");

    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path === "/v1/documents") return Promise.resolve({ documents: allDocs });
      if (path === "/v1/documents?space_id=s1") return Promise.resolve({ documents: s1Docs });
      return Promise.resolve({ documents: [] });
    });

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "s1" } });

    await waitFor(() => {
      expect(screen.getByText("Eng Doc")).toBeInTheDocument();
    });

    const docCalls = (mockApi.get as ReturnType<typeof vi.fn>).mock.calls
      .map((c: string[]) => c[0])
      .filter((url: string) => url.includes("/v1/documents"));
    expect(docCalls).toContain("/v1/documents?space_id=s1");
    expect(screen.queryByText("HR Doc")).not.toBeInTheDocument();
  });

  it("clearing the space selector calls the API without space_id and restores cross-space docs", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");

    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path === "/v1/documents") return Promise.resolve({ documents: allDocs });
      if (path === "/v1/documents?space_id=s1") return Promise.resolve({ documents: s1Docs });
      return Promise.resolve({ documents: [] });
    });

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument();
    });

    // Select a space
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "s1" } });
    await waitFor(() => {
      expect(screen.getByText("Eng Doc")).toBeInTheDocument();
    });

    // Clear the selector by selecting the empty "Select a space..." option
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "" } });

    await waitFor(() => {
      expect(screen.getByText("HR Doc")).toBeInTheDocument();
    });

    const docCalls = (mockApi.get as ReturnType<typeof vi.fn>).mock.calls
      .map((c: string[]) => c[0])
      .filter((url: string) => url.startsWith("/v1/documents"));
    const unfiltered = docCalls.filter((url: string) => !url.includes("space_id"));
    expect(unfiltered.length).toBeGreaterThanOrEqual(2);
  });
});
