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
  content_markdown: "# Doc\n\nOriginal content.", frontmatter: {},
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

describe("Document edit page — AI revision", () => {
  it("shows an Ask AI to revise control for an EDITOR-role user", async () => {
    setupDocumentMocks(editorMembership);
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    await screen.findByRole("textbox", { name: /markdown source/i });
    expect(screen.getByRole("button", { name: /ask ai to revise/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/ai instruction/i)).toBeInTheDocument();
  });

  it("sends the entire content when nothing is selected", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockResolvedValue({ suggestion: "Revised whole doc." });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    await screen.findByRole("textbox", { name: /markdown source/i });
    fireEvent.change(screen.getByLabelText(/ai instruction/i), { target: { value: "make this more concise" } });
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith("/v1/documents/d1/assist/revise", {
        content: mockVersion.content_markdown,
        instruction: "make this more concise",
        previous_suggestion: undefined,
      });
    });
  });

  it("sends only the selected substring when text is selected", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockResolvedValue({ suggestion: "Revised selection." });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = (await screen.findByRole("textbox", { name: /markdown source/i })) as HTMLTextAreaElement;
    textarea.setSelectionRange(2, 5);
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith("/v1/documents/d1/assist/revise", {
        content: mockVersion.content_markdown.slice(2, 5),
        instruction: "",
        previous_suggestion: undefined,
      });
    });
  });

  it("renders the suggestion in a distinct panel while leaving the editable pane unchanged", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockResolvedValue({ suggestion: "Suggested replacement text." });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = (await screen.findByRole("textbox", { name: /markdown source/i })) as HTMLTextAreaElement;
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));

    await waitFor(() => {
      expect(screen.getByText("Suggested replacement text.")).toBeInTheDocument();
    });
    expect(textarea.value).toBe(mockVersion.content_markdown);
  });

  it("applies the suggestion into the editable pane on Accept and marks the session edited", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockResolvedValue({ suggestion: "Accepted replacement." });
    mockApi.put.mockResolvedValue({
      draft: { content_markdown: "Accepted replacement.", editor_user_id: "u1", started_at: "2026-01-01T00:00:00Z", last_autosaved_at: "2026-01-01T00:00:00Z" },
    });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = (await screen.findByRole("textbox", { name: /markdown source/i })) as HTMLTextAreaElement;
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));

    await waitFor(() => expect(screen.getByText("Accepted replacement.")).toBeInTheDocument());

    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: /^accept$/i }));

    expect(textarea.value).toBe("Accepted replacement.");

    act(() => vi.advanceTimersByTime(4000));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(mockApi.put).toHaveBeenCalledWith("/v1/documents/d1/draft", { content_markdown: "Accepted replacement." });
  });

  it("leaves the editable pane exactly as it was and closes the panel on Discard", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockResolvedValue({ suggestion: "Discarded suggestion." });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = (await screen.findByRole("textbox", { name: /markdown source/i })) as HTMLTextAreaElement;
    const originalValue = textarea.value;
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));

    await waitFor(() => expect(screen.getByText("Discarded suggestion.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /^discard$/i }));

    expect(textarea.value).toBe(originalValue);
    expect(screen.queryByText("Discarded suggestion.")).not.toBeInTheDocument();
  });

  it("shows an error message and leaves the editable pane untouched on API failure", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockRejectedValue(new Error("LLM unavailable"));
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = (await screen.findByRole("textbox", { name: /markdown source/i })) as HTMLTextAreaElement;
    const originalValue = textarea.value;
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));

    await waitFor(() => expect(screen.getByText(/llm unavailable/i)).toBeInTheDocument());
    expect(textarea.value).toBe(originalValue);
  });

  it("disables the trigger while a request is in flight", async () => {
    setupDocumentMocks(editorMembership);
    let resolvePost!: (v: unknown) => void;
    mockApi.post.mockReturnValue(new Promise((res) => { resolvePost = res; }));
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    await screen.findByRole("textbox", { name: /markdown source/i });
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: /revis/i })).toBeDisabled());
    resolvePost({ suggestion: "Late suggestion." });
  });
});

