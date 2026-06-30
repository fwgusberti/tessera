"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { CompanyMemberMatch } from "@/lib/types";

type Role = "admin" | "editor" | "viewer";

type SearchStatus = "idle" | "loading" | "empty" | "error" | "results";

interface AddMemberFormProps {
  spaceId: string;
  onSuccess: () => void;
}

/**
 * The shared `api` client only surfaces the server's HTTP reason phrase for
 * these endpoints (members.py returns bare-string error details, not the
 * {error:{message}} shape the client parses) — so 400/403/404 are
 * distinguished by their standard reason phrase, not custom copy.
 */
function describeSubmitError(err: unknown): { refreshOnFailure: boolean; message: string } {
  const raw = err instanceof Error ? err.message : "";
  if (raw === "Bad Request") {
    return { refreshOnFailure: true, message: "This person is already a member of this space." };
  }
  if (raw === "Forbidden") {
    return {
      refreshOnFailure: false,
      message: "You don't have permission to add members to this space.",
    };
  }
  if (raw === "Not Found") {
    return {
      refreshOnFailure: false,
      message: "This person is no longer eligible to be added (they may have left the company).",
    };
  }
  return {
    refreshOnFailure: false,
    message: raw || "Something went wrong while adding this member. Please try again.",
  };
}

export function AddMemberForm({ spaceId, onSuccess }: AddMemberFormProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CompanyMemberMatch[]>([]);
  const [searchStatus, setSearchStatus] = useState<SearchStatus>("idle");
  const [selected, setSelected] = useState<CompanyMemberMatch | null>(null);
  const [role, setRole] = useState<Role>("viewer");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const trimmed = query.trim();
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (trimmed.length < 2) {
      setSearchStatus("idle");
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(() => {
      setSearchStatus("loading");
      api
        .get<{ members: CompanyMemberMatch[] }>(
          `/v1/spaces/${spaceId}/members/search?q=${encodeURIComponent(trimmed)}`
        )
        .then((data) => {
          setResults(data.members);
          setSearchStatus(data.members.length === 0 ? "empty" : "results");
        })
        .catch(() => {
          setSearchStatus("error");
        });
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, spaceId]);

  const handleSelect = (member: CompanyMemberMatch) => {
    setSelected(member);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.post(`/v1/spaces/${spaceId}/members`, { user_id: selected.user_id, role });
      setQuery("");
      setResults([]);
      setSearchStatus("idle");
      setSelected(null);
      setRole("viewer");
      onSuccess();
    } catch (err: unknown) {
      const { refreshOnFailure, message } = describeSubmitError(err);
      setSubmitError(message);
      // FR-010: query/selected/role are intentionally left untouched here.
      if (refreshOnFailure) onSuccess();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 p-4 border border-slate-200 rounded-lg bg-slate-50">
      <h3 className="text-sm font-semibold text-slate-700">Add Member</h3>

      <input
        type="text"
        placeholder="Search by name or email"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setSelected(null);
        }}
        className="px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
        disabled={submitting}
      />

      {searchStatus === "loading" && <p className="text-xs text-slate-500">Searching…</p>}
      {searchStatus === "empty" && <p className="text-xs text-slate-500">No matches found.</p>}
      {searchStatus === "error" && (
        <p className="text-xs text-red-600">Could not search company members. Please try again.</p>
      )}

      {searchStatus === "results" && !selected && (
        <ul className="flex flex-col gap-1 max-h-40 overflow-y-auto">
          {results.map((member) => (
            <li key={member.user_id}>
              <button
                type="button"
                onClick={() => handleSelect(member)}
                className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-slate-100"
              >
                <span className="font-medium text-slate-800">{member.display_name}</span>{" "}
                <span className="text-slate-500">{member.email}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selected && (
        <div className="text-sm text-slate-700">
          Selected: <span className="font-medium">{selected.display_name}</span>{" "}
          <span className="text-slate-500">({selected.email})</span>{" "}
          <button
            type="button"
            onClick={() => setSelected(null)}
            className="text-xs text-indigo-600 hover:text-indigo-700"
          >
            Change
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
          className="px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          disabled={submitting}
        >
          <option value="viewer">Viewer</option>
          <option value="editor">Editor</option>
          <option value="admin">Admin</option>
        </select>
        <button
          type="submit"
          disabled={!selected || submitting}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
        >
          {submitting ? "Adding…" : "Add Member"}
        </button>
      </form>

      {submitError && <p className="text-xs text-red-600">{submitError}</p>}
    </div>
  );
}
