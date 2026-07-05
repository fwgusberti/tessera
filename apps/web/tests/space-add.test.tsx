import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { Space } from "@/lib/types";

// --- next/navigation mock (usePathname returns /spaces so AuthGuard redirects there) ---

const mockReplace = vi.fn();
let mockParamsId = "p1";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  usePathname: () => "/spaces",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: mockParamsId }),
}));

// --- useAuth mock ---

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

function mockFolderView() {
  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/spaces") return Promise.resolve({ spaces: [{ ...folderSpace, effective_role: "admin", is_direct: true }] });
    if (path === `/v1/spaces/${mockParamsId}/ancestors`) return Promise.resolve({ ancestors: [] });
    if (path.startsWith("/v1/documents")) return Promise.resolve({ documents: [] });
    return Promise.reject(Object.assign(new Error("Not found"), { status: 404 }));
  });
}

describe("AddSpaceModal — top-level Spaces page", () => {
  it("shows an Add Space button on the Spaces page", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockResolvedValue({ spaces: [] });

    render(<SpacesPage />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /add space/i })).toBeInTheDocument()
    );
  });

  it("does nothing on Cancel", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockResolvedValue({ spaces: [] });

    render(<SpacesPage />);
    await waitFor(() => screen.getByRole("button", { name: /add space/i }));
    fireEvent.click(screen.getByRole("button", { name: /add space/i }));

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Marketing" } });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(mockApi.post).not.toHaveBeenCalled();
    expect(screen.queryByText("Marketing")).not.toBeInTheDocument();
  });

  it("rejects an empty name without calling the API", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockResolvedValue({ spaces: [] });

    render(<SpacesPage />);
    await waitFor(() => screen.getByRole("button", { name: /add space/i }));
    fireEvent.click(screen.getByRole("button", { name: /add space/i }));

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("creates a top-level space and shows it immediately without a reload", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockResolvedValue({ spaces: [] });
    const created: Space = {
      id: "new-1",
      name: "Marketing",
      slug: "marketing",
      sector: "General",
      parent_space_id: null,
      default_language: "pt-BR",
      confidence_threshold: 0.7,
      retention_policy: {},
    };
    mockApi.post.mockResolvedValue({ space: created });

    render(<SpacesPage />);
    await waitFor(() => screen.getByRole("button", { name: /add space/i }));
    fireEvent.click(screen.getByRole("button", { name: /add space/i }));

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Marketing" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() =>
      expect(mockApi.post).toHaveBeenCalledWith("/v1/spaces", { name: "Marketing" })
    );
    await waitFor(() => expect(screen.getByText("Marketing")).toBeInTheDocument());
    expect(mockApi.get).toHaveBeenCalledTimes(1);
  });

  it("shows an error, adds no tile, and allows retry when creation fails", async () => {
    const { default: SpacesPage } = await import("@/app/spaces/page");
    mockApi.get.mockResolvedValue({ spaces: [] });
    mockApi.post.mockRejectedValueOnce(new Error("Server error — please try again."));

    render(<SpacesPage />);
    await waitFor(() => screen.getByRole("button", { name: /add space/i }));
    fireEvent.click(screen.getByRole("button", { name: /add space/i }));

    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Marketing" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/server error/i)
    );
    expect(screen.queryByText("Marketing")).not.toBeInTheDocument();
    expect(input.value).toBe("Marketing");

    const created: Space = {
      id: "new-3",
      name: "Marketing",
      slug: "marketing",
      sector: "General",
      parent_space_id: null,
      default_language: "pt-BR",
      confidence_threshold: 0.7,
      retention_policy: {},
    };
    mockApi.post.mockResolvedValueOnce({ space: created });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => expect(screen.getByText("Marketing")).toBeInTheDocument());
  });
});

describe("AddSpaceModal — folder view", () => {
  it("shows an Add Space button in a space's folder view", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockFolderView();

    render(<SpaceFolderPage />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /add space/i })).toBeInTheDocument()
    );
  });

  it("creates a sub-space nested under the folder being viewed", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockFolderView();
    const created: Space = {
      id: "new-2",
      name: "Q3 Campaigns",
      slug: "q3-campaigns",
      sector: "General",
      parent_space_id: "p1",
      default_language: "pt-BR",
      confidence_threshold: 0.7,
      retention_policy: {},
    };
    mockApi.post.mockResolvedValue({ space: created });

    render(<SpaceFolderPage />);
    await waitFor(() => screen.getByRole("button", { name: /add space/i }));
    fireEvent.click(screen.getByRole("button", { name: /add space/i }));

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Q3 Campaigns" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() =>
      expect(mockApi.post).toHaveBeenCalledWith("/v1/spaces", {
        name: "Q3 Campaigns",
        parent_space_id: "p1",
      })
    );
    await waitFor(() => expect(screen.getByText("Q3 Campaigns")).toBeInTheDocument());
  });

  it("shows a 403 error from a folder view without creating a nested tile", async () => {
    mockParamsId = "p1";
    const { default: SpaceFolderPage } = await import("@/app/spaces/[id]/page");
    mockFolderView();
    mockApi.post.mockRejectedValueOnce(new Error("Access denied"));

    render(<SpaceFolderPage />);
    await waitFor(() => screen.getByRole("button", { name: /add space/i }));
    fireEvent.click(screen.getByRole("button", { name: /add space/i }));

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Should Fail" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/access denied/i)
    );
    expect(screen.queryByText("Should Fail")).not.toBeInTheDocument();
  });
});
