"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { DocumentVersion } from "@/lib/types";

interface DocumentContentProps {
  version: DocumentVersion | null;
}

export function DocumentContent({ version }: DocumentContentProps) {
  if (!version) {
    return <p className="text-sm text-slate-400 italic">No content available for this document.</p>;
  }

  return (
    <div className="prose prose-slate max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{version.content_markdown}</ReactMarkdown>
    </div>
  );
}
