"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { InviteForm } from "@/components/onboarding/InviteForm";
import { sendInvitations } from "@/lib/invitations";
import type { InvitationResult } from "@/lib/invitations";

export default function InvitePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(emails: string[]): Promise<InvitationResult> {
    setLoading(true);
    setError(null);
    try {
      const result = await sendInvitations(emails);
      setDone(true);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send invitations.");
      return { sent: [], failed: [] };
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-1">Invite Your Team</h2>
      <p className="text-sm text-gray-500 mb-6">
        Send invitations to colleagues so they can join your company workspace.
      </p>

      {error && (
        <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      <InviteForm onSubmit={handleSubmit} loading={loading} />

      <div className="mt-6">
        <button
          onClick={() => router.push("/onboarding/complete")}
          className="w-full text-sm text-gray-500 hover:text-gray-700 underline"
        >
          {done ? "Continue to completion →" : "Skip for now"}
        </button>
      </div>
    </div>
  );
}
