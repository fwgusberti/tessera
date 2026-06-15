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
];

const mockDocuments = [
  { id: "d1", space_id: "s1", title: "API Reference", language: "en", confidentiality: "internal", tags: [], state: "ingested", current_version_id: "v1", owner_user_id: "u1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  { id: "d2", space_id: "s1", title: "Architecture Overview", language: "en", confidentiality: "internal", tags: [], state: "published", current_version_id: "v2", owner_user_id: "u1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
];

const mockVersion = { id: "v1", document_id: "d1", version_number: 1, content_markdown: "# API Reference\n\nContent here.", frontmatter: {}, approver_user_id: null, approved_at: null, created_from_proposal_id: null, created_at: "2026-01-01T00:00:00Z" };
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
    expect(screen.getByText("1")).toBeInTheDocument();
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
