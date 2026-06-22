"use client";

import { useCallback, useRef, useState } from "react";
import { askAssistant } from "@/lib/chat";
import type { ChatTurn, HistoryMessage } from "@/lib/types";
import { generateId } from "@/lib/utils/generate-id";
import MessageBubble from "./MessageBubble";

const STARTER_PROMPTS = [
  "What's in our product roadmap?",
  "Summarize the latest meeting notes",
  "Find our onboarding documentation",
  "What changed in the last release?",
] as const;

export default function ChatInterface() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const isSubmittable = input.trim().length > 0;

  const deriveHistory = (completedTurns: ChatTurn[]): HistoryMessage[] =>
    completedTurns
      .filter((t) => t.status === "complete" && t.answer?.answer != null)
      .flatMap((t) => [
        { role: "user" as const, content: t.question },
        { role: "assistant" as const, content: t.answer!.answer! },
      ]);

  const handleSubmit = useCallback(async () => {
    if (!isSubmittable) return;

    const question = input.trim();
    const turnId = generateId();
    const history = deriveHistory(turns);

    setInput("");

    const pendingTurn: ChatTurn = {
      id: turnId,
      question,
      answer: null,
      status: "pending",
    };

    setTurns((prev) => [...prev, pendingTurn]);

    try {
      const answer = await askAssistant(question, history);
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId ? { ...t, status: "complete", answer } : t,
        ),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId ? { ...t, status: "error", errorMessage: message } : t,
        ),
      );
      setInput(question);
    }
  }, [input, isSubmittable, turns]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleNewConversation = () => {
    setTurns([]);
    setInput("");
    inputRef.current?.focus();
  };

  const inputBar = (
    <div className="flex gap-2 items-end">
      <textarea
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your question…"
        rows={1}
        className="flex-1 resize-none rounded border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent overflow-hidden"
        style={{ minHeight: "2.5rem" }}
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!isSubmittable}
        className="shrink-0 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Ask
      </button>
    </div>
  );

  if (turns.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-4 gap-8">
        <div className="flex flex-col items-center gap-2">
          <h1 className="text-4xl font-bold text-slate-900">Tessera</h1>
          <p className="text-lg text-slate-500">Your knowledge, always answered.</p>
        </div>

        <div className="max-w-2xl w-full">{inputBar}</div>

        <div className="flex flex-wrap gap-2 justify-center max-w-2xl w-full">
          {STARTER_PROMPTS.map((label) => (
            <button
              key={label}
              type="button"
              onClick={() => {
                setInput(label);
                inputRef.current?.focus();
              }}
              className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:border-indigo-400 hover:text-indigo-600 transition-colors bg-white"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <span className="text-xl font-semibold text-slate-900">Tessera</span>
        <button
          type="button"
          onClick={handleNewConversation}
          className="text-sm text-slate-500 hover:text-indigo-600 transition-colors"
        >
          New conversation
        </button>
      </div>

      {/* Scrollable message history */}
      <div className="flex-1 flex flex-col gap-4 px-4 py-4 max-w-3xl mx-auto w-full">
        {turns.map((turn) => (
          <MessageBubble key={turn.id} turn={turn} />
        ))}
      </div>

      {/* Sticky input bar */}
      <div className="sticky bottom-0 bg-white border-t border-slate-200 py-4">
        <div className="max-w-3xl mx-auto px-4">{inputBar}</div>
      </div>
    </div>
  );
}
