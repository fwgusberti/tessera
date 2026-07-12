import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import React from "react";

import MarkdownContent from "@/components/markdown/MarkdownContent";
import MessageBubble from "@/components/chat/MessageBubble";
import type { ChatTurn } from "@/lib/types";

function completeTurn(answer: string, extra?: Partial<NonNullable<ChatTurn["answer"]>>): ChatTurn {
  return {
    id: "turn-1",
    question: "A question?",
    status: "complete",
    answer: {
      answer,
      confidence: 0.9,
      dont_know: false,
      citations: [],
      ...extra,
    },
  };
}

describe("MarkdownContent — C1: shared markdown renderer", () => {
  it("renders GFM markdown as elements: headings, bold, lists, tables, code", () => {
    const content = [
      "# Title",
      "",
      "Some **bold** text.",
      "",
      "- first item",
      "- second item",
      "",
      "| Col A | Col B |",
      "| ----- | ----- |",
      "| a1    | b1    |",
      "",
      "```",
      "const x = 1;",
      "```",
    ].join("\n");

    const { container } = render(<MarkdownContent content={content} />);

    expect(screen.getByRole("heading", { name: "Title" })).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("bold");
    expect(container.querySelectorAll("li")).toHaveLength(2);
    expect(container.querySelector("table")).toBeInTheDocument();
    expect(container.querySelector("pre code")).toHaveTextContent("const x = 1;");
  });

  it("applies className to the wrapper", () => {
    const { container } = render(
      <MarkdownContent content="hello" className="prose prose-slate max-w-none" />,
    );
    const wrapper = container.firstElementChild;
    expect(wrapper).toHaveClass("prose", "prose-slate", "max-w-none");
  });

  it("adds no target to links by default (openLinksInNewTab defaults to false)", () => {
    const { container } = render(
      <MarkdownContent content="[a link](https://example.com)" />,
    );
    const link = container.querySelector("a");
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).not.toHaveAttribute("target");
  });

  it("adds target=_blank and rel=noopener noreferrer on every link when openLinksInNewTab is true", () => {
    const content = "[one](https://example.com/1) and [two](https://example.com/2)";
    const { container } = render(
      <MarkdownContent content={content} openLinksInNewTab />,
    );
    const links = container.querySelectorAll("a");
    expect(links).toHaveLength(2);
    links.forEach((link) => {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });
  });

  it("never renders or executes embedded script tags (FR-004)", () => {
    (globalThis as Record<string, unknown>).__xssExecuted = false;
    const { container } = render(
      <MarkdownContent content={'<script>globalThis.__xssExecuted = true;</script>alert(1)'} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect((globalThis as Record<string, unknown>).__xssExecuted).toBe(false);
    delete (globalThis as Record<string, unknown>).__xssExecuted;
  });

  it("renders malformed markdown legibly as text without throwing", () => {
    expect(() =>
      render(<MarkdownContent content="an **unclosed bold marker" />),
    ).not.toThrow();
    expect(screen.getByText(/unclosed bold marker/)).toBeInTheDocument();
  });
});

describe("MessageBubble — US1: read a formatted chat answer", () => {
  it("renders headings, bold, and lists as elements with no literal markers visible", () => {
    const answer = ["# Vacation Policy", "", "You get **20 days** per year:", "", "- Paid leave", "- Sick leave"].join(
      "\n",
    );
    const { container } = render(<MessageBubble turn={completeTurn(answer)} />);

    expect(screen.getByRole("heading", { name: "Vacation Policy" })).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("20 days");
    expect(container.querySelectorAll("li")).toHaveLength(2);

    const bubbleText = container.textContent ?? "";
    expect(bubbleText).not.toContain("#");
    expect(bubbleText).not.toContain("**");
    expect(bubbleText).not.toContain("- ");
  });

  it("renders a plain-prose answer as normal paragraphs", () => {
    const answer = "First paragraph of prose.\n\nSecond paragraph of prose.";
    const { container } = render(<MessageBubble turn={completeTurn(answer)} />);

    const paragraphs = Array.from(container.querySelectorAll("p")).filter((p) =>
      p.textContent?.includes("paragraph of prose"),
    );
    expect(paragraphs).toHaveLength(2);
    expect(paragraphs[0]).toHaveTextContent("First paragraph of prose.");
    expect(paragraphs[1]).toHaveTextContent("Second paragraph of prose.");
  });

  it("renders answer links with target=_blank and rel=noopener noreferrer", () => {
    const { container } = render(
      <MessageBubble turn={completeTurn("See [the handbook](https://example.com/handbook).")} />,
    );
    const link = Array.from(container.querySelectorAll("a")).find(
      (a) => a.getAttribute("href") === "https://example.com/handbook",
    );
    expect(link).toBeDefined();
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});

describe("MessageBubble — US2: formatting parity and containment", () => {
  it("renders a GFM table in the answer as table rows and columns", () => {
    const answer = ["| Plan | Days |", "| ---- | ---- |", "| Basic | 10 |", "| Full | 20 |"].join("\n");
    const { container } = render(<MessageBubble turn={completeTurn(answer)} />);

    const table = container.querySelector("table");
    expect(table).toBeInTheDocument();
    expect(table?.querySelectorAll("tr")).toHaveLength(3);
    expect(table?.querySelectorAll("th")).toHaveLength(2);
    expect(screen.getByText("Basic")).toBeInTheDocument();
  });

  it("renders a fenced code block as pre > code", () => {
    const answer = ["Run this:", "", "```", "npm install", "```"].join("\n");
    const { container } = render(<MessageBubble turn={completeTurn(answer)} />);
    expect(container.querySelector("pre code")).toHaveTextContent("npm install");
  });

  it("wraps the rendered answer body in an overflow-x-auto container", () => {
    const { container } = render(<MessageBubble turn={completeTurn("# Heading")} />);
    const heading = container.querySelector("h1");
    expect(heading?.closest(".overflow-x-auto")).not.toBeNull();
  });

  it("keeps literal markdown syntax quoted inside a code block visible as text", () => {
    const answer = ["```", "# not a heading", "**not bold**", "```"].join("\n");
    const { container } = render(<MessageBubble turn={completeTurn(answer)} />);

    expect(container.querySelector("h1")).toBeNull();
    expect(container.querySelector("strong")).toBeNull();
    const code = container.querySelector("pre code");
    expect(code?.textContent).toContain("# not a heading");
    expect(code?.textContent).toContain("**not bold**");
  });
});

describe("MessageBubble — US3: citations preserved below formatted answers", () => {
  it("renders the citations list below the formatted answer with unchanged link behavior", () => {
    const turn = completeTurn("The policy grants **20 days**.", {
      citations: [
        {
          chunk_id: "ch-1",
          document_id: "doc-1",
          document_version_id: "v-1",
          quote: "Employees receive 20 days of paid leave per year.",
          score: 0.95,
        },
      ],
    });
    const { container } = render(<MessageBubble turn={turn} />);

    expect(container.querySelector("strong")).toHaveTextContent("20 days");
    expect(screen.getByText("Sources")).toBeInTheDocument();

    const citation = screen.getByRole("link", { name: /Employees receive 20 days/ });
    expect(citation).toHaveAttribute("href", "/documents/doc-1");
    expect(citation).toHaveAttribute("target", "_blank");
    expect(citation).toHaveAttribute("rel", "noopener noreferrer");

    const answerEl = container.querySelector("strong") as HTMLElement;
    expect(
      answerEl.compareDocumentPosition(citation) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
