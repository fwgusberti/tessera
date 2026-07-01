"use client";

import { useState } from "react";
import type { Document, Space, SpaceAccess } from "@/lib/types";
import { reparentSpace } from "@/lib/spaces";
import { FolderTile } from "@/components/spaces/FolderTile";
import { DocumentTile } from "@/components/spaces/DocumentTile";

interface FolderGridProps {
  subfolders: SpaceAccess[];
  documents?: Document[];
  allAccesses?: SpaceAccess[];
  onReparented?: (updated: Space) => void;
  onSetParent?: (space: Space) => void;
}

export function FolderGrid({
  subfolders,
  documents = [],
  allAccesses = [],
  onReparented,
  onSetParent,
}: FolderGridProps) {
  const [dragError, setDragError] = useState<string | null>(null);

  async function handleDropOnTile(draggedId: string, targetId: string) {
    const result = await reparentSpace(draggedId, targetId, allAccesses);
    if (result.ok) {
      setDragError(null);
      onReparented?.(result.space);
    } else {
      setDragError(result.error);
    }
  }

  return (
    <div className="space-y-3">
      {dragError && (
        <p role="alert" className="text-sm text-red-600">
          {dragError}
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {subfolders.map((access) => (
          <FolderTile
            key={access.space.id}
            access={access}
            onDropSpace={(draggedId) => handleDropOnTile(draggedId, access.space.id)}
            onSetParent={onSetParent ? () => onSetParent(access.space) : undefined}
          />
        ))}
        {documents.map((document) => (
          <DocumentTile key={document.id} document={document} />
        ))}
      </div>
    </div>
  );
}
