"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/lib/auth-guard";
import {
  getCurrentCompany,
  updateCurrentCompany,
  type CompanyProfile,
} from "@/lib/companies";
import { useCompany } from "@/lib/company";
import { INDUSTRIES, TEAM_SIZES } from "@/lib/companyOptions";

function formatCreatedAt(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function NotProvided() {
  return <span className="text-slate-400">Not provided</span>;
}

export default function CompanySettingsPage() {
  const { reloadCompanies } = useCompany();

  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [teamSize, setTeamSize] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    getCurrentCompany()
      .then((data) => setProfile(data))
      .catch((err: Error) => setLoadError(err.message ?? "Failed to load company"))
      .finally(() => setLoading(false));
  }, []);

  function startEditing() {
    if (!profile) return;
    setName(profile.name);
    setIndustry(profile.industry ?? "");
    setTeamSize(profile.team_size ?? "");
    setFormError(null);
    setEditing(true);
  }

  function cancelEditing() {
    setEditing(false);
    setFormError(null);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setFormError("Company name is required.");
      return;
    }
    setFormError(null);
    setSaving(true);
    try {
      const saved = await updateCurrentCompany({
        name: trimmed,
        industry: industry || null,
        team_size: teamSize || null,
      });
      // Swap in the authoritative saved profile atomically, then refresh the
      // company menu so the new name shows everywhere immediately (FR-007).
      setProfile(saved);
      setEditing(false);
      await reloadCompanies();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  const isAdmin = profile?.role === "admin";

  return (
    <AuthGuard>
      <div className="max-w-2xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-slate-900">Company</h1>
          {isAdmin && !editing && (
            <button
              type="button"
              onClick={startEditing}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md"
            >
              Edit
            </button>
          )}
        </div>

        {loading && <p className="text-sm text-slate-500">Loading company…</p>}

        {!loading && loadError && <p className="text-sm text-red-600">{loadError}</p>}

        {!loading && !loadError && profile && !editing && (
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <dl className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-slate-500">Name</dt>
                <dd className="mt-1 text-sm text-slate-900">{profile.name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Industry</dt>
                <dd className="mt-1 text-sm text-slate-900">
                  {profile.industry ?? <NotProvided />}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Team Size</dt>
                <dd className="mt-1 text-sm text-slate-900">
                  {profile.team_size ?? <NotProvided />}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Created</dt>
                <dd className="mt-1 text-sm text-slate-900">
                  {formatCreatedAt(profile.created_at)}
                </dd>
              </div>
            </dl>
          </div>
        )}

        {!loading && !loadError && profile && editing && (
          <form
            onSubmit={handleSave}
            className="rounded-lg border border-slate-200 bg-white p-6 space-y-4"
          >
            <div>
              <label
                htmlFor="companyName"
                className="block text-sm font-medium text-slate-700 mb-1"
              >
                Company Name <span className="text-red-500">*</span>
              </label>
              <input
                id="companyName"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={255}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label htmlFor="industry" className="block text-sm font-medium text-slate-700 mb-1">
                Industry <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <select
                id="industry"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select industry…</option>
                {INDUSTRIES.map((i) => (
                  <option key={i} value={i}>
                    {i}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="teamSize" className="block text-sm font-medium text-slate-700 mb-1">
                Team Size <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <select
                id="teamSize"
                value={teamSize}
                onChange={(e) => setTeamSize(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select team size…</option>
                {TEAM_SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s} people
                  </option>
                ))}
              </select>
            </div>

            <div>
              <span className="block text-sm font-medium text-slate-500 mb-1">Created</span>
              <p className="text-sm text-slate-500">{formatCreatedAt(profile.created_at)}</p>
            </div>

            {formError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                {formError}
              </p>
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                type="button"
                onClick={cancelEditing}
                disabled={saving}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </AuthGuard>
  );
}
