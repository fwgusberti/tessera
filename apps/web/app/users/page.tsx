"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/lib/auth-guard";
import { getCompanyMembers, type CompanyMember } from "@/lib/companies";
import { CompanyRoleBadge } from "@/components/company/CompanyRoleBadge";

export default function UsersPage() {
  const [members, setMembers] = useState<CompanyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <AuthGuard>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Users</h1>

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
                        {member.display_name || member.email}
                      </div>
                      {member.email && (
                        <div className="text-xs text-slate-500">{member.email}</div>
                      )}
                    </td>
                    <td className="py-3">
                      <CompanyRoleBadge role={member.role} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {members.length === 0 && (
              <p className="text-sm text-slate-500 py-4 text-center">No users yet.</p>
            )}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
