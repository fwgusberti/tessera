"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { AuthGuard } from "@/lib/auth-guard";
import { SpaceMembersPanel } from "@/components/members/SpaceMembersPanel";
import { RoleBadge } from "@/components/members/RoleBadge";

type Role = "admin" | "editor" | "viewer";

interface MyMembership {
  space_id: string;
  user_id: string;
  role: Role;
  created_at: string;
}

export default function SpaceMembersPage() {
  const params = useParams();
  const spaceId = params?.id as string;

  const [myRole, setMyRole] = useState<Role | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!spaceId) return;
    api
      .get<{ membership: MyMembership }>(`/v1/spaces/${spaceId}/members/me`)
      .then((data) => setMyRole(data.membership.role))
      .catch((err) => {
        if (err?.status === 404) {
          setError("You are not a member of this space.");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load membership");
        }
      })
      .finally(() => setLoading(false));
  }, [spaceId]);

  return (
    <AuthGuard>
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-slate-900">Space Members</h1>
          {myRole && (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              Your role: <RoleBadge role={myRole} />
            </div>
          )}
        </div>

        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}
        {!loading && !error && (
          <SpaceMembersPanel spaceId={spaceId} myRole={myRole} />
        )}
      </main>
    </AuthGuard>
  );
}
