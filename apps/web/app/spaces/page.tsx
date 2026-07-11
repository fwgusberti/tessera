"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Space, SpaceAccess } from "@/lib/types";
import { mapSpaceAccesses, topLevelSpaces, isDescendant, type ApiSpaceItem } from "@/lib/spaces";
import { FolderGrid } from "@/components/spaces/FolderGrid";
import { SetParentModal } from "@/components/spaces/SetParentModal";
import { RenameSpaceModal } from "@/components/spaces/RenameSpaceModal";
import { DeleteSpaceModal } from "@/components/spaces/DeleteSpaceModal";
import { AddSpaceModal } from "@/components/spaces/AddSpaceModal";
import { AuthGuard } from "@/lib/auth-guard";
import { useCompany } from "@/lib/company";

export default function SpacesPage() {
  const { activeCompany } = useCompany();
  const isCompanyAdmin = activeCompany?.role === "admin";
  const [accesses, setAccesses] = useState<SpaceAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [managingSpace, setManagingSpace] = useState<Space | null>(null);
  const [renamingSpace, setRenamingSpace] = useState<Space | null>(null);
  const [deletingSpace, setDeletingSpace] = useState<Space | null>(null);
  const [addingSpace, setAddingSpace] = useState(false);

  useEffect(() => {
    api
      .get<{ spaces: ApiSpaceItem[] }>("/v1/spaces")
      .then((data) => {
        const mapped = mapSpaceAccesses(data.spaces ?? []);
        mapped.sort((a, b) => a.space.name.localeCompare(b.space.name));
        setAccesses(mapped);
      })
      .catch((err: Error) => setError(err.message ?? "Failed to load spaces"))
      .finally(() => setLoading(false));
  }, []);

  function handleSpaceUpdated(updated: Space) {
    setAccesses((prev) =>
      prev.map((a) => (a.space.id === updated.id ? { ...a, space: updated } : a))
    );
  }

  function handleSpaceDeleted(deletedId: string) {
    setAccesses((prev) =>
      prev.filter((a) => a.space.id !== deletedId && !isDescendant(prev, deletedId, a.space.id))
    );
  }

  function handleSpaceCreated(created: Space) {
    setAccesses((prev) => [
      ...prev,
      { space: created, effective_role: "admin" as const, is_direct: true },
    ]);
  }

  const roots = topLevelSpaces(accesses);

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Spaces</h1>
          <button
            onClick={() => setAddingSpace(true)}
            className="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700"
          >
            Add Space
          </button>
        </div>
        {loading && <p className="text-sm text-slate-500">Loading spaces…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && roots.length === 0 && (
          // Admins see every company space (058), so an empty list means the
          // company truly has none; members may simply not have been granted access.
          isCompanyAdmin ? (
            <p className="text-sm text-slate-500">No spaces available in your company.</p>
          ) : (
            <p className="text-sm text-slate-500">
              No spaces have been shared with you yet. A company administrator can
              grant you access.
            </p>
          )
        )}
        {!loading && !error && roots.length > 0 && (
          <FolderGrid
            subfolders={roots}
            allAccesses={accesses}
            onReparented={handleSpaceUpdated}
            onSetParent={(space) => setManagingSpace(space)}
            onRename={(space) => setRenamingSpace(space)}
            onDelete={(space) => setDeletingSpace(space)}
          />
        )}
        {managingSpace && (
          <SetParentModal
            space={managingSpace}
            accessibleSpaces={accesses}
            onClose={() => setManagingSpace(null)}
            onUpdated={handleSpaceUpdated}
          />
        )}
        {renamingSpace && (
          <RenameSpaceModal
            space={renamingSpace}
            onClose={() => setRenamingSpace(null)}
            onUpdated={handleSpaceUpdated}
          />
        )}
        {deletingSpace && (
          <DeleteSpaceModal
            space={deletingSpace}
            allAccesses={accesses}
            onClose={() => setDeletingSpace(null)}
            onDeleted={(deletedId) => {
              handleSpaceDeleted(deletedId);
              setDeletingSpace(null);
            }}
          />
        )}
        {addingSpace && (
          <AddSpaceModal
            onClose={() => setAddingSpace(false)}
            onCreated={(created) => {
              handleSpaceCreated(created);
              setAddingSpace(false);
            }}
          />
        )}
      </div>
    </AuthGuard>
  );
}
