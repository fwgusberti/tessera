"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Space, SpaceRole, SpaceWithRole } from "@/lib/types";
import { SpaceCard } from "@/components/spaces/SpaceCard";
import { AuthGuard } from "@/lib/auth-guard";

export default function SpacesPage() {
  const [items, setItems] = useState<SpaceWithRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<{ spaces: Space[] }>("/v1/spaces")
      .then(async (data) => {
        const spaces = data.spaces ?? [];
        const roleResults = await Promise.allSettled(
          spaces.map((space) =>
            api
              .get<{ membership: { role: SpaceRole } }>(`/v1/spaces/${space.id}/members/me`)
              .then((res) => res.membership.role as SpaceRole)
              .catch((): SpaceRole | null => null)
          )
        );
        const withRoles: SpaceWithRole[] = spaces.map((space, i) => ({
          space,
          role: roleResults[i].status === "fulfilled" ? (roleResults[i] as PromiseFulfilledResult<SpaceRole | null>).value : null,
        }));
        withRoles.sort((a, b) => a.space.name.localeCompare(b.space.name));
        setItems(withRoles);
      })
      .catch((err: Error) => setError(err.message ?? "Failed to load spaces"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AuthGuard>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Spaces</h1>
        {loading && <p className="text-sm text-slate-500">Loading spaces…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className="text-sm text-slate-500">No spaces available in your company.</p>
        )}
        {!loading && !error && items.length > 0 && (
          <div className="grid gap-4">
            {items.map(({ space, role }) => (
              <SpaceCard key={space.id} space={space} role={role} />
            ))}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
