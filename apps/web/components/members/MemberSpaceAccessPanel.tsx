"use client";

import { useEffect, useState } from "react";
import {
  addSpaceMember,
  changeSpaceMemberRole,
  getMemberSpaceAccess,
  removeSpaceMember,
  type MemberIdentity,
  type MemberSpaceAccessRow,
  type SpaceRole,
} from "@/lib/members";

interface MemberSpaceAccessPanelProps {
  member: MemberIdentity;
}

export function MemberSpaceAccessPanel({ member }: MemberSpaceAccessPanelProps) {
  const [rows, setRows] = useState<MemberSpaceAccessRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // role chosen in a no-access row's grant select, keyed by space id
  const [grantRoles, setGrantRoles] = useState<Record<string, SpaceRole>>({});
  const [busySpaceId, setBusySpaceId] = useState<string | null>(null);

  const refresh = async () => {
    const data = await getMemberSpaceAccess(member.user_id);
    setRows(data.spaces);
  };

  useEffect(() => {
    setLoading(true);
    setError(null);
    getMemberSpaceAccess(member.user_id)
      .then((data) => setRows(data.spaces))
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load space access")
      )
      .finally(() => setLoading(false));
  }, [member.user_id]);

  const handleGrant = async (row: MemberSpaceAccessRow) => {
    const role = grantRoles[row.id] ?? "viewer";
    setBusySpaceId(row.id);
    try {
      await addSpaceMember(row.id, member.user_id, role);
      await refresh();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to grant access");
    } finally {
      setBusySpaceId(null);
    }
  };

  const handleRoleChange = async (row: MemberSpaceAccessRow, role: SpaceRole) => {
    setBusySpaceId(row.id);
    try {
      await changeSpaceMemberRole(row.id, member.user_id, role);
      await refresh();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to change role");
    } finally {
      setBusySpaceId(null);
    }
  };

  const handleRevoke = async (row: MemberSpaceAccessRow) => {
    if (!confirm(`Revoke ${member.display_name || member.email}'s access to ${row.name}?`))
      return;
    setBusySpaceId(row.id);
    try {
      await removeSpaceMember(row.id, member.user_id);
      await refresh();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to revoke access");
    } finally {
      setBusySpaceId(null);
    }
  };

  if (loading) return <p className="text-sm text-slate-500">Loading space access…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="flex flex-col gap-4 p-4 border border-slate-200 rounded-lg bg-slate-50">
      <h2 className="text-sm font-semibold text-slate-700">
        Space access — {member.display_name || member.email}
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-left">
              <th className="py-2 pr-4 font-medium text-slate-600">Space</th>
              <th className="py-2 pr-4 font-medium text-slate-600">Access</th>
              <th className="py-2 font-medium text-slate-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const busy = busySpaceId === row.id;
              return (
                <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-100">
                  <td className="py-3 pr-4 font-medium text-slate-800">{row.name}</td>
                  <td className="py-3 pr-4">
                    {row.is_direct && row.direct_role ? (
                      <select
                        aria-label={`Role in ${row.name}`}
                        value={row.direct_role}
                        disabled={busy}
                        onChange={(e) =>
                          handleRoleChange(row, e.target.value as SpaceRole)
                        }
                        className="text-sm border border-slate-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="viewer">viewer</option>
                        <option value="editor">editor</option>
                        <option value="admin">admin</option>
                      </select>
                    ) : row.effective_role ? (
                      <span className="text-slate-600">
                        Inherited ({row.effective_role})
                      </span>
                    ) : (
                      <span className="text-slate-500">No access</span>
                    )}
                  </td>
                  <td className="py-3">
                    {row.is_direct ? (
                      <button
                        onClick={() => handleRevoke(row)}
                        disabled={busy}
                        className="text-xs text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
                      >
                        Revoke
                      </button>
                    ) : row.effective_role ? null : (
                      <span className="inline-flex items-center gap-2">
                        <select
                          aria-label={`Grant role in ${row.name}`}
                          value={grantRoles[row.id] ?? "viewer"}
                          disabled={busy}
                          onChange={(e) =>
                            setGrantRoles((prev) => ({
                              ...prev,
                              [row.id]: e.target.value as SpaceRole,
                            }))
                          }
                          className="text-sm border border-slate-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                          <option value="viewer">viewer</option>
                          <option value="editor">editor</option>
                          <option value="admin">admin</option>
                        </select>
                        <button
                          onClick={() => handleGrant(row)}
                          disabled={busy}
                          className="px-3 py-1 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
                        >
                          Grant
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && (
          <p className="text-sm text-slate-500 py-4 text-center">
            No spaces exist in this company yet.
          </p>
        )}
      </div>
    </div>
  );
}
