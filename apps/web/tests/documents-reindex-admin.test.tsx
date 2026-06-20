import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: { id: "u99", email: "admin@t.com", isAdmin: true }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "d1" }) }));

import { api } from "@/lib/api";

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

const mockVersion = {
  id: "v1", document_id: "d1", version_number: 1, content_markdown: "# Doc\n\nContent.",
  frontmatter: {}, approver_user_id: null, approved_at: null,
  created_from_proposal_id: null, created_at: "2026-01-01T00:00:00Z",
};

// Published document owned by u1 — admin is u99 (different user)
const publishedDocNotOwnedByAdmin = {
  id: "d1", space_id: "s1", title: "Admin Test Doc", language: "en",
  confidentiality: "internal" as const, tags: [], state: "published" as const,
  current_version_id: "v1", owner_user_id: "u1",
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
};

describe("Document detail page — Reindex button (admin)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1") return Promise.resolve({ document: publishedDocNotOwnedByAdmin, current_version: mockVersion });
      if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: [mockVersion] });
      return Promise.resolve({});
    });
  });

  it("shows Reindex button for admin on published document not owned by admin", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);
    await waitFor(() => expect(screen.getByText("Admin Test Doc")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^reindex$/i })).toBeInTheDocument();
  });
});
