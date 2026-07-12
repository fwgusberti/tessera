"use client";

import MarkdownContent from "@/components/markdown/MarkdownContent";
import type { DocumentVersion } from "@/lib/types";

interface DocumentContentProps {
  version: DocumentVersion | null;
}

export function DocumentContent({ version }: DocumentContentProps) {
  if (!version) {
    return <p className="text-sm text-slate-400 italic">No content available for this document.</p>;
  }

  return <MarkdownContent content={version.content_markdown} className="prose prose-slate max-w-none" />;
}
