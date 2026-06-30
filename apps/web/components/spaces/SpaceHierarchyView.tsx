"use client";

import type { Space, SpaceAccess } from "@/lib/types";
import { SpaceCard } from "@/components/spaces/SpaceCard";

interface SpaceHierarchyViewProps {
  spaces: SpaceAccess[];
  onSetParent?: (space: Space) => void;
}

interface TreeNode {
  access: SpaceAccess;
  children: TreeNode[];
  depth: number;
}

function buildTree(spaces: SpaceAccess[]): { roots: TreeNode[]; visibleIds: Set<string> } {
  const byId = new Map(spaces.map((a) => [a.space.id, a]));
  const visibleIds = new Set(spaces.map((a) => a.space.id));
  const nodes = new Map<string, TreeNode>(
    spaces.map((a) => [a.space.id, { access: a, children: [], depth: 0 }])
  );
  const roots: TreeNode[] = [];

  for (const [, node] of nodes) {
    const parentId = node.access.space.parent_space_id;
    if (parentId && byId.has(parentId)) {
      const parentNode = nodes.get(parentId)!;
      node.depth = parentNode.depth + 1;
      parentNode.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return { roots, visibleIds };
}

function renderNodes(
  nodes: TreeNode[],
  visibleParentIds: Set<string>,
  onSetParent?: (space: Space) => void
): React.ReactNode {
  return nodes.map((node) => (
    <div key={node.access.space.id}>
      <SpaceCard
        space={node.access.space}
        role={node.access.effective_role}
        depth={node.depth}
        visibleParentIds={visibleParentIds}
        isAdmin={node.access.effective_role === "admin"}
        onSetParent={onSetParent ? () => onSetParent(node.access.space) : undefined}
      />
      {node.children.length > 0 && (
        <div className="mt-2 space-y-2">
          {renderNodes(node.children, visibleParentIds, onSetParent)}
        </div>
      )}
    </div>
  ));
}

export function SpaceHierarchyView({ spaces, onSetParent }: SpaceHierarchyViewProps) {
  const { roots, visibleIds } = buildTree(spaces);
  return <div className="space-y-2">{renderNodes(roots, visibleIds, onSetParent)}</div>;
}
