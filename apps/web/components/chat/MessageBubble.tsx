"use client";

import MarkdownContent from "@/components/markdown/MarkdownContent";
import type { ChatTurn } from "@/lib/types";

interface MessageBubbleProps {
  turn: ChatTurn;
}

export default function MessageBubble({ turn }: MessageBubbleProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* User question */}
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-indigo-600 text-white rounded-lg px-4 py-2 text-sm">
          <p>{turn.question}</p>
        </div>
      </div>

      {/* Assistant response */}
      <div className="flex justify-start">
        <div className="max-w-[85%] bg-slate-100 text-slate-900 rounded-lg px-4 py-2 text-sm">
          {turn.status === "pending" && (
            <span role="status" aria-label="Loading" className="flex items-center gap-2 text-slate-500">
              <span className="animate-spin inline-block w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full" />
              Thinking…
            </span>
          )}

          {turn.status === "error" && (
            <p className="text-red-600">{turn.errorMessage ?? "Something went wrong. Please try again."}</p>
          )}

          {turn.status === "complete" && turn.answer && (
            <>
              {turn.answer.dont_know ? (
                <p className="text-slate-500 italic">
                  I don&apos;t have enough information to answer that.
                  {turn.answer.suggested_owner && (
                    <> Try checking the <strong>{turn.answer.suggested_owner.space_name}</strong> space.</>
                  )}
                </p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <MarkdownContent
                      content={turn.answer.answer ?? ""}
                      className="prose prose-sm prose-slate max-w-none break-words"
                      openLinksInNewTab
                    />
                  </div>
                  {turn.answer.citations && turn.answer.citations.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-slate-400 mt-2">Sources</p>
                      <div className="flex flex-col gap-1">
                        {turn.answer.citations.map((c) => (
                          <a
                            key={c.chunk_id}
                            href={`/documents/${c.document_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-indigo-600 hover:underline"
                          >
                            {c.quote.slice(0, 80)}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
