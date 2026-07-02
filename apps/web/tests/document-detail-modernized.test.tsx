import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
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
    user: { id: "u1", email: "owner@t.com", isAdmin: false },
    accessToken: "tok",
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "d1" }), useRouter: () => ({ push: vi.fn() }) }));

import { api } from "@/lib/api";

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

// ─── Fixtures ──────────────────────────────────────────────────────────────

const markdownWithFormatting = [
  "# Heading",
  "",
  "- First item",
  "- Second item",
  "",
  "```",
  "const x = 1;",
  "```",
].join("\n");

const nestedSpaceDocument = {
  id: "d1",
  space_id: "s2",
  title: "Onboarding Guide",
  language: "en",
  confidentiality: "internal" as const,
  tags: ["backend", "api", "urgent"],
  state: "ingested" as const,
  current_version_id: "v3",
  owner_user_id: "u1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const currentVersion = {
  id: "v3",
  document_id: "d1",
  version_number: 3,
  content_markdown: markdownWithFormatting,
  frontmatter: {},
  approver_user_id: "u2",
  approved_at: "2026-02-01T10:00:00Z",
  created_from_proposal_id: null,
  created_at: "2026-02-01T10:00:00Z",
};

const threeVersions = [
  {
    id: "v1",
    document_id: "d1",
    version_number: 1,
    content_markdown: "v1 content",
    frontmatter: {},
    approver_user_id: "u2",
    approved_at: "2026-01-05T09:00:00Z",
    created_from_proposal_id: null,
    created_at: "2026-01-05T09:00:00Z",
  },
  {
    id: "v2",
    document_id: "d1",
    version_number: 2,
    content_markdown: "v2 content",
    frontmatter: {},
    approver_user_id: "u2",
    approved_at: "2026-01-15T09:00:00Z",
    created_from_proposal_id: null,
    created_at: "2026-01-15T09:00:00Z",
  },
  currentVersion,
];

const zeroVersions: typeof threeVersions = [];

const ancestorsResponse = {
  ancestors: [{ id: "s1", name: "Engineering", slug: "engineering" }],
};

const ownSpaceResponse = {
  space: {
    id: "s2",
    slug: "backend",
    name: "Backend",
    sector: "engineering",
    parent_space_id: "s1",
    default_language: "en",
    confidence_threshold: 0.8,
    retention_policy: {},
  },
};

// ─── Shared mock setup ─────────────────────────────────────────────────────

interface MockOverrides {
  document?: typeof nestedSpaceDocument;
  currentVersionData?: typeof currentVersion | null;
  versions?: typeof threeVersions;
  ancestorsOk?: boolean;
  spaceOk?: boolean;
}

function setupApiMocks(overrides: MockOverrides = {}) {
  const {
    document = nestedSpaceDocument,
    currentVersionData = currentVersion,
    versions = threeVersions,
    ancestorsOk = true,
    spaceOk = true,
  } = overrides;

  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/documents/d1") {
      return Promise.resolve({ document, current_version: currentVersionData });
    }
    if (path === "/v1/documents/d1/versions") {
      return Promise.resolve({ versions });
    }
    if (path === `/v1/spaces/${document.space_id}/ancestors`) {
      return ancestorsOk ? Promise.resolve(ancestorsResponse) : Promise.reject(new Error("Not found"));
    }
    if (path === `/v1/spaces/${document.space_id}`) {
      return spaceOk ? Promise.resolve(ownSpaceResponse) : Promise.reject(new Error("Not found"));
    }
    return Promise.resolve({});
  });
}

