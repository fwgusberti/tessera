import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", email: "t@t.com", isAdmin: false },
    accessToken: "tok",
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as { post: ReturnType<typeof vi.fn> };

import SearchPage from "../app/search/page";

function makeResult(overrides: Record<string, unknown> = {}) {
  return {
    document_id: "doc-1",
    version_id: "ver-1",
    chunk_id: "chunk-1",
    score: 0.87,
    snippet: "Plain excerpt text",
    citation: { document_title: "Getting Started" },
    ...overrides,
  };
}

async function searchWithResults(results: unknown[]) {
  mockApi.post.mockResolvedValueOnce({ results });
  const utils = render(<SearchPage />);
  const input = screen.getByPlaceholderText(/search documentation/i);
  fireEvent.change(input, { target: { value: "query" } });
  fireEvent.keyDown(input, { key: "Enter" });
  await waitFor(() => {
    expect(mockApi.post).toHaveBeenCalled();
  });
  return utils;
}

describe("SearchPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("does not show 'No results found' before any search is submitted", () => {
    render(<SearchPage />);
    expect(screen.queryByText(/no results found/i)).toBeNull();
  });

  it("shows 'No results found' message after a search returns an empty results array", async () => {
    mockApi.post.mockResolvedValueOnce({ results: [] });

    render(<SearchPage />);

    const input = screen.getByPlaceholderText(/search documentation/i);
    fireEvent.change(input, { target: { value: "nomatch" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(screen.getByText(/no results found/i)).toBeTruthy();
    });
  });
});

describe("SearchPage — formatted result cards (US1)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders the document title at the top of the card, more prominent than the excerpt (FR-001)", async () => {
    await searchWithResults([
      makeResult({
        snippet: "Excerpt body text",
        citation: { document_title: "Getting Started" },
      }),
    ]);

    const title = await screen.findByText("Getting Started");
    expect(title.className).toContain("font-semibold");

    const excerpt = screen.getByText("Excerpt body text");
    // Title must precede the excerpt in document order (title on top)
    expect(
      title.compareDocumentPosition(excerpt) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("falls back to 'Untitled document' when the title is missing (FR-008)", async () => {
    await searchWithResults([makeResult({ citation: {} })]);

    expect(await screen.findByText("Untitled document")).toBeTruthy();
  });

  it("falls back to 'Untitled document' when the title is empty/whitespace (FR-008)", async () => {
    await searchWithResults([
      makeResult({ citation: { document_title: "   " } }),
    ]);

    expect(await screen.findByText("Untitled document")).toBeTruthy();
  });

  it("renders **bold** markdown as a <strong> element with no literal asterisks (FR-002)", async () => {
    const { container } = await searchWithResults([
      makeResult({ snippet: "This is **very important** information" }),
    ]);

    await screen.findByText("Getting Started");
    const strong = container.querySelector("strong");
    expect(strong).toBeTruthy();
    expect(strong!.textContent).toBe("very important");
    expect(screen.queryByText(/\*\*/)).toBeNull();
  });

  it("renders headings at compact card scale, not as a default page-scale <h1> (FR-005)", async () => {
    const { container } = await searchWithResults([
      makeResult({ snippet: "# Setup Guide\n\nInstall the dependencies." }),
    ]);

    const heading = await screen.findByText("Setup Guide");
    // Compact override applied: no default h1..h6 elements inside the card
    expect(container.querySelector("h1, h2, h3, h4, h5, h6")).toBeNull();
    expect(heading.className).toContain("text-sm");
    expect(heading.className).toContain("font-semibold");
  });

  it("never mounts embedded HTML — script/img appear only as escaped text (FR-003)", async () => {
    const { container } = await searchWithResults([
      makeResult({
        snippet:
          'Before <script>alert(1)</script> and <img src=x onerror="alert(2)"> after',
      }),
    ]);

    await screen.findByText("Getting Started");
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });

  it("keeps the relevance score visible as a percentage (FR-009)", async () => {
    await searchWithResults([makeResult({ score: 0.87 })]);

    await screen.findByText("Getting Started");
    expect(screen.getByText(/87\s*%/)).toBeTruthy();
  });
});

describe("SearchPage — result card navigation (US2)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("navigates to /documents/{document_id} when the card is clicked anywhere (FR-006)", async () => {
    await searchWithResults([
      makeResult({ document_id: "doc-42", snippet: "Excerpt body text" }),
    ]);

    const excerpt = await screen.findByText("Excerpt body text");
    fireEvent.click(excerpt);

    expect(pushMock).toHaveBeenCalledWith("/documents/doc-42");
  });

  it("navigates on Enter when the card is focused (FR-006)", async () => {
    await searchWithResults([makeResult({ document_id: "doc-42" })]);

    const card = await screen.findByRole("link");
    fireEvent.keyDown(card, { key: "Enter" });

    expect(pushMock).toHaveBeenCalledWith("/documents/doc-42");
  });

  it("navigates on Space when the card is focused (FR-006)", async () => {
    await searchWithResults([makeResult({ document_id: "doc-42" })]);

    const card = await screen.findByRole("link");
    fireEvent.keyDown(card, { key: " " });

    expect(pushMock).toHaveBeenCalledWith("/documents/doc-42");
  });

  it("exposes role=link, tabIndex=0 and a pointer/hover affordance (FR-007)", async () => {
    await searchWithResults([makeResult()]);

    const card = await screen.findByRole("link");
    expect(card.getAttribute("tabindex")).toBe("0");
    expect(card.className).toContain("cursor-pointer");
    expect(card.className).toMatch(/hover:/);
  });

  it("renders markdown links in the excerpt as non-anchor text; clicking them navigates to the document (R3)", async () => {
    await searchWithResults([
      makeResult({
        document_id: "doc-42",
        snippet: "See [the docs](https://example.com) for details",
      }),
    ]);

    const linkText = await screen.findByText("the docs");
    const card = screen.getByRole("link");
    expect(card.querySelector("a")).toBeNull();

    fireEvent.click(linkText);
    expect(pushMock).toHaveBeenCalledWith("/documents/doc-42");
    expect(pushMock).not.toHaveBeenCalledWith("https://example.com");
  });
});
