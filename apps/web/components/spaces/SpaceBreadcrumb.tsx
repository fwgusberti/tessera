"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Ancestor {
  id: string;
  name: string;
  slug: string;
}

interface SpaceBreadcrumbProps {
  spaceId: string;
}

export function SpaceBreadcrumb({ spaceId }: SpaceBreadcrumbProps) {
  const [ancestors, setAncestors] = useState<Ancestor[]>([]);

  useEffect(() => {
    api
      .get<{ ancestors: Ancestor[] }>(`/v1/spaces/${spaceId}/ancestors`)
      .then((data) => setAncestors(data.ancestors ?? []))
      .catch(() => setAncestors([]));
  }, [spaceId]);

  if (ancestors.length === 0) return null;

  return (
    <p className="text-xs text-slate-400 mt-1">
      {ancestors.map((a, i) => (
        <span key={a.id}>
          {a.name}
          {i < ancestors.length - 1 ? " › " : " ›"}
        </span>
      ))}
    </p>
  );
}
