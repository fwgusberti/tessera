"use client";

import type { Document } from "@/lib/types";

interface DocumentTileProps {
  document: Document;
}

const STATE_STYLES: Record<Document["state"], string> = {
  ingested: "bg-slate-100 text-slate-700",
  published: "bg-green-100 text-green-700",
  archived: "bg-amber-100 text-amber-700",
};

export function DocumentTile({ document }: DocumentTileProps) {
  return (
    <article className="bg-white rounded border border-slate-200 p-4 hover:border-indigo-300 hover:shadow-sm transition">
      <a href={`/documents/${document.id}`} className="min-w-0 flex-1 flex items-start gap-2 group">
        <svg
          className="w-8 h-8 text-slate-400 flex-shrink-0"
          fill="currentColor"
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M4 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0013.414 6L10 2.586A2 2 0 008.586 2H4zm6 1.414L11.586 5H10V3.414z"
            clipRule="evenodd"
          />
        </svg>
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-slate-900 truncate group-hover:text-indigo-600">
            {document.title}
          </h2>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-1 ${STATE_STYLES[document.state]}`}
          >
            {document.state}
          </span>
        </div>
      </a>
    </article>
  );
}
