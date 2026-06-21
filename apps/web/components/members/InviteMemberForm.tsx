"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Role = "admin" | "editor" | "viewer";

interface InviteMemberFormProps {
  spaceId: string;
  onSuccess: () => void;
}

export function InviteMemberForm({ spaceId, onSuccess }: InviteMemberFormProps) {
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim()) return;
    setError(null);
    setLoading(true);
    try {
      await api.post(`/v1/spaces/${spaceId}/members`, { user_id: userId.trim(), role });
      setUserId("");
      setRole("viewer");
      onSuccess();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to invite member";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 p-4 border border-slate-200 rounded-lg bg-slate-50">
      <h3 className="text-sm font-semibold text-slate-700">Invite Member</h3>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          className="flex-1 px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          disabled={loading}
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
          className="px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          disabled={loading}
        >
          <option value="viewer">Viewer</option>
          <option value="editor">Editor</option>
          <option value="admin">Admin</option>
        </select>
        <button
          type="submit"
          disabled={loading || !userId.trim()}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
        >
          {loading ? "Inviting…" : "Invite"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </form>
  );
}
