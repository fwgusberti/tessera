"use client";

import React, { useState } from "react";
import { useCompany } from "@/lib/company";

const TEAM_SIZES = ["1-10", "11-50", "51-200", "201-1000", "1000+"];

interface Props {
  open: boolean;
  onClose(): void;
}

export function CreateCompanyModal({ open, onClose }: Props) {
  const { createAndSetActive } = useCompany();
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [teamSize, setTeamSize] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await createAndSetActive({
        name: name.trim(),
        ...(industry ? { industry } : {}),
        ...(teamSize ? { team_size: teamSize } : {}),
      });
      setName("");
      setIndustry("");
      setTeamSize("");
      onClose();
    } catch {
      setError("Failed to create company. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Create company"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Create a new company</h2>
        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4">
            <label htmlFor="company-name" className="block text-sm font-medium text-slate-700 mb-1">
              Company name
            </label>
            <input
              id="company-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Acme Corp"
            />
          </div>

          <div className="mb-4">
            <label htmlFor="company-industry" className="block text-sm font-medium text-slate-700 mb-1">
              Industry <span className="text-slate-400">(optional)</span>
            </label>
            <input
              id="company-industry"
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Technology"
            />
          </div>

          <div className="mb-4">
            <label htmlFor="company-team-size" className="block text-sm font-medium text-slate-700 mb-1">
              Team size <span className="text-slate-400">(optional)</span>
            </label>
            <select
              id="company-team-size"
              value={teamSize}
              onChange={(e) => setTeamSize(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select size</option>
              {TEAM_SIZES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-600 mb-4">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded disabled:opacity-50"
            >
              {submitting ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
