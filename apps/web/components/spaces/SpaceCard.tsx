"use client";

import type { Space, SpaceRole } from "@/lib/types";
import { RoleBadge } from "@/components/members/RoleBadge";

interface SpaceCardProps {
  space: Space;
  role: SpaceRole | null;
}

export function SpaceCard({ space, role }: SpaceCardProps) {
  return (
    <article className="bg-white rounded border border-slate-200 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-slate-900 truncate">{space.name}</h2>
          <p className="text-sm text-slate-500 mt-1">{space.sector}</p>
        </div>
        {role && (
          <div className="flex-shrink-0">
            <RoleBadge role={role} />
          </div>
        )}
      </div>
      <div className="flex items-center gap-3 mt-3">
        <a
          href={`/spaces/${space.id}/members`}
          className="text-xs text-indigo-600 hover:text-indigo-700 hover:underline"
        >
          Members
        </a>
        <a
          href={`/documents?space=${space.id}`}
          className="text-xs text-indigo-600 hover:text-indigo-700 hover:underline"
        >
          Documents
        </a>
      </div>
    </article>
  );
}
