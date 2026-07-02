import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "editor@t.com", isAdmin: false }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "d1" }),
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
};

const mockDocument = {
  id: "d1", space_id: "s1", title: "API Reference", language: "en",
  confidentiality: "internal" as const, tags: [], state: "ingested" as const,
  current_version_id: "v1", owner_user_id: "u1",
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
};

const mockVersion = {
  id: "v1", document_id: "d1", version_number: 1,
  content_markdown: "# Doc\n\nContent.", frontmatter: {},
  approver_user_id: null, approved_at: null,
  created_from_proposal_id: null, created_at: "2026-01-01T00:00:00Z",
};

const editorMembership = { membership: { space_id: "s1", user_id: "u1", role: "editor" as const, created_at: "2026-01-01T00:00:00Z" } };
const viewerMembership = { membership: { space_id: "s1", user_id: "u2", role: "viewer" as const, created_at: "2026-01-01T00:00:00Z" } };

function setupDocumentMocks(membershipResponse: typeof editorMembership | typeof viewerMembership = editorMembership) {
  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/documents/d1") return Promise.resolve({ document: mockDocument, current_version: mockVersion });
    if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: [mockVersion] });
    if (path === "/v1/documents/d1/draft") return Promise.resolve({ draft: null });
    if (path === "/v1/spaces/s1/members/me") return Promise.resolve(membershipResponse);
    return Promise.resolve({});
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

// ─── User Story 1: split view + live preview ─────────────────────────────────

describe("Document edit page — split view", () => {
  it("renders a textarea seeded with current content and a rendered preview", async () => {
    setupDocumentMocks(editorMembership);
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    expect((textarea as HTMLTextAreaElement).value).toBe(mockVersion.content_markdown);
    expect(screen.getByRole("heading", { name: "Doc" })).toBeInTheDocument();
  });

  it("updates the preview pane synchronously when the textarea content changes", async () => {
    setupDocumentMocks(editorMembership);
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    fireEvent.change(textarea, { target: { value: "## New Heading\n\nUpdated." } });

    expect(screen.getByRole("heading", { name: "New Heading" })).toBeInTheDocument();
    expect(mockApi.put).not.toHaveBeenCalled();
  });

  it("renders GFM elements in the preview without unescaped raw HTML", async () => {
    setupDocumentMocks(editorMembership);
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    const gfmContent = [
      "| A | B |",
      "| - | - |",
      "| 1 | 2 |",
      "",
      "- item one",
      "- item two",
      "",
      "```js",
      "const x = 1;",
      "```",
      "",
      '<script>window.__pwned = true;</script>',
    ].join("\n");
    fireEvent.change(textarea, { target: { value: gfmContent } });

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("item one")).toBeInTheDocument();
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
    expect(document.querySelector("script")).not.toBeInTheDocument();
  });
});

describe("Document edit — access gating", () => {
  it("does not render an Edit link on the detail page for a VIEWER-role user", async () => {
    setupDocumentMocks(viewerMembership);
    const { default: DocumentDetailPage } = await import("@/app/documents/[id]/page");
    render(<DocumentDetailPage />);

    await waitFor(() => expect(screen.getByText("API Reference")).toBeInTheDocument());
    expect(screen.queryByRole("link", { name: /^edit$/i })).not.toBeInTheDocument();
  });

  it("redirects away from the edit route for a VIEWER-role user instead of rendering the editor", async () => {
    setupDocumentMocks(viewerMembership);
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/documents/d1"));
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});

// ─── User Story 2: autosave protection ───────────────────────────────────────

describe("Document edit page — autosave", () => {
  it("fires a debounced PUT /draft call with the latest content after ~4s, not before", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.put.mockResolvedValue({
      draft: { content_markdown: "edited content", editor_user_id: "u1", started_at: "2026-01-01T00:00:00Z", last_autosaved_at: "2026-01-01T00:00:00Z" },
    });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");

    vi.useFakeTimers();
    fireEvent.change(textarea, { target: { value: "edited content" } });

    act(() => vi.advanceTimersByTime(3999));
    expect(mockApi.put).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(1));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(mockApi.put).toHaveBeenCalledWith("/v1/documents/d1/draft", { content_markdown: "edited content" });
  });

  it("seeds the textarea from an existing draft instead of the current version", async () => {
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1") return Promise.resolve({ document: mockDocument, current_version: mockVersion });
      if (path === "/v1/documents/d1/versions") return Promise.resolve({ versions: [mockVersion] });
      if (path === "/v1/documents/d1/draft") {
        return Promise.resolve({
          draft: {
            content_markdown: "resumed draft content",
            editor_user_id: "u1",
            started_at: "2026-01-01T00:00:00Z",
            last_autosaved_at: "2026-01-01T00:05:00Z",
          },
        });
      }
      if (path === "/v1/spaces/s1/members/me") return Promise.resolve(editorMembership);
      return Promise.resolve({});
    });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    await waitFor(() => expect((textarea as HTMLTextAreaElement).value).toBe("resumed draft content"));
  });

  it("shows a save-failed warning and leaves textarea content unchanged when autosave fails", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.put.mockRejectedValue(new Error("Network error"));
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    vi.useFakeTimers();
    fireEvent.change(textarea, { target: { value: "content that fails to save" } });

    act(() => vi.advanceTimersByTime(4000));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText(/save failed/i)).toBeInTheDocument();
    expect((textarea as HTMLTextAreaElement).value).toBe("content that fails to save");
  });
});

