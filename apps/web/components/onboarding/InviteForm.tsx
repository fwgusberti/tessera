"use client";

import { useState } from "react";
import type { InvitationResult } from "@/lib/invitations";

interface InviteFormProps {
  onSubmit(emails: string[]): Promise<InvitationResult>;
  loading?: boolean;
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function InviteForm({ onSubmit, loading = false }: InviteFormProps) {
  const [input, setInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [result, setResult] = useState<InvitationResult | null>(null);
  const [submitted, setSubmitted] = useState(false);

  function addTag(raw: string) {
    const email = raw.trim().toLowerCase();
    if (!email) return;
    if (!isValidEmail(email)) {
      setFieldError(`"${email}" is not a valid email address.`);
      return;
    }
    if (tags.includes(email)) {
      setFieldError(`${email} is already in the list.`);
      return;
    }
    setFieldError(null);
    setTags((prev) => [...prev, email]);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === "," || e.key === " ") {
      e.preventDefault();
      addTag(input);
    } else if (e.key === "Backspace" && input === "" && tags.length > 0) {
      setTags((prev) => prev.slice(0, -1));
    }
  }

  function removeTag(email: string) {
    setTags((prev) => prev.filter((t) => t !== email));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim()) {
      addTag(input);
      return;
    }
    if (tags.length === 0) {
      setFieldError("Add at least one email address.");
      return;
    }
    setFieldError(null);
    const res = await onSubmit(tags);
    setResult(res);
    setSubmitted(true);
  }

  if (submitted && result) {
    return (
      <div className="space-y-4">
        {result.sent.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm font-medium text-green-800 mb-1">
              Invitations sent ({result.sent.length})
            </p>
            <ul className="text-sm text-green-700 space-y-0.5">
              {result.sent.map((email) => (
                <li key={email}>{email}</li>
              ))}
            </ul>
          </div>
        )}
        {result.failed.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm font-medium text-yellow-800 mb-1">
              Could not invite ({result.failed.length})
            </p>
            <ul className="text-sm text-yellow-700 space-y-0.5">
              {result.failed.map(({ email, reason }) => (
                <li key={email}>
                  {email}{" "}
                  <span className="text-yellow-500">
                    ({reason === "already_member" ? "already a member" : reason === "already_invited" ? "already invited" : reason})
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Email addresses
        </label>
        <div
          className={`flex flex-wrap gap-1.5 items-center border rounded px-3 py-2 min-h-[2.5rem] focus-within:ring-2 focus-within:ring-blue-500 ${
            fieldError ? "border-red-400" : "border-gray-300"
          }`}
          onClick={() => (document.getElementById("invite-input") as HTMLInputElement | null)?.focus()}
        >
          {tags.map((email) => (
            <span
              key={email}
              className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded-full"
            >
              {email}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  removeTag(email);
                }}
                className="text-blue-500 hover:text-blue-700 leading-none"
                aria-label={`Remove ${email}`}
              >
                ×
              </button>
            </span>
          ))}
          <input
            id="invite-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => addTag(input)}
            placeholder={tags.length === 0 ? "alice@company.com, bob@company.com" : ""}
            className="flex-1 min-w-[180px] text-sm outline-none bg-transparent"
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">Press Enter or comma to add each address.</p>
        {fieldError && (
          <p className="text-xs text-red-600 mt-1">{fieldError}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Sending…" : "Send Invitations"}
      </button>
    </form>
  );
}
