"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { RoleBadge } from "./RoleBadge";
import { AddMemberForm } from "./AddMemberForm";

type Role = "admin" | "editor" | "viewer";

interface Member {
  id: string;
  space_id: string;
  user_id: string;
  display_name?: string;
  email?: string;
  role: Role;
  invited_by_user_id: string | null;
  created_at: string;
}

interface SpaceMembersPanelProps {
  spaceId: string;
  myRole: Role | null;
}

export function SpaceMembersPanel({ spaceId, myRole }: SpaceMembersPanelProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = myRole === "admin";

  const fetchMembers = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ members: Member[] }>(`/v1/spaces/${spaceId}/members`);
      setMembers(data.members);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load members");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, [spaceId]);

  const handleRoleChange = async (userId: string, newRole: Role) => {
    try {
      await api.put(`/v1/spaces/${spaceId}/members/${userId}`, { role: newRole });
      await fetchMembers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to change role");
    }
  };

  const handleRemove = async (userId: string) => {
    if (!confirm("Remove this member?")) return;
    try {
      await api.delete(`/v1/spaces/${spaceId}/members/${userId}`);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  if (loading) return <p className="text-sm text-slate-500">Loading members…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-left">
              <th className="py-2 pr-4 font-medium text-slate-600">Member</th>
              <th className="py-2 pr-4 font-medium text-slate-600">Role</th>
              {isAdmin && <th className="py-2 font-medium text-slate-600">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 pr-4 max-w-[16rem]">
                  <div className="font-medium text-slate-800 truncate">
                    {member.display_name || member.email || "Unknown user"}
                  </div>
                  {member.display_name && member.email && (
                    <div className="text-xs text-slate-500 truncate">{member.email}</div>
                  )}
                </td>
                <td className="py-3 pr-4">
                  {isAdmin ? (
                    <select
                      value={member.role}
                      onChange={(e) => handleRoleChange(member.user_id, e.target.value as Role)}
                      className="text-sm border border-slate-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="viewer">viewer</option>
                      <option value="editor">editor</option>
                      <option value="admin">admin</option>
                    </select>
                  ) : (
                    <RoleBadge role={member.role} />
                  )}
                </td>
                {isAdmin && (
                  <td className="py-3">
                    <button
                      onClick={() => handleRemove(member.user_id)}
                      className="text-xs text-red-600 hover:text-red-800 font-medium"
                    >
                      Remove
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {members.length === 0 && (
          <p className="text-sm text-slate-500 py-4 text-center">No members yet.</p>
        )}
      </div>

      {isAdmin && (
        <AddMemberForm spaceId={spaceId} onSuccess={fetchMembers} />
      )}
    </div>
  );
}
