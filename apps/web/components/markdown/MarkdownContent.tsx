"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
  className?: string;
  openLinksInNewTab?: boolean;
}

export default function MarkdownContent({
  content,
  className,
  openLinksInNewTab = false,
}: MarkdownContentProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={
          openLinksInNewTab
            ? {
                a: ({ children, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
              }
            : undefined
        }
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
