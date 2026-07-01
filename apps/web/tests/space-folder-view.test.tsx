import { render, screen, waitFor, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

let mockParamsId = "p1";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: mockParamsId }),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "t@t.com", isAdmin: false }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn() },
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as { get: ReturnType<typeof vi.fn> };

// --- Fixtures: rootSpace (r1) > parentSpace (p1) > childSpace (c1) > grandchildSpace (g1) ---

const rootSpace = {
  id: "r1", slug: "root", name: "Root Space", sector: "Tech",
  parent_space_id: null, default_language: "en", confidence_threshold: 0.7, retention_policy: {},
  effective_role: "admin", is_direct: true,
};

const parentSpace = {
  id: "p1", slug: "parent", name: "Parent Space", sector: "Tech",
  parent_space_id: "r1", default_language: "en", confidence_threshold: 0.7, retention_policy: {},
  effective_role: "admin", is_direct: true,
};

const childSpace = {
  id: "c1", slug: "child", name: "Child Space", sector: "Tech",
  parent_space_id: "p1", default_language: "en", confidence_threshold: 0.7, retention_policy: {},
  effective_role: "editor", is_direct: false,
};

const grandchildSpace = {
  id: "g1", slug: "grandchild", name: "Grandchild Space", sector: "Tech",
  parent_space_id: "c1", default_language: "en", confidence_threshold: 0.7, retention_policy: {},
  effective_role: "editor", is_direct: false,
};

const allSpaces = [rootSpace, parentSpace, childSpace, grandchildSpace];

function mockSpacesAndAncestors(
  ancestors: { id: string; name: string; slug: string }[],
  documents: Record<string, unknown>[] = []
) {
  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/spaces") return Promise.resolve({ spaces: allSpaces });
    if (path === `/v1/spaces/${mockParamsId}/ancestors`) return Promise.resolve({ ancestors });
    if (path.startsWith("/v1/documents")) return Promise.resolve({ documents });
    return Promise.reject(Object.assign(new Error("Not found"), { status: 404 }));
  });
}

function makeDoc(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "d1",
    space_id: "p1",
    title: "Doc One",
    language: "en",
    confidentiality: "internal",
    tags: [],
    state: "published",
    current_version_id: "v1",
    owner_user_id: "u1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockParamsId = "p1";
});

describe("SpaceFolderPage — drill-down and mixed contents", () => {
  it("shows only the opened folder's direct sub-folders, not deeper descendants", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors([{ id: "r1", name: "Root Space", slug: "root" }]);

    render(<SpaceFolderPage />);

    await waitFor(() => {
      const tiles = screen.getAllByRole("article");
      expect(tiles.length).toBe(1);
      expect(tiles[0]).toHaveTextContent("Child Space");
    });
    expect(screen.queryByText("Grandchild Space")).not.toBeInTheDocument();
  });

  it("loading /spaces/{id} directly renders that folder's view with the correct breadcrumb (deep link)", async () => {
    mockParamsId = "c1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors([
      { id: "r1", name: "Root Space", slug: "root" },
      { id: "p1", name: "Parent Space", slug: "parent" },
    ]);

    render(<SpaceFolderPage />);

    await waitFor(() => {
      const tiles = screen.getAllByRole("article");
      expect(tiles.length).toBe(1);
      expect(tiles[0]).toHaveTextContent("Grandchild Space");
    });

    const breadcrumb = screen.getByRole("navigation", { name: /breadcrumb/i });
    expect(within(breadcrumb).getByText("Root Space")).toBeInTheDocument();
    expect(within(breadcrumb).getByText("Parent Space")).toBeInTheDocument();
    expect(within(breadcrumb).getByText("Child Space")).toBeInTheDocument();
  });
});

