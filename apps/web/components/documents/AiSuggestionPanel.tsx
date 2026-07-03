"use client";

import { useState } from "react";

interface AiSuggestionPanelProps {
  suggestion: string | null;
  status: "idle" | "loading" | "error";
  errorMessage?: string;
  onAccept: () => void;
  onDiscard: () => void;
  onRefine: (instruction: string) => void;
}

export function AiSuggestionPanel({
  suggestion,
  status,
  errorMessage,
  onAccept,
  onDiscard,
  onRefine,
}: AiSuggestionPanelProps) {
  const [refineText, setRefineText] = useState("");

  if (status === "idle" && suggestion === null) return null;

  const handleRefine = () => {
    onRefine(refineText);
    setRefineText("");
  };

  return (
    <div className="bg-indigo-50 border border-indigo-200 rounded p-3 space-y-2">
      <h3 className="text-sm font-semibold text-indigo-900">AI Suggestion</h3>

      {status === "loading" && <p className="text-sm text-slate-600">Generating suggestion…</p>}

      {status === "error" && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
          {errorMessage ?? "Failed to generate a suggestion"}
        </div>
      )}

      {suggestion !== null && (
        <>
          <div className="bg-white border border-indigo-100 rounded p-2 text-sm whitespace-pre-wrap font-mono">
            {suggestion}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onAccept}
              className="px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={onDiscard}
              className="px-3 py-1.5 text-sm font-medium text-slate-700 border rounded hover:bg-slate-50"
            >
              Discard
            </button>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              aria-label="Refine instruction"
              value={refineText}
              onChange={(e) => setRefineText(e.target.value)}
              placeholder="Refine further…"
              className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={handleRefine}
              disabled={status === "loading"}
              className="px-3 py-1.5 text-sm font-medium text-slate-700 border rounded hover:bg-slate-50 disabled:opacity-50 whitespace-nowrap"
            >
              Refine
            </button>
          </div>
        </>
      )}
    </div>
  );
}
