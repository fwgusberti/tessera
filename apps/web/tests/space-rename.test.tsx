import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { Space, SpaceAccess, SpaceRole } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  api: { patch: vi.fn() },
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as {
  patch: ReturnType<typeof vi.fn>;
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

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FolderTile — Rename control visibility", () => {
  it("shows a Rename control on an admin's folder tile", async () => {
    const { FolderTile } = await import("@/components/spaces/FolderTile");
    const admin = makeAccess("a1", "Alpha", null, "admin");

    render(<FolderTile access={admin} onRename={vi.fn()} />);

    expect(screen.getByRole("button", { name: /rename/i })).toBeInTheDocument();
  });

  it("does not show a Rename control on a non-admin's folder tile", async () => {
    const { FolderTile } = await import("@/components/spaces/FolderTile");
    const viewer = makeAccess("v1", "Viewer Space", null, "viewer");

    render(<FolderTile access={viewer} onRename={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /rename/i })).not.toBeInTheDocument();
  });

  it("does not show a Rename control on an editor's folder tile", async () => {
    const { FolderTile } = await import("@/components/spaces/FolderTile");
    const editor = makeAccess("e1", "Editor Space", null, "editor");

    render(<FolderTile access={editor} onRename={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /rename/i })).not.toBeInTheDocument();
  });
});

describe("RenameSpaceModal", () => {
  const space: Space = {
    id: "s1",
    slug: "s1",
    name: "Original Name",
    sector: "Tech",
    parent_space_id: null,
    default_language: "en",
    confidence_threshold: 0.7,
    retention_policy: {},
  };

  it("pre-fills the current name and calls PATCH .../name on save", async () => {
    const { RenameSpaceModal } = await import("@/components/spaces/RenameSpaceModal");
    mockApi.patch.mockResolvedValue({ space: { ...space, name: "New Name" } });
    const onUpdated = vi.fn();
    const onClose = vi.fn();

    render(<RenameSpaceModal space={space} onClose={onClose} onUpdated={onUpdated} />);

    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("Original Name");

    fireEvent.change(input, { target: { value: "New Name" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(mockApi.patch).toHaveBeenCalledWith("/v1/spaces/s1/name", { name: "New Name" })
    );
    await waitFor(() =>
      expect(onUpdated).toHaveBeenCalledWith(expect.objectContaining({ name: "New Name" }))
    );
  });

  it("rejects an empty name without calling the API", async () => {
    const { RenameSpaceModal } = await import("@/components/spaces/RenameSpaceModal");
    const onUpdated = vi.fn();
    const onClose = vi.fn();

    render(<RenameSpaceModal space={space} onClose={onClose} onUpdated={onUpdated} />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(mockApi.patch).not.toHaveBeenCalled();
    expect(onUpdated).not.toHaveBeenCalled();
  });

  it("does nothing on Cancel", async () => {
    const { RenameSpaceModal } = await import("@/components/spaces/RenameSpaceModal");
    const onUpdated = vi.fn();
    const onClose = vi.fn();

    render(<RenameSpaceModal space={space} onClose={onClose} onUpdated={onUpdated} />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Changed But Cancelled" } });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(mockApi.patch).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("shows an error and keeps the modal open when save fails, allowing retry", async () => {
    const { RenameSpaceModal } = await import("@/components/spaces/RenameSpaceModal");
    mockApi.patch.mockRejectedValueOnce(new Error("Server error — please try again."));
    const onUpdated = vi.fn();
    const onClose = vi.fn();

    render(<RenameSpaceModal space={space} onClose={onClose} onUpdated={onUpdated} />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Retried Name" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/server error/i)
    );
    expect(onUpdated).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();

    mockApi.patch.mockResolvedValueOnce({ space: { ...space, name: "Retried Name" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(onUpdated).toHaveBeenCalledWith(expect.objectContaining({ name: "Retried Name" }))
    );
  });
});
