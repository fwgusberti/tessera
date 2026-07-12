"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { generateDraft } from "@/lib/documentAssist";
import type { Document, DocumentVersion, Space } from "@/lib/types";

interface AddDocumentModalProps {
  open: boolean;
  spaces: Space[];
  initialSpaceId?: string;
  onClose: () => void;
  onCreated: (document: Document) => void;
}

export function AddDocumentModal({ open, spaces, initialSpaceId, onClose, onCreated }: AddDocumentModalProps) {
  const [title, setTitle] = useState("");
  const [spaceId, setSpaceId] = useState(initialSpaceId ?? "");
  const [language, setLanguage] = useState("pt-BR");
  const [confidentiality, setConfidentiality] = useState<"internal" | "restricted" | "public">("internal");
  const [contentMarkdown, setContentMarkdown] = useState("");
  const [errors, setErrors] = useState<{ title?: string; spaceId?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [canGenerateAi, setCanGenerateAi] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiPromptError, setAiPromptError] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<"idle" | "loading" | "error">("idle");
  const [aiError, setAiError] = useState<string | null>(null);
  const [preAiContent, setPreAiContent] = useState<string | null>(null);
  const [lastAiSuggestion, setLastAiSuggestion] = useState<string | null>(null);
  const [refineText, setRefineText] = useState("");

  useEffect(() => {
    if (!open) {
      setTitle("");
      setSpaceId(initialSpaceId ?? "");
      setLanguage("pt-BR");
      setConfidentiality("internal");
      setContentMarkdown("");
      setErrors({});
      setApiError(null);
      setSubmitting(false);
      setCanGenerateAi(false);
      setAiPrompt("");
      setAiPromptError(null);
      setAiStatus("idle");
      setAiError(null);
      setPreAiContent(null);
      setLastAiSuggestion(null);
      setRefineText("");
    }
  }, [open, initialSpaceId]);

  useEffect(() => {
    if (!spaceId) {
      setCanGenerateAi(false);
      return;
    }
    let cancelled = false;
    api
      .get<{ membership: { role: string } }>(`/v1/spaces/${spaceId}/members/me`)
      .then((data) => {
        if (cancelled) return;
        const role = data.membership.role;
        setCanGenerateAi(role === "editor" || role === "admin");
      })
      .catch(() => {
        if (!cancelled) setCanGenerateAi(false);
      });
    return () => {
      cancelled = true;
    };
  }, [spaceId]);

  const handleGenerateAi = async () => {
    if (!aiPrompt.trim()) {
      setAiPromptError("Prompt is required");
      return;
    }
    setAiPromptError(null);
    setAiError(null);
    setAiStatus("loading");
    try {
      const result = await generateDraft(spaceId, aiPrompt, lastAiSuggestion ?? undefined);
      setPreAiContent((prev) => (prev === null ? contentMarkdown : prev));
      setContentMarkdown(result.content_markdown);
      setLastAiSuggestion(result.content_markdown);
      setAiStatus("idle");
    } catch (err) {
      setAiStatus("error");
      setAiError(err instanceof Error ? err.message : "Failed to generate draft");
    }
  };

  const handleRefineAi = async () => {
    if (lastAiSuggestion === null) return;
    setAiError(null);
    setAiStatus("loading");
    try {
      const result = await generateDraft(spaceId, refineText, lastAiSuggestion);
      setContentMarkdown(result.content_markdown);
      setLastAiSuggestion(result.content_markdown);
      setRefineText("");
      setAiStatus("idle");
    } catch (err) {
      setAiStatus("error");
      setAiError(err instanceof Error ? err.message : "Failed to refine draft");
    }
  };

  const handleDiscardAi = () => {
    if (preAiContent !== null) setContentMarkdown(preAiContent);
    setPreAiContent(null);
    setLastAiSuggestion(null);
    setRefineText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: { title?: string; spaceId?: string } = {};
    if (!title.trim()) newErrors.title = "Title is required";
    if (!spaceId) newErrors.spaceId = "Space is required";
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    setSubmitting(true);
    setApiError(null);
    try {
      const data = await api.post<{ document: Document; version: DocumentVersion }>("/v1/documents", {
        space_id: spaceId,
        title: title.trim(),
        language,
        confidentiality,
        content_markdown: contentMarkdown,
        tags: [],
        frontmatter: {},
      });
      onCreated(data.document);
      onClose();
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to create document");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onKeyDown={handleKeyDown}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-doc-title"
        className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b">
          <h2 id="add-doc-title" className="text-lg font-semibold text-slate-900">Add Document</h2>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          {apiError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
              {apiError}
            </div>
          )}

          <div>
            <label htmlFor="doc-title" className="block text-sm font-medium text-slate-700 mb-1">
              Title
            </label>
            <input
              id="doc-title"
              type="text"
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Document title"
            />
            {errors.title && <p className="text-red-600 text-xs mt-1">{errors.title}</p>}
          </div>

          <div>
            <label htmlFor="doc-space" className="block text-sm font-medium text-slate-700 mb-1">
              Space
            </label>
            {spaces.length === 0 ? (
              <p className="text-sm text-slate-500 italic">No spaces available — create a space first.</p>
            ) : (
              <select
                id="doc-space"
                value={spaceId}
                onChange={(e) => setSpaceId(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select a space…</option>
                {spaces.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            )}
            {errors.spaceId && <p className="text-red-600 text-xs mt-1">{errors.spaceId}</p>}
          </div>

          {canGenerateAi && (
            <div className="bg-indigo-50 border border-indigo-200 rounded p-3 space-y-2">
              <label htmlFor="ai-prompt" className="block text-sm font-medium text-slate-700">
                AI Prompt
              </label>
              <div className="flex gap-2">
                <input
                  id="ai-prompt"
                  type="text"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g. Onboarding checklist for new hires"
                />
                <button
                  type="button"
                  onClick={handleGenerateAi}
                  disabled={aiStatus === "loading"}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
                >
                  {aiStatus === "loading" ? "Generating…" : "Generate with AI"}
                </button>
              </div>
              {aiPromptError && <p className="text-red-600 text-xs">{aiPromptError}</p>}
              {aiError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
                  {aiError}
                </div>
              )}
              {lastAiSuggestion !== null && (
                <div className="flex gap-2 pt-1">
                  <input
                    type="text"
                    aria-label="Refine instruction"
                    value={refineText}
                    onChange={(e) => setRefineText(e.target.value)}
                    className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Refine further…"
                  />
                  <button
                    type="button"
                    onClick={handleRefineAi}
                    disabled={aiStatus === "loading"}
                    className="px-3 py-1.5 text-sm font-medium text-slate-700 border rounded hover:bg-slate-50 disabled:opacity-50 whitespace-nowrap"
                  >
                    Refine
                  </button>
                  <button
                    type="button"
                    onClick={handleDiscardAi}
                    className="px-3 py-1.5 text-sm font-medium text-slate-700 border rounded hover:bg-slate-50 whitespace-nowrap"
                  >
                    Discard AI draft
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="doc-language" className="block text-sm font-medium text-slate-700 mb-1">
                Language
              </label>
              <select
                id="doc-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="pt-BR">pt-BR</option>
                <option value="en">en</option>
              </select>
            </div>

            <div>
              <label htmlFor="doc-confidentiality" className="block text-sm font-medium text-slate-700 mb-1">
                Confidentiality
              </label>
              <select
                id="doc-confidentiality"
                value={confidentiality}
                onChange={(e) => setConfidentiality(e.target.value as typeof confidentiality)}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="internal">Internal</option>
                <option value="restricted">Restricted</option>
                <option value="public">Public</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="doc-content" className="block text-sm font-medium text-slate-700 mb-1">
              Content (Markdown)
            </label>
            <textarea
              id="doc-content"
              value={contentMarkdown}
              onChange={(e) => setContentMarkdown(e.target.value)}
              rows={6}
              className="w-full border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
              placeholder="# Title&#10;&#10;Content here…"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 border rounded hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || spaces.length === 0}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