describe("Document detail page (modernized)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── User Story 1: modern layout, formatted content, breadcrumb ──────────

  it("renders the current version's markdown as distinct formatted elements, not raw source", async () => {
    setupApiMocks();
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    const { container } = render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("Onboarding Guide")).toBeInTheDocument());

    expect(screen.getByRole("heading", { name: "Heading" })).toBeInTheDocument();

    const listItems = screen.getAllByRole("listitem");
    expect(listItems.some((li) => li.textContent === "First item")).toBe(true);
    expect(listItems.some((li) => li.textContent === "Second item")).toBe(true);

    const codeBlock = container.querySelector("pre code");
    expect(codeBlock).not.toBeNull();
    expect(codeBlock?.textContent).toContain("const x = 1;");

    // Raw markdown syntax must not leak into the rendered text
    expect(screen.queryByText("# Heading")).not.toBeInTheDocument();
    expect(screen.queryByText("- First item")).not.toBeInTheDocument();
  });

  it("renders a full breadcrumb trail for a document in a nested space", async () => {
    setupApiMocks();
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("Onboarding Guide")).toBeInTheDocument());

    const nav = screen.getByRole("navigation", { name: /breadcrumb/i });
    expect(within(nav).getByRole("link", { name: "Root" })).toHaveAttribute("href", "/spaces");
    expect(within(nav).getByRole("link", { name: "Engineering" })).toHaveAttribute("href", "/spaces/s1");
    expect(within(nav).getByRole("link", { name: "Backend" })).toHaveAttribute("href", "/spaces/s2");
    expect(within(nav).getByText("Onboarding Guide")).toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: "Onboarding Guide" })).not.toBeInTheDocument();
  });

  it("falls back to a plain Documents link when the space/ancestors lookups reject", async () => {
    setupApiMocks({ ancestorsOk: false, spaceOk: false });
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("Onboarding Guide")).toBeInTheDocument());

    expect(screen.queryByRole("navigation", { name: /breadcrumb/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /documents/i })).toHaveAttribute("href", "/documents");

    // The rest of the page still renders
    expect(screen.getByRole("button", { name: /publish/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Heading" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /version history/i })).toBeInTheDocument();
  });

  it("falls back to a plain Documents link when the space/ancestors responses are malformed", async () => {
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1") {
        return Promise.resolve({ document: nestedSpaceDocument, current_version: currentVersion });
      }
      if (path === "/v1/documents/d1/versions") {
        return Promise.resolve({ versions: threeVersions });
      }
      if (path === "/v1/spaces/s2/ancestors") {
        return Promise.resolve({}); // missing `ancestors`
      }
      if (path === "/v1/spaces/s2") {
        return Promise.resolve({}); // missing `space`
      }
      return Promise.resolve({});
    });
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("Onboarding Guide")).toBeInTheDocument());

    expect(screen.queryByRole("navigation", { name: /breadcrumb/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /documents/i })).toHaveAttribute("href", "/documents");
  });

  it("renders each tag as an individual pill instead of a joined string", async () => {
    setupApiMocks();
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("Onboarding Guide")).toBeInTheDocument());

    expect(screen.getByText("backend")).toBeInTheDocument();
    expect(screen.getByText("api")).toBeInTheDocument();
    expect(screen.getByText("urgent")).toBeInTheDocument();
    expect(screen.queryByText("backend, api, urgent")).not.toBeInTheDocument();
  });

  // ─── User Story 2: restyled actions, parity of behavior ──────────────────

  it("shows a loading state on Publish, then reflects the published state on success", async () => {
    setupApiMocks();
    const publishedDocument = { ...nestedSpaceDocument, state: "published" as const };
    mockApi.post.mockResolvedValue({ document: publishedDocument, version: currentVersion });

    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("button", { name: /^publish$/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^publish$/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: /publishing/i })).toBeDisabled());

    await waitFor(() => expect(screen.queryByRole("button", { name: /^publish$/i })).not.toBeInTheDocument());
    expect(screen.getByText(/published/i)).toBeInTheDocument();
  });

  it("shows a clearly styled inline error when Publish fails, without breaking the rest of the page", async () => {
    setupApiMocks();
    mockApi.post.mockRejectedValue(new Error("Failed to publish document"));

    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByRole("button", { name: /^publish$/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /^publish$/i }));

    const errorMessage = await screen.findByText("Failed to publish document");
    expect(errorMessage).toBeInTheDocument();

    // Rest of the page is unaffected
    expect(screen.getByRole("heading", { name: "Heading" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /version history/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^publish$/i })).toBeEnabled();
  });

  // ─── User Story 3: scannable version history ──────────────────────────────

  it("renders each version's number, approval date/time, and approver as a scannable list with no table", async () => {
    setupApiMocks({ versions: threeVersions });
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    const { container } = render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("Onboarding Guide")).toBeInTheDocument());

    expect(container.querySelector("table")).toBeNull();

    for (const v of threeVersions) {
      expect(screen.getByText(`Version ${v.version_number}`)).toBeInTheDocument();
    }
    expect(screen.getAllByText("u2")).toHaveLength(3);
    expect(
      screen.getByText(new Date(currentVersion.approved_at as string).toLocaleString())
    ).toBeInTheDocument();
  });

  it("renders a styled empty state when there are no versions", async () => {
    setupApiMocks({ versions: zeroVersions });
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    const { container } = render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("Onboarding Guide")).toBeInTheDocument());

    expect(container.querySelector("table")).toBeNull();
    expect(screen.getByText(/no versions/i)).toBeInTheDocument();
  });
});
