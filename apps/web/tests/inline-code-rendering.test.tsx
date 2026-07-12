import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import React from "react";

import MessageBubble from "@/components/chat/MessageBubble";
import { DocumentContent } from "@/components/documents/DocumentContent";
import type { ChatTurn, DocumentVersion } from "@/lib/types";

function completeTurn(answer: string): ChatTurn {
  return {
    id: "turn-1",
    question: "A question?",
    status: "complete",
    answer: {
      answer,
      confidence: 0.9,
      dont_know: false,
      citations: [],
    },
  };
}

function version(content_markdown: string): DocumentVersion {
  return {
    id: "v-1",
    document_id: "doc-1",
    version_number: 1,
    content_markdown,
    frontmatter: {},
    approver_user_id: null,
    approved_at: null,
    created_from_proposal_id: null,
    created_at: "2026-07-11T00:00:00Z",
  };
}

function renderChat(answer: string) {
  return render(<MessageBubble turn={completeTurn(answer)} />).container;
}

function renderDocument(content_markdown: string) {
  return render(<DocumentContent version={version(content_markdown)} />).container;
}

function readGlobalsCss(): string {
  const candidates = [
    resolve(process.cwd(), "apps/web/app/globals.css"),
    resolve(process.cwd(), "app/globals.css"),
  ];
  const cssPath = candidates.find(existsSync);
  if (!cssPath) throw new Error(`globals.css not found in: ${candidates.join(", ")}`);
  return readFileSync(cssPath, "utf8");
}

const normalizedCss = readGlobalsCss().replace(/\s+/g, " ");

describe("globals.css — CSS contract: typography backtick override", () => {
  it("sets content: none on .prose code::before", () => {
    expect(normalizedCss).toMatch(/\.prose code::before[^{}]*\{[^}]*content:\s*none/);
  });

  it("sets content: none on .prose code::after", () => {
    expect(normalizedCss).toMatch(/\.prose code::after[^{}]*\{[^}]*content:\s*none/);
  });

  it("gives inline code (not code blocks) a background pill", () => {
    expect(normalizedCss).toMatch(/\.prose :not\(pre\) > code[^{}]*\{[^}]*background-color/);
  });

  it("defines --font-mono as a real monospace stack (Geist is not loaded)", () => {
    expect(normalizedCss).toMatch(/--font-mono:[^;]*monospace/);
    expect(normalizedCss).not.toMatch(/--font-mono:[^;]*geist/i);
  });
});

describe("US1 — inline code displays without backtick symbols (markup layer)", () => {
  it("chat: inline code renders as a <code> element outside <pre>, no backtick in the bubble text", () => {
    const container = renderChat("Run `main` now");

    const code = container.querySelector("code");
    expect(code).toHaveTextContent("main");
    expect(code?.closest("pre")).toBeNull();
    expect(container.textContent).not.toContain("`");
  });

  it("document viewer: inline code renders as a <code> element outside <pre>, no backtick in the text", () => {
    const container = renderDocument("Deploy from the `main` branch.");

    const code = container.querySelector("code");
    expect(code).toHaveTextContent("main");
    expect(code?.closest("pre")).toBeNull();
    expect(container.textContent).not.toContain("`");
  });

  it("renders three inline snippets in one sentence as three <code> elements with prose intact", () => {
    const container = renderChat("Use `git add`, then `git commit`, then `git push` to publish.");

    const codes = container.querySelectorAll("code");
    expect(codes).toHaveLength(3);
    expect(codes[0]).toHaveTextContent("git add");
    expect(codes[1]).toHaveTextContent("git commit");
    expect(codes[2]).toHaveTextContent("git push");
    expect(container.textContent).not.toContain("`");
    expect(container.textContent).toContain("to publish.");
  });
});

describe("US2 — inline code remains visually distinct (nested contexts)", () => {
  const nested = [
    "# The `deploy` heading",
    "",
    "This is **bold with `inline` code** in prose.",
    "",
    "- Run `npm test` first",
    "",
    "| Command | Purpose |",
    "| --- | --- |",
    "| `make build` | Build |",
  ].join("\n");

  it.each([
    ["chat", renderChat],
    ["document viewer", renderDocument],
  ])("%s: snippets nested in heading, bold, list item, and table cell render as <code>", (_surface, renderSurface) => {
    const container = renderSurface(nested);

    expect(container.querySelector("h1 code")).toHaveTextContent("deploy");
    expect(container.querySelector("strong code")).toHaveTextContent("inline");
    expect(container.querySelector("li code")).toHaveTextContent("npm test");
    expect(container.querySelector("td code")).toHaveTextContent("make build");
    expect(container.textContent).not.toContain("`");
  });

  it("globals.css still defines --tw-prose-code (code styling untouched by the fix)", () => {
    expect(normalizedCss).toContain("--tw-prose-code:");
  });
});

describe("US3 — intentional backticks are preserved", () => {
  const fencedBlock = ["```text", "Literal backticks stay: `example`", "```"].join("\n");
  const lonePr = "A lone backtick ` in prose stays visible.";

  it.each([
    ["chat", renderChat],
    ["document viewer", renderDocument],
  ])("%s: backticks inside a fenced code block remain visible verbatim", (_surface, renderSurface) => {
    const container = renderSurface(fencedBlock);

    const block = container.querySelector("pre code");
    expect(block?.textContent).toContain("`example`");
  });

  it.each([
    ["chat", renderChat],
    ["document viewer", renderDocument],
  ])("%s: a single unpaired backtick in prose stays visible as typed", (_surface, renderSurface) => {
    const container = renderSurface(lonePr);

    expect(container.textContent).toContain("A lone backtick ` in prose stays visible.");
  });

  it("whitespace-only inline code produces no stray symbols", () => {
    const container = renderChat("Before ` ` after.");

    const code = container.querySelector("code");
    if (code) {
      expect(code.textContent?.trim()).toBe("");
    }
    expect(container.textContent).toContain("Before");
    expect(container.textContent).toContain("after.");
    expect(container.textContent).not.toContain("`");
  });
});
