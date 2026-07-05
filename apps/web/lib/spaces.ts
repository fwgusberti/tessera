import { api } from "@/lib/api";
import type { Space, SpaceAccess, SpaceRole } from "@/lib/types";

export interface ApiSpaceItem {
  id: string;
  slug: string;
  name: string;
  sector: string;
  parent_space_id: string | null;
  default_language: string;
  confidence_threshold: number;
  retention_policy: Record<string, unknown>;
  effective_role: SpaceRole;
  is_direct: boolean;
}

export function mapSpaceAccesses(items: ApiSpaceItem[]): SpaceAccess[] {
  return items.map((item) => ({
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
}

export function topLevelSpaces(accesses: SpaceAccess[]): SpaceAccess[] {
  const accessibleIds = new Set(accesses.map((a) => a.space.id));
  return accesses.filter((a) => {
    const parentId = a.space.parent_space_id;
    return !parentId || !accessibleIds.has(parentId);
  });
}

export function directChildren(accesses: SpaceAccess[], parentId: string): SpaceAccess[] {
  return accesses.filter((a) => a.space.parent_space_id === parentId);
}

export function isDescendant(
  accesses: SpaceAccess[],
  ancestorId: string,
  candidateId: string
): boolean {
  const byId = new Map(accesses.map((a) => [a.space.id, a]));
  const seen = new Set<string>();
  let current = byId.get(candidateId);
  while (current?.space.parent_space_id) {
    if (seen.has(current.space.id)) return false;
    seen.add(current.space.id);
    if (current.space.parent_space_id === ancestorId) return true;
    current = byId.get(current.space.parent_space_id);
  }
  return false;
}

export type ReparentResult = { ok: true; space: Space } | { ok: false; error: string };

export async function reparentSpace(
  draggedId: string,
  targetId: string | null,
  accesses: SpaceAccess[]
): Promise<ReparentResult> {
  if (draggedId === targetId) {
    return { ok: false, error: "A folder cannot be moved into itself." };
  }
  if (targetId && isDescendant(accesses, draggedId, targetId)) {
    return { ok: false, error: "A folder cannot be moved into one of its own sub-folders." };
  }
  try {
    const data = targetId
      ? await api.patch<{ space: Space }>(`/v1/spaces/${draggedId}/parent`, { parent_space_id: targetId })
      : await api.delete<{ space: Space }>(`/v1/spaces/${draggedId}/parent`);
    return { ok: true, space: data.space };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to move folder.";
    return { ok: false, error: message };
  }
}
