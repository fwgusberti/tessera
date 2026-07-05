"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Space, SpaceAccess } from "@/lib/types";
import { isDescendant } from "@/lib/spaces";

interface DeleteSpaceModalProps {
  space: Space;
  allAccesses: SpaceAccess[];
  onClose: () => void;
  onDeleted: (deletedSpaceId: string) => void;
}

export function DeleteSpaceModal({ space, allAccesses, onClose, onDeleted }: DeleteSpaceModalProps) {
  const [step, setStep] = useState<"confirm" | "password">("confirm");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const childCount = allAccesses.filter(
    (a) => a.space.id !== space.id && isDescendant(allAccesses, space.id, a.space.id)
  ).length;

  async function handleDelete() {
    setLoading(true);
    setError(null);
    try {
      await api.delete<{ deleted: boolean; space_id: string }>(`/v1/spaces/${space.id}`, {
        password,
      });
      onDeleted(space.id);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete space.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40"
    >
      <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Delete &ldquo;{space.name}&rdquo;?
        </h2>

        {step === "confirm" ? (
          <>
            <p className="text-sm text-slate-700 mb-4">
              This will permanently delete &ldquo;{space.name}&rdquo;
              {childCount > 0 ? ` and its ${childCount} sub-space(s)` : ""}, along with all documents
              inside them. This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm text-slate-700 border border-slate-300 rounded hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={() => setStep("password")}
                className="px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700"
              >
                Continue
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Confirm your password
                <input
                  type="password"
                  aria-label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-red-600"
                />
              </label>
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
                onClick={handleDelete}
                disabled={loading}
                className="px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
              >
                {loading ? "Deleting…" : "Delete"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
