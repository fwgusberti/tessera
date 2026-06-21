"use client";

import { useCallback, useRef, useState } from "react";
import { askAssistant } from "@/lib/chat";
import type { ChatTurn, HistoryMessage } from "@/lib/types";
import MessageBubble from "./MessageBubble";

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
    const turnId = crypto.randomUUID();
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

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Ask Tessera</h2>
        {turns.length > 0 && (
          <button
            type="button"
            onClick={handleNewConversation}
            className="text-sm text-slate-500 hover:text-indigo-600 transition-colors"
          >
            New conversation
          </button>
        )}
      </div>

      {/* Conversation area */}
      <div className="flex flex-col gap-4 min-h-[120px]">
        {turns.length === 0 ? (
          <p className="text-slate-400 text-sm">Ask a question to get started.</p>
        ) : (
          turns.map((turn) => <MessageBubble key={turn.id} turn={turn} />)
        )}
      </div>

      {/* Input row */}
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
    </div>
  );
}
