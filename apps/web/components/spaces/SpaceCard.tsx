"use client";

import type { Space, SpaceRole } from "@/lib/types";
import { RoleBadge } from "@/components/members/RoleBadge";
import { SpaceBreadcrumb } from "@/components/spaces/SpaceBreadcrumb";

interface SpaceCardProps {
  space: Space;
  role: SpaceRole | null;
  depth?: number;
  visibleParentIds?: Set<string>;
  isAdmin?: boolean;
  onSetParent?: () => void;
}

export function SpaceCard({
  space,
  role,
  depth = 0,
  visibleParentIds,
  isAdmin = false,
  onSetParent,
}: SpaceCardProps) {
  const showBreadcrumb =
    !!space.parent_space_id &&
    visibleParentIds !== undefined &&
    !visibleParentIds.has(space.parent_space_id);

  return (
    <article
      className="bg-white rounded border border-slate-200 p-4"
      style={{ marginLeft: depth > 0 ? `${depth * 1.5}rem` : undefined }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-slate-900 truncate">{space.name}</h2>
          <p className="text-sm text-slate-500 mt-1">{space.sector}</p>
          {showBreadcrumb && <SpaceBreadcrumb spaceId={space.id} />}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {role && <RoleBadge role={role} />}
          {isAdmin && onSetParent && (
            <button
              onClick={onSetParent}
              className="text-xs text-slate-400 hover:text-indigo-600 underline"
            >
              Set parent
            </button>
          )}
        </div>
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
