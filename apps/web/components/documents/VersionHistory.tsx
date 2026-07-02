"use client";

import type { DocumentVersion } from "@/lib/types";

interface VersionHistoryProps {
  versions: DocumentVersion[];
}

export function VersionHistory({ versions }: VersionHistoryProps) {
  if (versions.length === 0) {
    return (
      <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-slate-400">
        No versions found.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {versions.map((v) => (
        <div
          key={v.id}
          className="bg-white rounded border border-slate-200 p-4 flex items-center justify-between gap-4"
        >
          <div>
            <p className="text-sm font-medium text-slate-900">Version {v.version_number}</p>
            <p className="text-xs text-slate-500 font-mono">{v.approver_user_id ?? "—"}</p>
          </div>
          <p className="text-xs text-slate-500">
            {v.approved_at ? new Date(v.approved_at).toLocaleString() : "—"}
          </p>
        </div>
      ))}
    </div>
  );
}
