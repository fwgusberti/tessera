"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Space } from "@/lib/types";

interface RenameSpaceModalProps {
  space: Space;
  onClose: () => void;
  onUpdated: (updated: Space) => void;
}

export function RenameSpaceModal({ space, onClose, onUpdated }: RenameSpaceModalProps) {
  const [name, setName] = useState(space.name);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Name cannot be empty.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.patch<{ space: Space }>(`/v1/spaces/${space.id}/name`, {
        name: trimmed,
      });
      onUpdated(data.space);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to rename space.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Rename &ldquo;{space.name}&rdquo;
        </h2>

        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">Space Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-600 mb-3">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
