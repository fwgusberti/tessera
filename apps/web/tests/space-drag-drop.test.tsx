import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { Space, SpaceAccess, SpaceRole } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  api: { patch: vi.fn(), delete: vi.fn() },
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as {
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

function makeAccess(
  id: string,
  name: string,
  parentId: string | null,
  role: SpaceRole = "admin"
): SpaceAccess {
  const space: Space = {
    id,
    slug: id,
    name,
    sector: "Tech",
    parent_space_id: parentId,
    default_language: "en",
    confidence_threshold: 0.7,
    retention_policy: {},
  };
  return { space, effective_role: role, is_direct: true };
}

function makeDataTransfer() {
  const store: Record<string, string> = {};
  return {
    setData: (key: string, value: string) => {
      store[key] = value;
    },
    getData: (key: string) => store[key] ?? "",
    effectAllowed: "",
    dropEffect: "",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FolderGrid — drag-and-drop reparenting", () => {
  it("dragging a folder tile onto another calls PATCH /v1/spaces/{id}/parent with the target id and updates the view", async () => {
    const { FolderGrid } = await import("@/components/spaces/FolderGrid");
    const alpha = makeAccess("a1", "Alpha", null, "admin");
    const beta = makeAccess("b1", "Beta", null, "admin");
    const accesses = [alpha, beta];
    mockApi.patch.mockResolvedValue({ space: { ...alpha.space, parent_space_id: "b1" } });

    const onReparented = vi.fn();
    render(<FolderGrid subfolders={accesses} allAccesses={accesses} onReparented={onReparented} />);

    const tiles = screen.getAllByRole("article");
    const dt = makeDataTransfer();
    fireEvent.dragStart(tiles[0], { dataTransfer: dt });
    fireEvent.dragOver(tiles[1], { dataTransfer: dt });
    fireEvent.drop(tiles[1], { dataTransfer: dt });

    await waitFor(() =>
      expect(mockApi.patch).toHaveBeenCalledWith("/v1/spaces/a1/parent", { parent_space_id: "b1" })
    );
    await waitFor(() =>
      expect(onReparented).toHaveBeenCalledWith(expect.objectContaining({ id: "a1", parent_space_id: "b1" }))
    );
  });

  it("rejects dropping a folder onto itself with a clear message and no API call", async () => {
    const { FolderGrid } = await import("@/components/spaces/FolderGrid");
    const alpha = makeAccess("a1", "Alpha", null, "admin");
    const accesses = [alpha];
    const onReparented = vi.fn();

    render(<FolderGrid subfolders={accesses} allAccesses={accesses} onReparented={onReparented} />);

    const tile = screen.getByRole("article");
    const dt = makeDataTransfer();
    fireEvent.dragStart(tile, { dataTransfer: dt });
    fireEvent.dragOver(tile, { dataTransfer: dt });
    fireEvent.drop(tile, { dataTransfer: dt });

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(mockApi.patch).not.toHaveBeenCalled();
    expect(mockApi.delete).not.toHaveBeenCalled();
    expect(onReparented).not.toHaveBeenCalled();
  });

  it("rejects dropping a folder onto one of its own descendants with a clear message and no API call", async () => {
    const { FolderGrid } = await import("@/components/spaces/FolderGrid");
    const parent = makeAccess("par1", "Parent", null, "admin");
    const child = makeAccess("chi1", "Child", "par1", "admin");
    const accesses = [parent, child];
    const onReparented = vi.fn();

    render(<FolderGrid subfolders={accesses} allAccesses={accesses} onReparented={onReparented} />);

    const tiles = screen.getAllByRole("article");
    const parentTile = tiles.find((t) => t.textContent?.includes("Parent"))!;
    const childTile = tiles.find((t) => t.textContent?.includes("Child"))!;

    const dt = makeDataTransfer();
    fireEvent.dragStart(parentTile, { dataTransfer: dt });
    fireEvent.dragOver(childTile, { dataTransfer: dt });
    fireEvent.drop(childTile, { dataTransfer: dt });

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(mockApi.patch).not.toHaveBeenCalled();
    expect(onReparented).not.toHaveBeenCalled();
  });

  it("does not make a non-admin's folder tile draggable (drag not available without permission)", async () => {
    const { FolderGrid } = await import("@/components/spaces/FolderGrid");
    const viewerSpace = makeAccess("v1", "Viewer Space", null, "viewer");

    render(<FolderGrid subfolders={[viewerSpace]} allAccesses={[viewerSpace]} />);

    const tile = screen.getByRole("article");
    expect(tile).toHaveAttribute("draggable", "false");
  });

  it("shows a permission message and makes no hierarchy change when the server rejects the drop as forbidden", async () => {
    const { FolderGrid } = await import("@/components/spaces/FolderGrid");
    const alpha = makeAccess("a1", "Alpha", null, "admin");
    const beta = makeAccess("b1", "Beta", null, "admin");
    const accesses = [alpha, beta];
    mockApi.patch.mockRejectedValue(new Error("Forbidden — admin role required on both spaces."));
    const onReparented = vi.fn();

    render(<FolderGrid subfolders={accesses} allAccesses={accesses} onReparented={onReparented} />);

    const tiles = screen.getAllByRole("article");
    const dt = makeDataTransfer();
    fireEvent.dragStart(tiles[0], { dataTransfer: dt });
    fireEvent.dragOver(tiles[1], { dataTransfer: dt });
    fireEvent.drop(tiles[1], { dataTransfer: dt });

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/forbidden/i));
    expect(onReparented).not.toHaveBeenCalled();
  });
});

