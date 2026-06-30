"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Space, SpaceAccess } from "@/lib/types";

interface SetParentModalProps {
  space: Space;
  accessibleSpaces: SpaceAccess[];
  onClose: () => void;
  onUpdated: (updated: Space) => void;
}

export function SetParentModal({
  space,
  accessibleSpaces,
  onClose,
  onUpdated,
}: SetParentModalProps) {
  const [selectedParentId, setSelectedParentId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const candidates = accessibleSpaces
    .map((a) => a.space)
    .filter((s) => s.id !== space.id);

  async function handleSetParent() {
    if (!selectedParentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.patch<{ space: Space }>(
        `/v1/spaces/${space.id}/parent`,
        { parent_space_id: selectedParentId }
      );
      onUpdated(data.space);
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to set parent — check for cycles or permission issues.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleRemoveParent() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.delete<{ space: Space }>(
        `/v1/spaces/${space.id}/parent`
      );
      onUpdated(data.space);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to remove parent.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Set Parent for &ldquo;{space.name}&rdquo;
        </h2>

        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Parent Space
          </label>
          <select
            value={selectedParentId}
            onChange={(e) => setSelectedParentId(e.target.value)}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          >
            <option value="">— select a parent —</option>
            {candidates.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

        <div className="flex items-center justify-between gap-2">
          {space.parent_space_id && (
            <button
              onClick={handleRemoveParent}
              disabled={loading}
              className="text-sm text-slate-500 hover:text-slate-700 underline disabled:opacity-50"
            >
              Remove parent
            </button>
          )}
          <div className="flex gap-2 ml-auto">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSetParent}
              disabled={loading || !selectedParentId}
              className="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? "Saving…" : "Set Parent"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
