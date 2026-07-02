"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Space, SpaceAccess } from "@/lib/types";
import { mapSpaceAccesses, topLevelSpaces, type ApiSpaceItem } from "@/lib/spaces";
import { FolderGrid } from "@/components/spaces/FolderGrid";
import { SetParentModal } from "@/components/spaces/SetParentModal";
import { RenameSpaceModal } from "@/components/spaces/RenameSpaceModal";
import { AuthGuard } from "@/lib/auth-guard";

export default function SpacesPage() {
  const [accesses, setAccesses] = useState<SpaceAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [managingSpace, setManagingSpace] = useState<Space | null>(null);
  const [renamingSpace, setRenamingSpace] = useState<Space | null>(null);

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

  const roots = topLevelSpaces(accesses);

  return (
    <AuthGuard>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Spaces</h1>
        {loading && <p className="text-sm text-slate-500">Loading spaces…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && roots.length === 0 && (
          <p className="text-sm text-slate-500">No spaces available in your company.</p>
        )}
        {!loading && !error && roots.length > 0 && (
          <FolderGrid
            subfolders={roots}
            allAccesses={accesses}
            onReparented={handleSpaceUpdated}
            onSetParent={(space) => setManagingSpace(space)}
            onRename={(space) => setRenamingSpace(space)}
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
      </div>
    </AuthGuard>
  );
}
