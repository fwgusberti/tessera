"use client";

import { useEffect, useRef, useState } from "react";
import {
  addCompanyMember,
  inviteCompanyMember,
  searchAddableUsers,
  type AddableUser,
  type CompanyMember,
  type CompanyRole,
} from "@/lib/companies";
import { ApiError } from "@/lib/api";

// Simple client-side email shape check — a malformed address is rejected before
// any API call (FR-006). The server re-validates with Pydantic EmailStr.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Mode = "invite" | "existing";

type Outcome =
  | { kind: "idle" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

type SearchStatus = "idle" | "loading" | "empty" | "error" | "results";

interface AddUserPanelProps {
  /** Called with the new membership when a user is direct-added (US2). */
  onMemberAdded?: (member: CompanyMember) => void;
}

function describeInviteError(err: unknown): string {
  const code = err instanceof ApiError ? err.code : null;
  switch (code) {
    case "already_member":
      return "That person is already a member of this company.";
    case "already_invited":
      return "An invitation for that email is already pending.";
    case "send_failed":
      return "The invitation could not be delivered. Please try again.";
    default:
      return err instanceof Error && err.message
        ? err.message
        : "Something went wrong. Please try again.";
  }
}

function describeAddError(err: unknown): string {
  const code = err instanceof ApiError ? err.code : null;
  switch (code) {
    case "already_member":
      return "That person is already a member of this company.";
    case "no_such_user":
      return "No such user — they may no longer have an account.";
    default:
      return err instanceof Error && err.message
        ? err.message
        : "Something went wrong. Please try again.";
  }
}

export function AddUserPanel({ onMemberAdded }: AddUserPanelProps = {}) {
  const [mode, setMode] = useState<Mode>("invite");
  const [role, setRole] = useState<CompanyRole>("member");
  const [submitting, setSubmitting] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>({ kind: "idle" });

  // Invite-by-email state.
  const [email, setEmail] = useState("");

  // Direct-add state.
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AddableUser[]>([]);
  const [searchStatus, setSearchStatus] = useState<SearchStatus>("idle");
  const [selected, setSelected] = useState<AddableUser | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (mode !== "existing") return;
    const trimmed = query.trim();
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (trimmed.length < 2) {
      setSearchStatus("idle");
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(() => {
      setSearchStatus("loading");
      searchAddableUsers(trimmed)
        .then((users) => {
          setResults(users);
          setSearchStatus(users.length === 0 ? "empty" : "results");
        })
        .catch(() => setSearchStatus("error"));
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, mode]);

  const switchMode = (next: Mode) => {
    setMode(next);
    setOutcome({ kind: "idle" });
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!EMAIL_RE.test(trimmed)) {
      setOutcome({ kind: "error", message: "Please enter a valid email address." });
      return;
    }
    setSubmitting(true);
    setOutcome({ kind: "idle" });
    try {
      const res = await inviteCompanyMember(trimmed, role);
      setOutcome({ kind: "success", message: `Invitation sent to ${res.email}.` });
      setEmail("");
    } catch (err: unknown) {
      setOutcome({ kind: "error", message: describeInviteError(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setOutcome({ kind: "idle" });
    try {
      const member = await addCompanyMember(selected.user_id, role);
      onMemberAdded?.(member);
      setOutcome({
        kind: "success",
        message: `${member.display_name || member.email} was added to the company.`,
      });
      setQuery("");
      setResults([]);
      setSearchStatus("idle");
      setSelected(null);
    } catch (err: unknown) {
      setOutcome({ kind: "error", message: describeAddError(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const tabClass = (active: boolean) =>
    `px-3 py-1.5 text-sm font-medium rounded-md ${
      active ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"
    }`;

  return (
    <div className="flex flex-col gap-4 p-4 border border-slate-200 rounded-lg bg-slate-50">
      <h2 className="text-sm font-semibold text-slate-700">Add user</h2>

      <div className="flex gap-2">
        <button type="button" className={tabClass(mode === "invite")} onClick={() => switchMode("invite")}>
          Invite by email
        </button>
        <button
          type="button"
          className={tabClass(mode === "existing")}
          onClick={() => switchMode("existing")}
        >
          Add existing user
        </button>
      </div>

      <label className="flex flex-col gap-1 text-sm text-slate-600 max-w-xs">
        Role
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as CompanyRole)}
          disabled={submitting}
          className="px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="member">Member</option>
          <option value="admin">Administrator</option>
        </select>
      </label>

      {mode === "invite" && (
        <form onSubmit={handleInvite} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm text-slate-600">
            Email
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="person@company.com"
              disabled={submitting}
              className="px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="self-start px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
          >
            {submitting ? "Sending…" : "Send invite"}
          </button>
        </form>
      )}

      {mode === "existing" && (
        <form onSubmit={handleAdd} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm text-slate-600">
            Search
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(null);
              }}
              placeholder="Search by name or email"
              disabled={submitting}
              className="px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </label>

          {searchStatus === "loading" && <p className="text-xs text-slate-500">Searching…</p>}
          {searchStatus === "empty" && <p className="text-xs text-slate-500">No matches found.</p>}
          {searchStatus === "error" && (
            <p className="text-xs text-red-600">Could not search users. Please try again.</p>
          )}

          {searchStatus === "results" && !selected && (
            <ul className="flex flex-col gap-1 max-h-40 overflow-y-auto">
              {results.map((u) => (
                <li key={u.user_id}>
                  <button
                    type="button"
                    onClick={() => setSelected(u)}
                    className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-slate-100"
                  >
                    <span className="font-medium text-slate-800">{u.display_name}</span>{" "}
                    <span className="text-slate-500">{u.email}</span>
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

          <button
            type="submit"
            disabled={!selected || submitting}
            className="self-start px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
          >
            {submitting ? "Adding…" : "Add user"}
          </button>
        </form>
      )}

      {outcome.kind === "success" && <p className="text-sm text-green-700">{outcome.message}</p>}
      {outcome.kind === "error" && <p className="text-sm text-red-600">{outcome.message}</p>}
    </div>
  );
}
