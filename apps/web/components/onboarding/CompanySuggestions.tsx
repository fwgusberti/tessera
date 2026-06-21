"use client";

import type { CompanySuggestionDomainMatch, CompanySuggestionInvitation } from "@/lib/companies";

interface CompanySuggestionsProps {
  invitations: CompanySuggestionInvitation[];
  domainMatches: CompanySuggestionDomainMatch[];
  onJoinViaInvitation(companyId: string, invitationId: string): Promise<void>;
  onJoinViaDomain(companyId: string): Promise<void>;
  loading?: boolean;
}

function InvitationCard({
  invitation,
  onJoin,
  loading,
}: {
  invitation: CompanySuggestionInvitation;
  onJoin(): void;
  loading?: boolean;
}) {
  const expiresDate = new Date(invitation.expires_at).toLocaleDateString();

  return (
    <div className="border border-indigo-200 bg-indigo-50 rounded-lg p-4 flex items-center justify-between">
      <div className="min-w-0">
        <p className="font-medium text-slate-900 truncate">{invitation.company_name}</p>
        {invitation.invited_by && (
          <p className="text-sm text-slate-500">Invited by {invitation.invited_by}</p>
        )}
        <p className="text-xs text-slate-400 mt-1">Expires {expiresDate}</p>
      </div>
      <button
        onClick={onJoin}
        disabled={loading}
        className="ml-4 bg-indigo-600 text-white rounded px-3 py-1.5 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
      >
        Accept
      </button>
    </div>
  );
}

function DomainMatchCard({
  match,
  onJoin,
  loading,
}: {
  match: CompanySuggestionDomainMatch;
  onJoin(): void;
  loading?: boolean;
}) {
  const isAutoJoin = match.policy === "auto_join";

  return (
    <div className="border border-slate-200 bg-white rounded-lg p-4 flex items-center justify-between">
      <div className="min-w-0">
        <p className="font-medium text-slate-900 truncate">{match.company_name}</p>
        <p className="text-sm text-slate-500">
          {isAutoJoin ? "Join instantly via" : "Request access via"} @{match.domain}
        </p>
      </div>
      <button
        onClick={onJoin}
        disabled={loading}
        className="ml-4 border border-slate-300 text-slate-700 rounded px-3 py-1.5 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 whitespace-nowrap"
      >
        {isAutoJoin ? "Join" : "Request Access"}
      </button>
    </div>
  );
}

export function CompanySuggestions({
  invitations,
  domainMatches,
  onJoinViaInvitation,
  onJoinViaDomain,
  loading = false,
}: CompanySuggestionsProps) {
  const invitedCompanyIds = new Set(invitations.map((i) => i.company_id));
  const filteredDomainMatches = domainMatches.filter(
    (m) => !invitedCompanyIds.has(m.company_id)
  );

  return (
    <div className="space-y-3">
      {invitations.map((inv) => (
        <InvitationCard
          key={inv.id}
          invitation={inv}
          onJoin={() => onJoinViaInvitation(inv.company_id, inv.id)}
          loading={loading}
        />
      ))}
      {filteredDomainMatches.map((match) => (
        <DomainMatchCard
          key={match.company_id}
          match={match}
          onJoin={() => onJoinViaDomain(match.company_id)}
          loading={loading}
        />
      ))}
    </div>
  );
}
