"use client";

import { useState } from "react";
import type { DragEvent } from "react";
import type { Ancestor, Space, SpaceAccess } from "@/lib/types";
import { reparentSpace } from "@/lib/spaces";

const SPACE_ID_MIME = "text/plain";

interface SpaceBreadcrumbProps {
  ancestors: Ancestor[];
  currentName: string;
  allAccesses?: SpaceAccess[];
  onReparented?: (updated: Space) => void;
}

export function SpaceBreadcrumb({
  ancestors,
  currentName,
  allAccesses = [],
  onReparented,
}: SpaceBreadcrumbProps) {
  const [dragError, setDragError] = useState<string | null>(null);

  function handleDragOver(e: DragEvent<HTMLAnchorElement>) {
    e.preventDefault();
  }

  async function handleDrop(targetId: string | null, e: DragEvent<HTMLAnchorElement>) {
    e.preventDefault();
    const draggedId = e.dataTransfer.getData(SPACE_ID_MIME);
    if (!draggedId) return;
    const result = await reparentSpace(draggedId, targetId, allAccesses);
    if (result.ok) {
      setDragError(null);
      onReparented?.(result.space);
    } else {
      setDragError(result.error);
    }
  }

  return (
    <nav aria-label="breadcrumb" className="text-sm text-slate-500 flex items-center flex-wrap gap-1">
      {dragError && (
        <p role="alert" className="w-full text-red-600">
          {dragError}
        </p>
      )}
      <a
        href="/spaces"
        className="text-indigo-600 hover:underline"
        onDragOver={handleDragOver}
        onDrop={(e) => handleDrop(null, e)}
      >
        Root
      </a>
      {ancestors.map((a) => (
        <span key={a.id} className="flex items-center gap-1">
          <span aria-hidden="true">›</span>
          <a
            href={`/spaces/${a.id}`}
            className="text-indigo-600 hover:underline"
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(a.id, e)}
          >
            {a.name}
          </a>
        </span>
      ))}
      <span className="flex items-center gap-1">
        <span aria-hidden="true">›</span>
        <span className="text-slate-700 font-medium">{currentName}</span>
      </span>
    </nav>
  );
}
