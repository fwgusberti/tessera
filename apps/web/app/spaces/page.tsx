"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Space, SpaceAccess } from "@/lib/types";
import { SpaceHierarchyView } from "@/components/spaces/SpaceHierarchyView";
import { SetParentModal } from "@/components/spaces/SetParentModal";
import { AuthGuard } from "@/lib/auth-guard";

interface ApiSpaceItem {
  id: string;
  slug: string;
  name: string;
  sector: string;
  parent_space_id: string | null;
  default_language: string;
  confidence_threshold: number;
  retention_policy: Record<string, unknown>;
  effective_role: "admin" | "editor" | "viewer";
  is_direct: boolean;
}

export default function SpacesPage() {
  const [accesses, setAccesses] = useState<SpaceAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [managingSpace, setManagingSpace] = useState<Space | null>(null);

  useEffect(() => {
    api
      .get<{ spaces: ApiSpaceItem[] }>("/v1/spaces")
      .then((data) => {
        const items = data.spaces ?? [];
        const mapped: SpaceAccess[] = items.map((item) => ({
          space: {
            id: item.id,
            slug: item.slug,
            name: item.name,
            sector: item.sector,
            parent_space_id: item.parent_space_id,
            default_language: item.default_language,
            confidence_threshold: item.confidence_threshold,
            retention_policy: item.retention_policy,
          },
          effective_role: item.effective_role,
          is_direct: item.is_direct,
        }));
        mapped.sort((a, b) => a.space.name.localeCompare(b.space.name));
        setAccesses(mapped);
      })
      .catch((err: Error) => setError(err.message ?? "Failed to load spaces"))
      .finally(() => setLoading(false));
  }, []);

  function handleSpaceUpdated(updated: Space) {
    setAccesses((prev) =>
      prev.map((a) =>
        a.space.id === updated.id ? { ...a, space: updated } : a
      )
    );
  }

  return (
    <AuthGuard>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Spaces</h1>
        {loading && <p className="text-sm text-slate-500">Loading spaces…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && accesses.length === 0 && (
          <p className="text-sm text-slate-500">No spaces available in your company.</p>
        )}
        {!loading && !error && accesses.length > 0 && (
          <SpaceHierarchyView
            spaces={accesses}
            onSetParent={(space) => setManagingSpace(space)}
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
      </div>
    </AuthGuard>
  );
}
