import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
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
];

const mockDocuments = [
  { id: "d1", space_id: "s1", title: "API Reference", language: "en", confidentiality: "internal", tags: [], state: "ingested", current_version_id: "v1", owner_user_id: "u1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  { id: "d2", space_id: "s1", title: "Architecture Overview", language: "en", confidentiality: "internal", tags: [], state: "published", current_version_id: "v2", owner_user_id: "u1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
];

const mockVersion = { id: "v1", document_id: "d1", version_number: 1, content_markdown: "Content here.", frontmatter: {}, approver_user_id: null, approved_at: null, created_from_proposal_id: null, created_at: "2026-01-01T00:00:00Z" };
const mockVersions = [mockVersion];

describe("Document browser page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("populates space dropdown on mount", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    mockApi.get.mockResolvedValue({ spaces: mockSpaces });

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument();
    });
  });

  it("fetches and renders documents when space is selected", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path.includes("/v1/documents")) return Promise.resolve({ documents: mockDocuments });
      return Promise.resolve({});
    });

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "s1" } });

    await waitFor(() => {
      expect(screen.getByText("API Reference")).toBeInTheDocument();
      expect(screen.getByText("Architecture Overview")).toBeInTheDocument();
    });
  });

  it("shows empty state when space has no documents", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path.includes("/v1/documents")) return Promise.resolve({ documents: [] });
      return Promise.resolve({});
    });

    render(<DocumentsPage />);

    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "s1" } });

    await waitFor(() => {
      expect(screen.getByText(/no documents/i)).toBeInTheDocument();
    });
  });
});

describe("Document detail page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mock("next/navigation", () => ({ useParams: () => ({ id: "d1" }) }));
  });

  it("renders document metadata, content, and version history", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1") return Promise.resolve({ document: mockDocuments[0], current_version: mockVersion });
      if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: mockVersions });
      return Promise.resolve({});
    });

    render(<DocumentDetailPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "API Reference" })).toBeInTheDocument();
    });

    expect(screen.getByText(/ingested/i)).toBeInTheDocument();
    expect(screen.getByText(/Content here/)).toBeInTheDocument();
    expect(screen.getByText("Version 1")).toBeInTheDocument();
  });

  it("shows Publish button only for ingested documents", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1") return Promise.resolve({ document: mockDocuments[0], current_version: mockVersion });
      if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: mockVersions });
      return Promise.resolve({});
    });

    render(<DocumentDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("API Reference")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /publish/i })).toBeInTheDocument();
  });

  it("hides Publish button for published documents", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1") return Promise.resolve({ document: mockDocuments[1], current_version: mockVersion });
      if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: mockVersions });
      return Promise.resolve({});
    });

    render(<DocumentDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Architecture Overview")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: /publish/i })).not.toBeInTheDocument();
  });

  it("updates state to published on successful publish", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1") return Promise.resolve({ document: mockDocuments[0], current_version: mockVersion });
      if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: mockVersions });
      return Promise.resolve({});
    });
    mockApi.post.mockResolvedValue({ document: { ...mockDocuments[0], state: "published" }, version: mockVersion });

    render(<DocumentDetailPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /publish/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /publish/i }));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /publish/i })).not.toBeInTheDocument();
    });

    expect(screen.getByText(/published/i)).toBeInTheDocument();
  });
});

// ─── Add Document modal ───────────────────────────────────────────────────────

const newMockDoc = {
  id: "d3", space_id: "s1", title: "New Doc", language: "pt-BR", confidentiality: "internal",
  tags: [], state: "ingested", current_version_id: null, owner_user_id: null,
  created_at: "2026-06-18T00:00:00Z", updated_at: "2026-06-18T00:00:00Z",
};

