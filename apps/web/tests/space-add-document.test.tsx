import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { Document, Space, SpaceRole } from "@/lib/types";

// --- next/navigation mock ---

const mockReplace = vi.fn();
let mockParamsId = "p1";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  usePathname: () => "/spaces",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: mockParamsId }),
}));

// --- auth/company mocks ---

vi.mock("@/lib/company", () => ({
  useCompany: () => ({ activeCompany: { id: "c1", name: "Acme", role: "admin" } }),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// --- api mock ---

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();
  mockParamsId = "p1";
});

// --- fixtures ---

const folderSpace: Space = {
  id: "p1",
  name: "Parent Space",
  slug: "parent",
  sector: "Tech",
  parent_space_id: null,
  default_language: "en",
  confidence_threshold: 0.7,
  retention_policy: {},
};

const otherSpace: Space = {
  id: "s2",
  name: "Other Space",
  slug: "other",
  sector: "Tech",
  parent_space_id: null,
  default_language: "en",
  confidence_threshold: 0.7,
  retention_policy: {},
};

const existingDoc: Document = {
  id: "d1",
  space_id: "p1",
  title: "Existing Doc",
  language: "en",
  confidentiality: "internal",
  tags: [],
  state: "ingested",
  current_version_id: "v1",
  owner_user_id: "u1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockVersion = {
  id: "v9",
  document_id: "d9",
  version_number: 1,
  content_markdown: "",
  frontmatter: {},
  approver_user_id: null,
  approved_at: null,
  created_from_proposal_id: null,
  created_at: "2026-07-11T00:00:00Z",
};

function makeCreatedDoc(overrides: Partial<Document> = {}): Document {
  return {
    id: "d9",
    space_id: "p1",
    title: "New Doc",
    language: "pt-BR",
    confidentiality: "internal",
    tags: [],
    state: "ingested",
    current_version_id: null,
    owner_user_id: null,
    created_at: "2026-07-11T00:00:00Z",
    updated_at: "2026-07-11T00:00:00Z",
    ...overrides,
  } as Document;
}

function mockFolderView({
  role = "editor" as SpaceRole,
  documents = [existingDoc] as Document[],
} = {}) {
  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/spaces") {
      return Promise.resolve({
        spaces: [
          { ...folderSpace, effective_role: role, is_direct: true },
          { ...otherSpace, effective_role: "editor", is_direct: true },
        ],
      });
    }
    if (path === `/v1/spaces/${mockParamsId}/ancestors`) return Promise.resolve({ ancestors: [] });
    if (path.startsWith("/v1/documents")) return Promise.resolve({ documents });
    if (path.endsWith("/members/me")) return Promise.resolve({ membership: { role: "editor" } });
    return Promise.reject(Object.assign(new Error("Not found"), { status: 404 }));
  });
}

async function renderFolderPage() {
  const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
  render(<SpaceFolderPage />);
  await waitFor(() =>
    expect(screen.getByRole("heading", { name: "Parent Space" })).toBeInTheDocument()
  );
}

function countDocumentListFetches() {
  return mockApi.get.mock.calls.filter((call: unknown[]) =>
    String(call[0]).startsWith("/v1/documents")
  ).length;
}

// ─── US1 — create a document from within a space ─────────────────────────────

