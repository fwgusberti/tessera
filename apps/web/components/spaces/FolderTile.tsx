"use client";

import type { DragEvent } from "react";
import type { SpaceAccess } from "@/lib/types";
import { RoleBadge } from "@/components/members/RoleBadge";

const SPACE_ID_MIME = "text/plain";

interface FolderTileProps {
  access: SpaceAccess;
  onDropSpace?: (draggedSpaceId: string) => void;
  onSetParent?: () => void;
}

export function FolderTile({ access, onDropSpace, onSetParent }: FolderTileProps) {
  const { space, effective_role } = access;
  const isAdmin = effective_role === "admin";

  function handleDragStart(e: DragEvent<HTMLElement>) {
    e.dataTransfer.setData(SPACE_ID_MIME, space.id);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDragOver(e: DragEvent<HTMLElement>) {
    e.preventDefault();
  }

  function handleDrop(e: DragEvent<HTMLElement>) {
    e.preventDefault();
    const draggedId = e.dataTransfer.getData(SPACE_ID_MIME);
    if (draggedId) onDropSpace?.(draggedId);
  }

  return (
    <article
      draggable={isAdmin}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className="bg-white rounded border border-slate-200 p-4 hover:border-indigo-300 hover:shadow-sm transition"
    >
      <div className="flex items-start justify-between gap-2">
        <a href={`/spaces/${space.id}`} className="min-w-0 flex-1 flex items-start gap-2 group">
          <svg
            className="w-8 h-8 text-indigo-400 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
          </svg>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-slate-900 truncate group-hover:text-indigo-600">
              {space.name}
            </h2>
            <p className="text-sm text-slate-500 mt-1">{space.sector}</p>
          </div>
        </a>
        <div className="flex items-center gap-2 flex-shrink-0">
          <RoleBadge role={effective_role} />
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
      </div>
    </article>
  );
}
