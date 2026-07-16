"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/lib/auth-guard";
import { getCompanyMembers, type CompanyMember } from "@/lib/companies";
import { useCompany } from "@/lib/company";
import { CompanyRoleBadge } from "@/components/company/CompanyRoleBadge";
import { AddUserPanel } from "@/components/company/AddUserPanel";
import { MemberSpaceAccessPanel } from "@/components/members/MemberSpaceAccessPanel";

export default function UsersPage() {
  const { activeCompany } = useCompany();
  const isAdmin = activeCompany?.role === "admin";

  const [members, setMembers] = useState<CompanyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [spacesMember, setSpacesMember] = useState<CompanyMember | null>(null);

  useEffect(() => {
    getCompanyMembers()
      .then((data) => setMembers(data))
      .catch((err: Error) => {
        const message = err.message ?? "Failed to load users";
        // Access-control failures (403/401) surface a clean denial, never a roster.
        if (/access denied|forbidden|session expired|not authenticated/i.test(message)) {
          setDenied(true);
        } else {
          setError(message);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const handleMemberAdded = (member: CompanyMember) => {
    // FR-013: a direct-added member appears in the roster in place (no reload).
    setMembers((prev) =>
      prev.some((m) => m.user_id === member.user_id) ? prev : [...prev, member]
    );
  };

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Users</h1>
          {isAdmin && !denied && (
            <button
              onClick={() => setShowAddPanel((v) => !v)}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md"
            >
              {showAddPanel ? "Close" : "Add user"}
            </button>
          )}
        </div>

        {isAdmin && showAddPanel && !denied && (
          <AddUserPanel onMemberAdded={handleMemberAdded} />
        )}

        {loading && <p className="text-sm text-slate-500">Loading users…</p>}

        {!loading && denied && (
          <p className="text-sm text-slate-600">
            Access denied — only company administrators can view the user list.
          </p>
        )}

        {!loading && !denied && error && (
          <p className="text-sm text-red-600">{error}</p>
        )}

        {!loading && !denied && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="py-2 pr-4 font-medium text-slate-600">User</th>
                  <th className="py-2 font-medium text-slate-600">Role</th>
                  {isAdmin && (
                    <th className="py-2 font-medium text-slate-600">Actions</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr
                    key={member.user_id}
                    className="border-b border-slate-100 hover:bg-slate-50"
                  >
                    <td className="py-3 pr-4">
                      <div className="font-medium text-slate-800">
                        {member.display_name || member.email || "Unknown user"}
                      </div>
                      {member.email && (
                        <div className="text-xs text-slate-500">{member.email}</div>
                      )}
                    </td>
                    <td className="py-3">
                      <CompanyRoleBadge role={member.role} />
                    </td>
                    {isAdmin && (
                      <td className="py-3">
                        <button
                          onClick={() =>
                            setSpacesMember((prev) =>
                              prev?.user_id === member.user_id ? null : member
                            )
                          }
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                        >
                          {spacesMember?.user_id === member.user_id
                            ? "Close spaces"
                            : "Spaces"}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {members.length === 0 && (
              <p className="text-sm text-slate-500 py-4 text-center">No users yet.</p>
            )}
            {isAdmin && spacesMember && (
              <div className="mt-4">
                <MemberSpaceAccessPanel member={spacesMember} />
              </div>
            )}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
