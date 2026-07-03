import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "t@t.com", isAdmin: false }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

const mockSpaces = [
  { id: "s1", slug: "eng", name: "Engineering", sector: "Tech", default_language: "en", confidence_threshold: 0.7, retention_policy: {} },
];

const editorMembership = { membership: { space_id: "s1", user_id: "u1", role: "editor" as const, created_at: "2026-01-01T00:00:00Z" } };
const viewerMembership = { membership: { space_id: "s1", user_id: "u1", role: "viewer" as const, created_at: "2026-01-01T00:00:00Z" } };

function setupMocks(membershipResponse: typeof editorMembership | typeof viewerMembership = editorMembership) {
  mockApi.get.mockImplementation((path: string) => {
    if (path === "/v1/spaces") return Promise.resolve({ spaces: mockSpaces });
    if (path.includes("/v1/documents")) return Promise.resolve({ documents: [] });
    if (path === "/v1/spaces/s1/members/me") return Promise.resolve(membershipResponse);
    return Promise.resolve({});
  });
}

async function openModalWithSpaceSelected() {
  const { default: DocumentsPage } = await import("@/app/documents/page");
  render(<DocumentsPage />);
  await waitFor(() => expect(screen.getByRole("option", { name: "Engineering" })).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /add document/i }));
  fireEvent.change(screen.getByLabelText(/space/i), { target: { value: "s1" } });
}

describe("Add Document modal — AI draft generation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  it("shows the Generate with AI control for an EDITOR-role space", async () => {
    setupMocks(editorMembership);
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    expect(screen.getByLabelText(/ai prompt/i)).toBeInTheDocument();
  });

  it("hides the Generate with AI control for a VIEWER-role space", async () => {
    setupMocks(viewerMembership);
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByLabelText(/space/i)).toHaveValue("s1"));
    expect(screen.queryByRole("button", { name: /generate with ai/i })).not.toBeInTheDocument();
  });

  it("calls generateDraft and fills the content field without auto-submitting", async () => {
    setupMocks(editorMembership);
    mockApi.post.mockResolvedValue({ content_markdown: "# Onboarding\n\nWelcome to the team!" });
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/ai prompt/i), { target: { value: "Onboarding checklist" } });
    fireEvent.click(screen.getByRole("button", { name: /generate with ai/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith("/v1/documents/assist/draft", {
        space_id: "s1",
        prompt: "Onboarding checklist",
        previous_suggestion: undefined,
      });
    });

    await waitFor(() => {
      expect(screen.getByLabelText(/content/i)).toHaveValue("# Onboarding\n\nWelcome to the team!");
    });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("keeps manual edits after a draft appears", async () => {
    setupMocks(editorMembership);
    mockApi.post.mockResolvedValue({ content_markdown: "# Generated" });
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/ai prompt/i), { target: { value: "Topic" } });
    fireEvent.click(screen.getByRole("button", { name: /generate with ai/i }));

    await waitFor(() => expect(screen.getByLabelText(/content/i)).toHaveValue("# Generated"));

    fireEvent.change(screen.getByLabelText(/content/i), { target: { value: "Hand-edited content" } });
    expect(screen.getByLabelText(/content/i)).toHaveValue("Hand-edited content");
  });

  it("blocks a blank prompt client-side with an inline message and no API call", async () => {
    setupMocks(editorMembership);
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /generate with ai/i }));

    expect(screen.getByText(/prompt is required/i)).toBeInTheDocument();
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("shows a banner on API error and leaves existing content untouched", async () => {
    setupMocks(editorMembership);
    mockApi.post.mockRejectedValue(new Error("LLM unavailable"));
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/content/i), { target: { value: "existing text" } });
    fireEvent.change(screen.getByLabelText(/ai prompt/i), { target: { value: "Topic" } });
    fireEvent.click(screen.getByRole("button", { name: /generate with ai/i }));

    await waitFor(() => expect(screen.getByText(/llm unavailable/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/content/i)).toHaveValue("existing text");
  });

  it("submits a follow-up refinement instruction and overwrites the content field", async () => {
    setupMocks(editorMembership);
    mockApi.post
      .mockResolvedValueOnce({ content_markdown: "# Draft A" })
      .mockResolvedValueOnce({ content_markdown: "# Draft B" });
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/ai prompt/i), { target: { value: "Onboarding checklist" } });
    fireEvent.click(screen.getByRole("button", { name: /generate with ai/i }));
    await waitFor(() => expect(screen.getByLabelText(/content/i)).toHaveValue("# Draft A"));

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "shorter" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenLastCalledWith("/v1/documents/assist/draft", {
        space_id: "s1",
        prompt: "shorter",
        previous_suggestion: "# Draft A",
      });
    });
    await waitFor(() => expect(screen.getByLabelText(/content/i)).toHaveValue("# Draft B"));
  });

  it("restores the pre-AI content after two refinements when Discard AI draft is clicked", async () => {
    setupMocks(editorMembership);
    mockApi.post
      .mockResolvedValueOnce({ content_markdown: "# Draft A" })
      .mockResolvedValueOnce({ content_markdown: "# Draft B" })
      .mockResolvedValueOnce({ content_markdown: "# Draft C" });
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/content/i), { target: { value: "hand-typed intro" } });
    fireEvent.change(screen.getByLabelText(/ai prompt/i), { target: { value: "topic" } });
    fireEvent.click(screen.getByRole("button", { name: /generate with ai/i }));
    await waitFor(() => expect(screen.getByLabelText(/content/i)).toHaveValue("# Draft A"));

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "refine 1" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));
    await waitFor(() => expect(screen.getByLabelText(/content/i)).toHaveValue("# Draft B"));

    fireEvent.change(screen.getByLabelText(/refine instruction/i), { target: { value: "refine 2" } });
    fireEvent.click(screen.getByRole("button", { name: /^refine$/i }));
    await waitFor(() => expect(screen.getByLabelText(/content/i)).toHaveValue("# Draft C"));

    fireEvent.click(screen.getByRole("button", { name: /discard ai draft/i }));
    expect(screen.getByLabelText(/content/i)).toHaveValue("hand-typed intro");
  });

  it("disables the Generate with AI button while a request is in flight", async () => {
    setupMocks(editorMembership);
    let resolvePost!: (v: unknown) => void;
    mockApi.post.mockReturnValue(new Promise((res) => { resolvePost = res; }));
    await openModalWithSpaceSelected();

    await waitFor(() => expect(screen.getByRole("button", { name: /generate with ai/i })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/ai prompt/i), { target: { value: "Topic" } });
    fireEvent.click(screen.getByRole("button", { name: /generate with ai/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: /generat/i })).toBeDisabled());
    resolvePost({ content_markdown: "# Done" });
  });
});
