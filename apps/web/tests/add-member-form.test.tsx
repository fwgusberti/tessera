import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

const SPACE_ID = "space-abc-123";

const searchResults = [
  { user_id: "bob-id", display_name: "Bob Builder", email: "bob@acme.com" },
];

async function searchAndSelectBob() {
  vi.useFakeTimers();
  fireEvent.change(screen.getByPlaceholderText(/search by name or email/i), {
    target: { value: "bo" },
  });
  await act(async () => {
    vi.advanceTimersByTime(300);
  });
  vi.useRealTimers();

  await waitFor(() => expect(screen.getByText("Bob Builder")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /bob builder/i }));
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "editor" } });
}

describe("AddMemberForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders a search input and role selector", async () => {
    const onSuccess = vi.fn();
    const { AddMemberForm } = await import("@/components/members/AddMemberForm");
    render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

    expect(screen.getByPlaceholderText(/search by name or email/i)).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("labels search results with the fallback chain display_name → email → Unknown user (feature 065, US3)", async () => {
    mockApi.get.mockResolvedValue({
      members: [
        { user_id: "named-id", display_name: "Named Person", email: "named@acme.com" },
        { user_id: "blank-name-id", display_name: "", email: "only-email@acme.com" },
        { user_id: "no-identity-id", display_name: "", email: "" },
      ],
    });

    const { AddMemberForm } = await import("@/components/members/AddMemberForm");
    render(<AddMemberForm spaceId={SPACE_ID} onSuccess={vi.fn()} />);

    vi.useFakeTimers();
    fireEvent.change(screen.getByPlaceholderText(/search by name or email/i), {
      target: { value: "an" },
    });
    await act(async () => {
      vi.advanceTimersByTime(300);
    });
    vi.useRealTimers();

    await waitFor(() => expect(screen.getByText("Named Person")).toBeInTheDocument());
    // Blank display_name → the email carries the primary (font-medium) label.
    const emailLabel = screen.getAllByText("only-email@acme.com")
      .find((el) => el.className.includes("font-medium"));
    expect(emailLabel).toBeTruthy();
    // Both blank → literal "Unknown user"; never the identifier.
    expect(screen.getByText("Unknown user")).toBeInTheDocument();
    expect(screen.queryByText("no-identity-id")).not.toBeInTheDocument();
  });

  it("does not search below 2 characters", async () => {
    const onSuccess = vi.fn();
    const { AddMemberForm } = await import("@/components/members/AddMemberForm");
    render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

    vi.useFakeTimers();
    fireEvent.change(screen.getByPlaceholderText(/search by name or email/i), {
      target: { value: "b" },
    });
    act(() => vi.advanceTimersByTime(500));

    expect(mockApi.get).not.toHaveBeenCalled();
  });

  it("debounces and searches once 2+ characters are typed", async () => {
    mockApi.get.mockResolvedValue({ members: searchResults });
    const onSuccess = vi.fn();
    const { AddMemberForm } = await import("@/components/members/AddMemberForm");
    render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

    vi.useFakeTimers();
    fireEvent.change(screen.getByPlaceholderText(/search by name or email/i), {
      target: { value: "bo" },
    });

    // Not called immediately — debounced
    expect(mockApi.get).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockApi.get).toHaveBeenCalledWith(
      `/v1/spaces/${SPACE_ID}/members/search?q=bo`
    );

    vi.useRealTimers();
    await waitFor(() => {
      expect(screen.getByText("Bob Builder")).toBeInTheDocument();
      expect(screen.getByText("bob@acme.com")).toBeInTheDocument();
    });
  });

  it("shows an empty-results message distinct from the not-yet-searched state", async () => {
    mockApi.get.mockResolvedValue({ members: [] });
    const onSuccess = vi.fn();
    const { AddMemberForm } = await import("@/components/members/AddMemberForm");
    render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

    expect(screen.queryByText(/no matches/i)).not.toBeInTheDocument();

    vi.useFakeTimers();
    fireEvent.change(screen.getByPlaceholderText(/search by name or email/i), {
      target: { value: "zzz" },
    });
    await act(async () => {
      vi.advanceTimersByTime(300);
    });
    vi.useRealTimers();

    await waitFor(() => {
      expect(screen.getByText(/no matches/i)).toBeInTheDocument();
    });
  });

  it("selects a result, picks a role, and submits to add the member", async () => {
    mockApi.get.mockResolvedValue({ members: searchResults });
    mockApi.post.mockResolvedValueOnce({
      membership: { id: "m9", space_id: SPACE_ID, user_id: "bob-id", role: "editor" },
    });
    const onSuccess = vi.fn();
    const { AddMemberForm } = await import("@/components/members/AddMemberForm");
    render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

    await searchAndSelectBob();
    fireEvent.click(screen.getByRole("button", { name: /^add member$/i }));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith(`/v1/spaces/${SPACE_ID}/members`, {
        user_id: "bob-id",
        role: "editor",
      });
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  describe("failure paths (FR-006, FR-010)", () => {
    it("shows an 'already a member' message and refreshes the list on a 400 (race) response", async () => {
      mockApi.get.mockResolvedValue({ members: searchResults });
      mockApi.post.mockRejectedValueOnce(new Error("Bad Request"));
      const onSuccess = vi.fn();
      const { AddMemberForm } = await import("@/components/members/AddMemberForm");
      render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

      await searchAndSelectBob();
      fireEvent.click(screen.getByRole("button", { name: /^add member$/i }));

      await waitFor(() => {
        expect(screen.getByText(/already a member/i)).toBeInTheDocument();
      });
      // The list must be refreshed to reflect reality even though this submit failed
      expect(onSuccess).toHaveBeenCalledTimes(1);
      // FR-010: query, selection, and role survive the failure
      expect(screen.getByDisplayValue("bo")).toBeInTheDocument();
      expect(screen.getByText("Bob Builder")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue("editor");
    });

    it("shows a permission message on a 403 response without refreshing the list", async () => {
      mockApi.get.mockResolvedValue({ members: searchResults });
      mockApi.post.mockRejectedValueOnce(new Error("Forbidden"));
      const onSuccess = vi.fn();
      const { AddMemberForm } = await import("@/components/members/AddMemberForm");
      render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

      await searchAndSelectBob();
      fireEvent.click(screen.getByRole("button", { name: /^add member$/i }));

      await waitFor(() => {
        expect(screen.getByText(/don't have permission/i)).toBeInTheDocument();
      });
      expect(onSuccess).not.toHaveBeenCalled();
      expect(screen.getByDisplayValue("bo")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue("editor");
    });

    it("shows a no-longer-eligible message on a 404 response without refreshing the list", async () => {
      mockApi.get.mockResolvedValue({ members: searchResults });
      mockApi.post.mockRejectedValueOnce(new Error("Not Found"));
      const onSuccess = vi.fn();
      const { AddMemberForm } = await import("@/components/members/AddMemberForm");
      render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

      await searchAndSelectBob();
      fireEvent.click(screen.getByRole("button", { name: /^add member$/i }));

      await waitFor(() => {
        expect(screen.getByText(/no longer eligible/i)).toBeInTheDocument();
      });
      expect(onSuccess).not.toHaveBeenCalled();
      expect(screen.getByDisplayValue("bo")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue("editor");
    });

    it("shows a retryable network message on a connectivity failure without refreshing the list", async () => {
      mockApi.get.mockResolvedValue({ members: searchResults });
      mockApi.post.mockRejectedValueOnce(
        new Error("Could not reach the server. Please check your connection and try again.")
      );
      const onSuccess = vi.fn();
      const { AddMemberForm } = await import("@/components/members/AddMemberForm");
      render(<AddMemberForm spaceId={SPACE_ID} onSuccess={onSuccess} />);

      await searchAndSelectBob();
      fireEvent.click(screen.getByRole("button", { name: /^add member$/i }));

      await waitFor(() => {
        expect(screen.getByText(/could not reach the server/i)).toBeInTheDocument();
      });
      expect(onSuccess).not.toHaveBeenCalled();
      expect(screen.getByDisplayValue("bo")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue("editor");
    });
  });
});
