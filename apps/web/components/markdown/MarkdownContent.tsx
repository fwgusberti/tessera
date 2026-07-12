"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
  className?: string;
  openLinksInNewTab?: boolean;
  components?: Components;
}

export default function MarkdownContent({
  content,
  className,
  openLinksInNewTab = false,
  components,
}: MarkdownContentProps) {
  const baseComponents: Components | undefined = openLinksInNewTab
    ? {
        a: ({ children, ...props }) => (
          <a {...props} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        ),
      }
    : undefined;

  const mergedComponents =
    baseComponents || components
      ? { ...baseComponents, ...components }
      : undefined;

  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={mergedComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
