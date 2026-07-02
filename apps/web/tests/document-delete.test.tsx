import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

let mockUser: { id: string; email: string; isAdmin: boolean } = {
  id: "u1",
  email: "owner@t.com",
  isAdmin: false,
};

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: mockUser, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "d1" }),
  useRouter: () => ({ push: mockPush }),
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

const mockVersion = {
  id: "v1", document_id: "d1", version_number: 1, content_markdown: "# Doc\n\nContent.",
  frontmatter: {}, approver_user_id: null, approved_at: null,
  created_from_proposal_id: null, created_at: "2026-01-01T00:00:00Z",
};

// Document owned by u1
const ownedDoc = {
  id: "d1", space_id: "s1", title: "Deletable Doc", language: "en",
  confidentiality: "internal" as const, tags: [], state: "published" as const,
  current_version_id: "v1", owner_user_id: "u1",
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
};

function setupDocumentMocks(membershipResponse: { membership: { role: string } } | null = null) {
  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/documents/d1") return Promise.resolve({ document: ownedDoc, current_version: mockVersion });
    if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: [mockVersion] });
    if (path === "/v1/spaces/s1/ancestors") return Promise.resolve({ ancestors: [] });
    if (path === "/v1/spaces/s1") {
      return Promise.resolve({
        space: {
          id: "s1", slug: "ops", name: "Ops", sector: "operations",
          parent_space_id: null, default_language: "en", confidence_threshold: 0.8, retention_policy: {},
        },
      });
    }
    if (path === "/v1/spaces/s1/members/me") {
      if (membershipResponse) return Promise.resolve(membershipResponse);
      return Promise.reject(new Error("not a member"));
    }
    return Promise.resolve({});
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUser = { id: "u1", email: "owner@t.com", isAdmin: false };
});

describe("Document detail page — Delete button", () => {
  it("shows a Delete button for the document owner", async () => {
    mockUser = { id: "u1", email: "owner@t.com", isAdmin: false };
    setupDocumentMocks();
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Deletable Doc" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("does not show a Delete button for a non-owner without admin rights", async () => {
    mockUser = { id: "u2", email: "editor@t.com", isAdmin: false };
    setupDocumentMocks({ membership: { role: "editor" } });
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Deletable Doc" })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
  });

  it("does not call the delete API when the confirm dialog is cancelled", async () => {
    mockUser = { id: "u1", email: "owner@t.com", isAdmin: false };
    setupDocumentMocks();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Deletable Doc" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /delete/i }));

    expect(mockApi.delete).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Deletable Doc" })).toBeInTheDocument();
  });

  it("shows a Delete button for a space admin who does not own the document", async () => {
    mockUser = { id: "u2", email: "admin@t.com", isAdmin: false };
    setupDocumentMocks({ membership: { role: "admin" } });
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Deletable Doc" })).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument());
  });

  it("shows a Delete button for a platform admin who does not own the document", async () => {
    mockUser = { id: "u2", email: "platform-admin@t.com", isAdmin: true };
    setupDocumentMocks({ membership: { role: "viewer" } });
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Deletable Doc" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("allows deleting after a previously cancelled confirmation", async () => {
    mockUser = { id: "u1", email: "owner@t.com", isAdmin: false };
    setupDocumentMocks();
    mockApi.delete.mockResolvedValue({ deleted: true, document_id: "d1" });
    const confirmSpy = vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true);
    vi.spyOn(window, "confirm").mockImplementation(confirmSpy);
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Deletable Doc" })).toBeInTheDocument());
    const deleteButton = screen.getByRole("button", { name: /delete/i });

    fireEvent.click(deleteButton);
    expect(mockApi.delete).not.toHaveBeenCalled();

    fireEvent.click(deleteButton);
    await waitFor(() => expect(mockApi.delete).toHaveBeenCalledTimes(1));
    expect(mockApi.delete).toHaveBeenCalledWith("/v1/documents/d1");
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/spaces/s1"));
  });
});
