"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { reviseContent } from "@/lib/documentAssist";
import type { Document, DocumentDraft, DocumentVersion } from "@/lib/types";
import { AuthGuard } from "@/lib/auth-guard";
import { useAuth } from "@/lib/auth";
import { DocumentContent } from "@/components/documents/DocumentContent";
import { AiSuggestionPanel } from "@/components/documents/AiSuggestionPanel";

type SpaceRole = "admin" | "editor" | "viewer";
type SaveStatus = "idle" | "saving" | "saved" | "error";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AUTOSAVE_DEBOUNCE_MS = 4000;
const AUTOSAVE_MAX_WAIT_MS = 15000;
const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000;

export default function DocumentEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user, accessToken } = useAuth();
  const [document, setDocument] = useState<Document | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [canEdit, setCanEdit] = useState<boolean | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [aiInstruction, setAiInstruction] = useState("");
  const [aiStatus, setAiStatus] = useState<"idle" | "loading" | "error">("idle");
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null);
  const [aiRange, setAiRange] = useState<{ start: number; end: number } | null>(null);
  const contentRef = useRef(content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxWaitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasEditedRef = useRef(false);
  const finalizedRef = useRef(false);
  const accessTokenRef = useRef(accessToken);

  useEffect(() => {
    contentRef.current = content;
  }, [content]);

  useEffect(() => {
    accessTokenRef.current = accessToken;
  }, [accessToken]);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get<{ document: Document; current_version: DocumentVersion | null }>(`/v1/documents/${id}`),
      api
        .get<{ draft: DocumentDraft | null }>(`/v1/documents/${id}/draft`)
        .catch(() => ({ draft: null })),
    ])
      .then(([docData, draftData]) => {
        setDocument(docData.document);
        setContent(draftData.draft?.content_markdown ?? docData.current_version?.content_markdown ?? "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load document"))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    const spaceId = document?.space_id;
    if (!spaceId) return;
    api
      .get<{ membership: { role: SpaceRole } }>(`/v1/spaces/${spaceId}/members/me`)
      .then((data) => {
        const role = data.membership.role;
        setCanEdit(role === "editor" || role === "admin" || user?.isAdmin === true);
      })
      .catch(() => setCanEdit(user?.isAdmin === true));
  }, [document?.space_id, user?.isAdmin]);

  useEffect(() => {
    if (canEdit === false) {
      router.replace(`/documents/${id}`);
    }
  }, [canEdit, id, router]);

  const clearAutosaveTimers = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    if (maxWaitTimerRef.current) {
      clearTimeout(maxWaitTimerRef.current);
      maxWaitTimerRef.current = null;
    }
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }
  }, []);

  const flushDraft = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    if (maxWaitTimerRef.current) {
      clearTimeout(maxWaitTimerRef.current);
      maxWaitTimerRef.current = null;
    }
    setSaveStatus("saving");
    return api
      .put(`/v1/documents/${id}/draft`, { content_markdown: contentRef.current })
      .then(() => setSaveStatus("saved"))
      .catch(() => setSaveStatus("error"));
  }, [id]);

  const finishEditSession = useCallback(
    async (notice?: string) => {
      if (finalizedRef.current) return;
      finalizedRef.current = true;
      const hadEdits = hasEditedRef.current;
      clearAutosaveTimers();
      try {
        if (hadEdits) {
          // flush the latest keystrokes before finalizing, so a finish that
          // races the debounce window doesn't finalize stale draft content
          await flushDraft();
        }
        await api.post(`/v1/documents/${id}/draft/finish`, {});
      } catch {
        // best-effort finalize; still navigate away so the user isn't stuck
      }
      router.push(notice ? `/documents/${id}?notice=${notice}` : `/documents/${id}`);
    },
    [id, router, clearAutosaveTimers, flushDraft],
  );

  useEffect(() => clearAutosaveTimers, [clearAutosaveTimers]);

  useEffect(() => {
    if (canEdit !== true) return;
    const handlePageHide = () => {
      if (!hasEditedRef.current || finalizedRef.current) return;
      finalizedRef.current = true;
      const token = accessTokenRef.current;
      fetch(`${API_URL}/v1/documents/${id}/draft/finish`, {
        method: "POST",
        keepalive: true,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    };
    window.addEventListener("pagehide", handlePageHide);
    return () => window.removeEventListener("pagehide", handlePageHide);
  }, [canEdit, id]);

  const handleContentChange = (value: string) => {
    setContent(value);
    hasEditedRef.current = true;

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(flushDraft, AUTOSAVE_DEBOUNCE_MS);
    if (!maxWaitTimerRef.current) {
      maxWaitTimerRef.current = setTimeout(flushDraft, AUTOSAVE_MAX_WAIT_MS);
    }

    if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
    inactivityTimerRef.current = setTimeout(() => {
      finishEditSession("inactivity-timeout");
    }, INACTIVITY_TIMEOUT_MS);
  };

  const handleRequestRevision = async () => {
    const textarea = textareaRef.current;
    let start = 0;
    let end = content.length;
    if (textarea && textarea.selectionStart !== textarea.selectionEnd) {
      start = textarea.selectionStart;
      end = textarea.selectionEnd;
    }
    const target = content.slice(start, end);
    setAiRange({ start, end });
    setAiStatus("loading");
    setAiError(null);
    try {
      const result = await reviseContent(id, target, aiInstruction);
      setAiSuggestion(result.suggestion);
      setAiStatus("idle");
    } catch (err) {
      setAiStatus("error");
      setAiError(err instanceof Error ? err.message : "Failed to generate revision");
    }
  };

  const handleAcceptSuggestion = () => {
    if (aiSuggestion === null || aiRange === null) return;
    const newContent = content.slice(0, aiRange.start) + aiSuggestion + content.slice(aiRange.end);
    handleContentChange(newContent);
    setAiSuggestion(null);
    setAiRange(null);
    setAiInstruction("");
  };

  const handleDiscardSuggestion = () => {
    setAiSuggestion(null);
    setAiRange(null);
    setAiStatus("idle");
    setAiError(null);
  };

  const handleRefineSuggestion = async (instruction: string) => {
    if (aiSuggestion === null || aiRange === null) return;
    const target = content.slice(aiRange.start, aiRange.end);
    setAiStatus("loading");
    setAiError(null);
    try {
      const result = await reviseContent(id, target, instruction, aiSuggestion);
      setAiSuggestion(result.suggestion);
      setAiStatus("idle");
    } catch (err) {
      setAiStatus("error");
      setAiError(err instanceof Error ? err.message : "Failed to refine suggestion");
    }
  };

  const saveStatusLabel =
    saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "Saved" : saveStatus === "error" ? "Save failed" : null;

  return (
    <AuthGuard>
      {loading ? (
        <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-slate-500">
          Loading document…
        </div>
      ) : error ? (
        <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-red-600">
          {error}
        </div>
      ) : !document ? (
        <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-slate-500">
          Document not found.
        </div>
      ) : canEdit !== true ? (
        <div className="bg-white rounded border border-slate-200 p-8 text-center text-sm text-slate-500">
          {canEdit === false ? "Redirecting…" : "Checking permissions…"}
        </div>
      ) : (
        <div className="space-y-4 max-w-6xl">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-slate-900">Editing: {document.title}</h1>
            <div className="flex items-center gap-4">
              <a href={`/documents/${id}`} className="text-sm text-indigo-600 hover:underline">
                Back
              </a>
              <button
                onClick={() => finishEditSession()}
                className="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
              >
                Done editing
              </button>
            </div>
          </div>

          <div className="bg-indigo-50 border border-indigo-200 rounded p-3 space-y-2">
            <label htmlFor="ai-instruction" className="block text-sm font-medium text-slate-700">
              AI Instruction
            </label>
            <div className="flex gap-2">
              <input
                id="ai-instruction"
                type="text"
                value={aiInstruction}
                onChange={(e) => setAiInstruction(e.target.value)}
                className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. make this more concise"
              />
              <button
                type="button"
                onClick={handleRequestRevision}
                disabled={aiStatus === "loading"}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
              >
                {aiStatus === "loading" ? "Revising…" : "Ask AI to revise"}
              </button>
            </div>
          </div>

          <AiSuggestionPanel
            suggestion={aiSuggestion}
            status={aiStatus}
            errorMessage={aiError ?? undefined}
            onAccept={handleAcceptSuggestion}
            onDiscard={handleDiscardSuggestion}
            onRefine={handleRefineSuggestion}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white rounded border p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
                  Markdown Source
                </h2>
                {saveStatusLabel && (
                  <span
                    role={saveStatus === "error" ? "alert" : undefined}
                    className={`text-xs px-2 py-0.5 rounded ${
                      saveStatus === "error"
                        ? "text-red-600 bg-red-50 border border-red-200"
                        : "text-slate-500"
                    }`}
                  >
                    {saveStatusLabel}
                  </span>
                )}
              </div>
              <textarea
                ref={textareaRef}
                aria-label="Markdown source"
                value={content}
                onChange={(e) => handleContentChange(e.target.value)}
                className="w-full h-[60vh] font-mono text-sm border border-slate-200 rounded p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                spellCheck={false}
              />
            </div>
            <div className="bg-white rounded border p-4">
              <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-2">
                Preview
              </h2>
              <DocumentContent version={{ content_markdown: content } as DocumentVersion} />
            </div>
          </div>
        </div>
      )}
    </AuthGuard>
  );
}