describe("SpaceFolderPage — breadcrumb", () => {
  it("reads 'Root › {folder name}' when opening a top-level folder with no ancestors", async () => {
    mockParamsId = "r1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors([]);

    render(<SpaceFolderPage />);

    const breadcrumb = await screen.findByRole("navigation", { name: /breadcrumb/i });
    expect(within(breadcrumb).getByText("Root")).toBeInTheDocument();
    expect(within(breadcrumb).getByText("Root Space")).toBeInTheDocument();
  });

  it("renders 'Root' and each ancestor as a clickable link, with the current folder as plain text", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors([{ id: "r1", name: "Root Space", slug: "root" }]);

    render(<SpaceFolderPage />);

    const breadcrumb = await screen.findByRole("navigation", { name: /breadcrumb/i });
    const rootLink = within(breadcrumb).getByRole("link", { name: "Root" });
    expect(rootLink).toHaveAttribute("href", "/spaces");

    const ancestorLink = within(breadcrumb).getByRole("link", { name: "Root Space" });
    expect(ancestorLink).toHaveAttribute("href", "/spaces/r1");

    expect(within(breadcrumb).queryByRole("link", { name: "Parent Space" })).not.toBeInTheDocument();
    expect(within(breadcrumb).getByText("Parent Space")).toBeInTheDocument();
  });

  it("clicking the 'Root' breadcrumb segment links back to the top-level grid", async () => {
    mockParamsId = "c1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors([
      { id: "r1", name: "Root Space", slug: "root" },
      { id: "p1", name: "Parent Space", slug: "parent" },
    ]);

    render(<SpaceFolderPage />);

    const breadcrumb = await screen.findByRole("navigation", { name: /breadcrumb/i });
    expect(within(breadcrumb).getByRole("link", { name: "Root" })).toHaveAttribute("href", "/spaces");
    expect(within(breadcrumb).getByRole("link", { name: "Root Space" })).toHaveAttribute("href", "/spaces/r1");
  });
});

describe("SpaceFolderPage — mixed sub-folder and document contents", () => {
  it("renders sub-folders and documents together when a folder has both", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors(
      [{ id: "r1", name: "Root Space", slug: "root" }],
      [makeDoc({ id: "d1", space_id: "p1", title: "Doc One" })]
    );

    render(<SpaceFolderPage />);

    await waitFor(() => {
      expect(screen.getByText("Child Space")).toBeInTheDocument();
      expect(screen.getByText("Doc One")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /child space/i })).toHaveAttribute("href", "/spaces/c1");
    expect(screen.getByRole("link", { name: /doc one/i })).toHaveAttribute("href", "/documents/d1");
  });

  it("renders only sub-folders when the folder has sub-folders but no documents", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors([{ id: "r1", name: "Root Space", slug: "root" }], []);

    render(<SpaceFolderPage />);

    await waitFor(() => expect(screen.getByText("Child Space")).toBeInTheDocument());
    expect(screen.queryByRole("link", { name: /doc one/i })).not.toBeInTheDocument();
  });

  it("renders only documents when the folder has documents but no sub-folders", async () => {
    mockParamsId = "g1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors(
      [
        { id: "r1", name: "Root Space", slug: "root" },
        { id: "p1", name: "Parent Space", slug: "parent" },
        { id: "c1", name: "Child Space", slug: "child" },
      ],
      [makeDoc({ id: "d2", space_id: "g1", title: "Leaf Doc" })]
    );

    render(<SpaceFolderPage />);

    await waitFor(() => expect(screen.getByText("Leaf Doc")).toBeInTheDocument());
    expect(screen.queryByRole("article")).not.toBeNull(); // the document tile itself
    expect(screen.getAllByRole("article").length).toBe(1);
  });

  it("shows an empty-state message when the folder has neither sub-folders nor documents", async () => {
    mockParamsId = "g1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors(
      [
        { id: "r1", name: "Root Space", slug: "root" },
        { id: "p1", name: "Parent Space", slug: "parent" },
        { id: "c1", name: "Child Space", slug: "child" },
      ],
      []
    );

    render(<SpaceFolderPage />);

    await waitFor(() => expect(screen.getByText(/no.*(contents|items|sub-folders|documents)/i)).toBeInTheDocument());
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("clicking a document tile links to /documents/{id}", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockSpacesAndAncestors(
      [{ id: "r1", name: "Root Space", slug: "root" }],
      [makeDoc({ id: "d3", space_id: "p1", title: "Clickable Doc" })]
    );

    render(<SpaceFolderPage />);

    const link = await screen.findByRole("link", { name: /clickable doc/i });
    expect(link).toHaveAttribute("href", "/documents/d3");
  });
});