describe("Document edit page — iterative refinement", () => {
  it("submits a follow-up refinement using the currently shown suggestion as context", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post
      .mockResolvedValueOnce({ suggestion: "Suggestion A" })
      .mockResolvedValueOnce({ suggestion: "Suggestion B" });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    await screen.findByRole("textbox", { name: /markdown source/i });
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));
    await waitFor(() => expect(screen.getByText("Suggestion A")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "even shorter" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenLastCalledWith("/v1/documents/d1/assist/revise", {
        content: mockVersion.content_markdown,
        instruction: "even shorter",
        previous_suggestion: "Suggestion A",
      });
    });
    await waitFor(() => expect(screen.getByText("Suggestion B")).toBeInTheDocument());
  });

  it("applies the latest suggestion after two refinements, not an earlier one", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post
      .mockResolvedValueOnce({ suggestion: "Suggestion A" })
      .mockResolvedValueOnce({ suggestion: "Suggestion B" })
      .mockResolvedValueOnce({ suggestion: "Suggestion C" });
    mockApi.put.mockResolvedValue({
      draft: { content_markdown: "Suggestion C", editor_user_id: "u1", started_at: "2026-01-01T00:00:00Z", last_autosaved_at: "2026-01-01T00:00:00Z" },
    });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = (await screen.findByRole("textbox", { name: /markdown source/i })) as HTMLTextAreaElement;
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));
    await waitFor(() => expect(screen.getByText("Suggestion A")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "refine 1" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));
    await waitFor(() => expect(screen.getByText("Suggestion B")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "refine 2" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));
    await waitFor(() => expect(screen.getByText("Suggestion C")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^accept$/i }));
    expect(textarea.value).toBe("Suggestion C");
  });

  it("restores the pre-suggestion content after two refinements when Discard is clicked", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post
      .mockResolvedValueOnce({ suggestion: "Suggestion A" })
      .mockResolvedValueOnce({ suggestion: "Suggestion B" })
      .mockResolvedValueOnce({ suggestion: "Suggestion C" });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    const textarea = (await screen.findByRole("textbox", { name: /markdown source/i })) as HTMLTextAreaElement;
    const originalValue = textarea.value;
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));
    await waitFor(() => expect(screen.getByText("Suggestion A")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "refine 1" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));
    await waitFor(() => expect(screen.getByText("Suggestion B")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "refine 2" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));
    await waitFor(() => expect(screen.getByText("Suggestion C")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^discard$/i }));
    expect(textarea.value).toBe(originalValue);
    expect(screen.queryByText("Suggestion C")).not.toBeInTheDocument();
  });
});

describe("Document edit page — pending suggestion discarded on finalize", () => {
  it("never includes the pending suggestion text when finalizing with an open, un-accepted panel", async () => {
    setupDocumentMocks(editorMembership);
    mockApi.post.mockImplementation((path: string) => {
      if (path === "/v1/documents/d1/assist/revise") return Promise.resolve({ suggestion: "Never applied suggestion text." });
      if (path === "/v1/documents/d1/draft/finish") return Promise.resolve({ version: null });
      return Promise.resolve({});
    });
    const { default: DocumentEditPage } = await import("@/app/documents/[id]/edit/page");
    render(<DocumentEditPage />);

    await screen.findByRole("textbox", { name: /markdown source/i });
    fireEvent.click(screen.getByRole("button", { name: /ask ai to revise/i }));
    await waitFor(() => expect(screen.getByText("Never applied suggestion text.")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /done editing/i }));

    await waitFor(() => expect(mockApi.post).toHaveBeenCalledWith("/v1/documents/d1/draft/finish", {}));
    expect(mockApi.put).not.toHaveBeenCalledWith(
      "/v1/documents/d1/draft",
      expect.objectContaining({ content_markdown: expect.stringContaining("Never applied suggestion text.") }),
    );
  });
});