describe("Add Document modal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path.includes("/v1/documents")) return Promise.resolve({ documents: mockDocuments });
      return Promise.resolve({});
    });
  });

  it("shows Add Document button on the Documents page", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /add document/i })).toBeInTheDocument();
  });

  it("opens modal dialog when Add Document button is clicked", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("calls POST /v1/documents and prepends new document on successful submit", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path.includes("/v1/documents")) return Promise.resolve({ documents: [] });
      return Promise.resolve({});
    });
    mockApi.post.mockResolvedValue({ document: newMockDoc, version: mockVersion });

    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "s1" } });
    await waitFor(() => expect(screen.getByText(/no documents/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "New Doc" } });
    fireEvent.change(screen.getByLabelText(/space/i), { target: { value: "s1" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("New Doc")).toBeInTheDocument();
  });

  it("shows inline error for empty title without submitting", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /add document/i }));

    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(screen.getByText(/title is required/i)).toBeInTheDocument();
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("shows inline error when no space selected without submitting", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /add document/i }));

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "Test" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(screen.getByText(/space is required/i)).toBeInTheDocument();
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("shows API error banner and keeps modal open on submission failure", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    mockApi.post.mockRejectedValue(new Error("Server error"));

    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /add document/i }));

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText(/space/i), { target: { value: "s1" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(screen.getByText(/server error/i)).toBeInTheDocument());
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("closes modal without saving when Cancel is clicked", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("resets form fields when modal is reopened after cancel", async () => {
    const { default: DocumentsPage } = await import("@/app/documents/page");
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "Draft" } });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    expect((screen.getByLabelText(/title/i) as HTMLInputElement).value).toBe("");
  });
});

// ─── Document detail page — Reindex button ────────────────────────────────────
// useParams is hoisted to return { id: "d1" } by the "Document detail page" beforeEach above.
// All reindex tests use id: "d1" API paths to stay consistent with that hoisted mock.

const reindexPublishedOwned = { ...mockDocuments[0], state: "published" as const, owner_user_id: "u1" };
const reindexPublishedNotOwned = { ...mockDocuments[0], state: "published" as const, owner_user_id: "u2" };
const reindexIngested = mockDocuments[0]; // state: "ingested", owner_user_id: "u1"
const reindexArchived = { ...mockDocuments[0], state: "archived" as const, owner_user_id: "u1" };

function setupReindexMock(doc: typeof mockDocuments[0]) {
  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/documents/d1") return Promise.resolve({ document: doc, current_version: mockVersion });
    if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: mockVersions });
    return Promise.resolve({});
  });
}

describe("Document detail page — Reindex button", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows Reindex button for owner of published document", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    setupReindexMock(reindexPublishedOwned);
    render(<DocumentDetailPage />);
    await waitFor(() => expect(screen.getByText("API Reference")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^reindex$/i })).toBeInTheDocument();
  });

  it("shows 'Reindex queued' on success and re-enables button after 3 seconds", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    setupReindexMock(reindexPublishedOwned);
    mockApi.post.mockResolvedValue({ queued: true, document_id: "d1" });
    render(<DocumentDetailPage />);

    // Wait with real timers so waitFor's internal setTimeout works
    await waitFor(() => expect(screen.getByRole("button", { name: /^reindex$/i })).toBeInTheDocument());

    // Enable fake timers only after initial render — now component's setTimeout is fake
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: /^reindex$/i }));

    // Flush the resolved api.post promise and resulting state updates
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText(/reindex queued/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reindexing/i })).toBeDisabled();

    // Advance past the 3-second auto-dismiss timer
    act(() => vi.advanceTimersByTime(3000));

    expect(screen.queryByText(/reindex queued/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^reindex$/i })).toBeEnabled();
  });

  it("shows server error inline on reindex failure and re-enables button", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    setupReindexMock(reindexPublishedOwned);
    mockApi.post.mockRejectedValue(new Error("Indexing service unavailable"));
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("button", { name: /^reindex$/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /^reindex$/i }));

    await waitFor(() => expect(screen.getByText(/indexing service unavailable/i)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^reindex$/i })).toBeEnabled();
  });

  it("disables Reindex button while request is in-flight", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    setupReindexMock(reindexPublishedOwned);
    let resolvePost!: (v: unknown) => void;
    mockApi.post.mockReturnValue(new Promise(res => { resolvePost = res; }));
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("button", { name: /^reindex$/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /^reindex$/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: /reindexing/i })).toBeDisabled());
    resolvePost({ queued: true });
  });

  it("hides Reindex button for non-owner non-admin on published document", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    setupReindexMock(reindexPublishedNotOwned);
    render(<DocumentDetailPage />);
    await waitFor(() => expect(screen.getByText("API Reference")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /reindex/i })).not.toBeInTheDocument();
  });

  it("hides Reindex button for ingested document even when user is owner", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    setupReindexMock(reindexIngested);
    render(<DocumentDetailPage />);
    await waitFor(() => expect(screen.getByText("API Reference")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /reindex/i })).not.toBeInTheDocument();
  });

  it("hides Reindex button for archived document even when user is owner", async () => {
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    setupReindexMock(reindexArchived);
    render(<DocumentDetailPage />);
    await waitFor(() => expect(screen.getByText("API Reference")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /reindex/i })).not.toBeInTheDocument();
  });
});