describe("Space page — Add Document button (US1)", () => {
  it("renders an Add Document button next to Add Space for an editor", async () => {
    mockFolderView({ role: "editor" });
    await renderFolderPage();

    expect(screen.getByRole("button", { name: /add document/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add space/i })).toBeInTheDocument();
  });

  it("opens the dialog with the current space preselected as destination", async () => {
    mockFolderView({ role: "editor" });
    await renderFolderPage();

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    const select = screen.getByLabelText(/^space$/i) as HTMLSelectElement;
    expect(select.value).toBe("p1");
  });

  it("creates a document in the current space and appends it to the grid without reload", async () => {
    mockFolderView({ role: "editor" });
    mockApi.post.mockResolvedValue({ document: makeCreatedDoc(), version: mockVersion });
    await renderFolderPage();
    const initialDocFetches = countDocumentListFetches();

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "New Doc" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() =>
      expect(mockApi.post).toHaveBeenCalledWith(
        "/v1/documents",
        expect.objectContaining({ space_id: "p1", title: "New Doc" })
      )
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("New Doc")).toBeInTheDocument();
    expect(countDocumentListFetches()).toBe(initialDocFetches); // no refetch, no reload
  });

  it("replaces the empty state with the grid when creating from an empty space", async () => {
    mockFolderView({ role: "editor", documents: [] });
    mockApi.post.mockResolvedValue({ document: makeCreatedDoc(), version: mockVersion });
    await renderFolderPage();

    expect(screen.getByText(/no sub-folders or documents/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "New Doc" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => expect(screen.getByText("New Doc")).toBeInTheDocument());
    expect(screen.queryByText(/no sub-folders or documents/i)).not.toBeInTheDocument();
  });

  it("creates nothing and leaves the page unchanged on cancel", async () => {
    mockFolderView({ role: "editor" });
    await renderFolderPage();

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "Abandoned" } });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mockApi.post).not.toHaveBeenCalled();
    expect(screen.queryByText("Abandoned")).not.toBeInTheDocument();
    expect(screen.getByText("Existing Doc")).toBeInTheDocument();
  });

  it("shows validation and creates nothing when title is missing", async () => {
    mockFolderView({ role: "editor" });
    await renderFolderPage();

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    expect(screen.getByText(/title is required/i)).toBeInTheDocument();
    expect(mockApi.post).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("does not add the document to the grid when the destination is changed to another space", async () => {
    mockFolderView({ role: "editor" });
    mockApi.post.mockResolvedValue({
      document: makeCreatedDoc({ id: "d10", space_id: "s2", title: "Cross Doc" }),
      version: mockVersion,
    });
    await renderFolderPage();

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "Cross Doc" } });
    fireEvent.change(screen.getByLabelText(/^space$/i), { target: { value: "s2" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() =>
      expect(mockApi.post).toHaveBeenCalledWith(
        "/v1/documents",
        expect.objectContaining({ space_id: "s2", title: "Cross Doc" })
      )
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.queryByText("Cross Doc")).not.toBeInTheDocument();
  });
});

// ─── US2 — permission-aware visibility ────────────────────────────────────────

describe("Space page — Add Document permission gating (US2)", () => {
  it("hides the Add Document button from a viewer", async () => {
    mockFolderView({ role: "viewer" });
    await renderFolderPage();

    expect(screen.queryByRole("button", { name: /add document/i })).not.toBeInTheDocument();
  });

  it("shows the Add Document button to an editor", async () => {
    mockFolderView({ role: "editor" });
    await renderFolderPage();

    expect(screen.getByRole("button", { name: /add document/i })).toBeInTheDocument();
  });

  it("shows the Add Document button to an admin", async () => {
    mockFolderView({ role: "admin" });
    await renderFolderPage();

    expect(screen.getByRole("button", { name: /add document/i })).toBeInTheDocument();
  });

  it("keeps the dialog open with content preserved when the server rejects the save (stale page)", async () => {
    mockFolderView({ role: "editor" });
    mockApi.post.mockRejectedValue(
      Object.assign(new Error("You do not have permission to create documents in this space"), {
        status: 403,
      })
    );
    await renderFolderPage();

    fireEvent.click(screen.getByRole("button", { name: /add document/i }));
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: "Stale Doc" } });
    fireEvent.change(screen.getByLabelText(/content/i), { target: { value: "Draft body" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() =>
      expect(screen.getByText(/do not have permission/i)).toBeInTheDocument()
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect((screen.getByLabelText(/title/i) as HTMLInputElement).value).toBe("Stale Doc");
    expect((screen.getByLabelText(/content/i) as HTMLTextAreaElement).value).toBe("Draft body");
    expect(screen.queryByText("Stale Doc")).not.toBeInTheDocument(); // no grid tile added
  });
});