describe("FolderGrid — non-drag Set Parent fallback", () => {
  it("keeps the Set Parent trigger present and functional on an admin's folder tile, independent of drag", async () => {
    const { FolderGrid } = await import("@/components/spaces/FolderGrid");
    const alpha = makeAccess("a1", "Alpha", null, "admin");
    const onSetParent = vi.fn();

    render(<FolderGrid subfolders={[alpha]} onSetParent={onSetParent} />);

    const button = screen.getByRole("button", { name: /set parent/i });
    fireEvent.click(button);
    expect(onSetParent).toHaveBeenCalledWith(alpha.space);
  });

  it("does not show a Set Parent trigger for a non-admin's folder tile", async () => {
    const { FolderGrid } = await import("@/components/spaces/FolderGrid");
    const viewerSpace = makeAccess("v1", "Viewer Space", null, "viewer");
    const onSetParent = vi.fn();

    render(<FolderGrid subfolders={[viewerSpace]} onSetParent={onSetParent} />);

    expect(screen.queryByRole("button", { name: /set parent/i })).not.toBeInTheDocument();
  });
});

describe("SpaceBreadcrumb — drag-and-drop drop targets", () => {
  it("dropping a folder tile onto the Root crumb calls DELETE /v1/spaces/{id}/parent", async () => {
    const { SpaceBreadcrumb } = await import("@/components/spaces/SpaceBreadcrumb");
    const accesses = [makeAccess("a1", "Alpha", "p1", "admin")];
    mockApi.delete.mockResolvedValue({ space: { ...accesses[0].space, parent_space_id: null } });
    const onReparented = vi.fn();

    render(
      <SpaceBreadcrumb
        ancestors={[{ id: "p1", name: "Parent", slug: "parent" }]}
        currentName="Current Folder"
        allAccesses={accesses}
        onReparented={onReparented}
      />
    );

    const rootCrumb = screen.getByRole("link", { name: "Root" });
    const dt = makeDataTransfer();
    dt.setData("text/plain", "a1");
    fireEvent.dragOver(rootCrumb, { dataTransfer: dt });
    fireEvent.drop(rootCrumb, { dataTransfer: dt });

    await waitFor(() => expect(mockApi.delete).toHaveBeenCalledWith("/v1/spaces/a1/parent"));
    await waitFor(() =>
      expect(onReparented).toHaveBeenCalledWith(expect.objectContaining({ id: "a1", parent_space_id: null }))
    );
  });

  it("dropping a folder tile onto an ancestor crumb calls PATCH /v1/spaces/{id}/parent with that ancestor's id", async () => {
    const { SpaceBreadcrumb } = await import("@/components/spaces/SpaceBreadcrumb");
    const accesses = [makeAccess("a1", "Alpha", "p1", "admin")];
    mockApi.patch.mockResolvedValue({ space: { ...accesses[0].space, parent_space_id: "r1" } });
    const onReparented = vi.fn();

    render(
      <SpaceBreadcrumb
        ancestors={[{ id: "r1", name: "Root Space", slug: "root" }]}
        currentName="Current Folder"
        allAccesses={accesses}
        onReparented={onReparented}
      />
    );

    const ancestorCrumb = screen.getByRole("link", { name: "Root Space" });
    const dt = makeDataTransfer();
    dt.setData("text/plain", "a1");
    fireEvent.dragOver(ancestorCrumb, { dataTransfer: dt });
    fireEvent.drop(ancestorCrumb, { dataTransfer: dt });

    await waitFor(() =>
      expect(mockApi.patch).toHaveBeenCalledWith("/v1/spaces/a1/parent", { parent_space_id: "r1" })
    );
  });
});
