"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CompanyForm } from "@/components/onboarding/CompanyForm";
import { CompanySuggestions } from "@/components/onboarding/CompanySuggestions";
import { createCompany, getSuggestions, joinCompany } from "@/lib/companies";
import type { CompanySuggestions as Suggestions } from "@/lib/companies";
import { getOnboardingStatus } from "@/lib/onboarding";

type View = "loading" | "suggestions" | "create";

export default function CompanyPage() {
  const router = useRouter();
  const [view, setView] = useState<View>("loading");
  const [suggestions, setSuggestions] = useState<Suggestions | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSuggestions()
      .then((data) => {
        setSuggestions(data);
        const hasSuggestions =
          data.invitations.length > 0 || data.domain_matches.length > 0;
        setView(hasSuggestions ? "suggestions" : "create");
      })
      .catch(() => setView("create"));
  }, []);

  async function handleCreateCompany(data: {
    name: string;
    industry?: string;
    team_size?: string;
  }) {
    setActionLoading(true);
    setError(null);
    try {
      await createCompany(data);
      router.push("/onboarding/invite");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create company.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleJoinViaInvitation(companyId: string, invitationId: string) {
    setActionLoading(true);
    setError(null);
    try {
      const result = await joinCompany(companyId, "invitation", invitationId);
      if (result.status === "joined") {
        const status = await getOnboardingStatus();
        if (status.company_join_method === "joined") {
          router.push("/onboarding/complete");
        } else {
          router.push("/onboarding/invite");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to join company.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleJoinViaDomain(companyId: string) {
    setActionLoading(true);
    setError(null);
    try {
      const result = await joinCompany(companyId, "domain_match");
      if (result.status === "joined") {
        router.push("/onboarding/complete");
      } else if (result.status === "pending") {
        router.push(`/onboarding/pending?company=${companyId}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to join company.");
    } finally {
      setActionLoading(false);
    }
  }

  if (view === "loading") {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-1">Your Company</h2>
      <p className="text-sm text-gray-500 mb-6">
        {view === "suggestions"
          ? "We found some companies that match your email. Join one or create a new one."
          : "Create a new company workspace for your team."}
      </p>

      {error && (
        <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      {view === "suggestions" && suggestions && (
        <div className="space-y-4">
          <CompanySuggestions
            invitations={suggestions.invitations}
            domainMatches={suggestions.domain_matches}
            onJoinViaInvitation={handleJoinViaInvitation}
            onJoinViaDomain={handleJoinViaDomain}
            loading={actionLoading}
          />
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-white px-2 text-gray-400">or</span>
            </div>
          </div>
          <button
            onClick={() => setView("create")}
            className="w-full border border-gray-300 text-gray-700 rounded px-4 py-2 text-sm font-medium hover:bg-gray-50"
          >
            Create a new company
          </button>
        </div>
      )}

      {view === "create" && (
        <>
          <CompanyForm onSubmit={handleCreateCompany} loading={actionLoading} />
          {suggestions && (suggestions.invitations.length > 0 || suggestions.domain_matches.length > 0) && (
            <button
              onClick={() => setView("suggestions")}
              className="mt-3 w-full text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Back to suggestions
            </button>
          )}
        </>
      )}
    </div>
  );
}