// ─── User Story 3: finalizing the session creates a version ─────────────────

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000;

describe("Document edit page — session finalization", () => {
  it('finalizes the draft and navigates back to the document on "Done editing"', async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockResolvedValue({ version: { ...mockVersion, content_markdown: "edited" } });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    await screen.findByRole("textbox");
    fireEvent.click(screen.getByRole("button", { name: /done editing/i }));

    await waitFor(() => expect(mockApi.post).toHaveBeenCalledWith("/v1/documents/d1/draft/finish", {}));
    await waitFor(() => expect(mockPush.mock.calls[0]?.[0]).toMatch(/^\/documents\/d1/));
  });

  it("flushes the latest unsaved content before finalizing, so a fast Done-editing click doesn't finalize stale content", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.put.mockResolvedValue({
      draft: { content_markdown: "last-second edit", editor_user_id: "u1", started_at: "2026-01-01T00:00:00Z", last_autosaved_at: "2026-01-01T00:00:00Z" },
    });
    mockApi.post.mockResolvedValue({ version: null });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    fireEvent.change(textarea, { target: { value: "last-second edit" } });
    // click "Done editing" immediately — well within the autosave debounce window
    fireEvent.click(screen.getByRole("button", { name: /done editing/i }));

    await waitFor(() => expect(mockApi.post).toHaveBeenCalledWith("/v1/documents/d1/draft/finish", {}));
    expect(mockApi.put).toHaveBeenCalledWith("/v1/documents/d1/draft", { content_markdown: "last-second edit" });
    expect(mockApi.put.mock.invocationCallOrder[0]).toBeLessThan(mockApi.post.mock.invocationCallOrder[0]);
  });

  it("fires a keepalive fetch to the finish endpoint on pagehide when there is unfinalized content", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.put.mockResolvedValue({
      draft: { content_markdown: "unsaved edit", editor_user_id: "u1", started_at: "2026-01-01T00:00:00Z", last_autosaved_at: "2026-01-01T00:00:00Z" },
    });
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 200 }));
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    fireEvent.change(textarea, { target: { value: "unsaved edit" } });

    act(() => {
      window.dispatchEvent(new Event("pagehide"));
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/documents/d1/draft/finish"),
      expect.objectContaining({ method: "POST", keepalive: true }),
    );
    fetchSpy.mockRestore();
  });

  it("finishes and redirects automatically after the inactivity threshold, resetting the timer on keystrokes", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockResolvedValue({ version: null });
    mockApi.put.mockResolvedValue({
      draft: { content_markdown: "typing more", editor_user_id: "u1", started_at: "2026-01-01T00:00:00Z", last_autosaved_at: "2026-01-01T00:00:00Z" },
    });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = await screen.findByRole("textbox");
    vi.useFakeTimers();
    fireEvent.change(textarea, { target: { value: "typing" } });

    act(() => vi.advanceTimersByTime(INACTIVITY_TIMEOUT_MS - 1000));
    fireEvent.change(textarea, { target: { value: "typing more" } });
    act(() => vi.advanceTimersByTime(INACTIVITY_TIMEOUT_MS - 1000));
    expect(mockApi.post).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(1000));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(mockApi.post).toHaveBeenCalledWith("/v1/documents/d1/draft/finish", {});
    expect(mockPush.mock.calls[0]?.[0]).toMatch(/^\/documents\/d1/);
  });
});
