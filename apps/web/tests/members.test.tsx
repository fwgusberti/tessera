import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "actor-id", email: "actor@example.com" },
    accessToken: "tok",
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

const SPACE_ID = "space-abc-123";

const mockMembers = [
  {
    id: "m1",
    space_id: SPACE_ID,
    user_id: "actor-id",
    display_name: "Actor User",
    email: "actor@example.com",
    role: "admin",
    invited_by_user_id: null,
    created_at: "2026-06-21T12:00:00Z",
  },
  {
    id: "m2",
    space_id: SPACE_ID,
    user_id: "other-id",
    display_name: "Other User",
    email: "other@example.com",
    role: "viewer",
    invited_by_user_id: "actor-id",
    created_at: "2026-06-21T13:00:00Z",
  },
];

const myMembership = {
  space_id: SPACE_ID,
  user_id: "actor-id",
  role: "admin",
  created_at: "2026-06-21T12:00:00Z",
};

// ---------------------------------------------------------------------------
// RoleBadge
// ---------------------------------------------------------------------------

describe("RoleBadge", () => {
  it("renders admin role with indigo styles", async () => {
    const { RoleBadge } = await import("@/components/members/RoleBadge");
    render(<RoleBadge role="admin" />);
    const badge = screen.getByText("admin");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("indigo");
  });

  it("renders editor role with slate styles", async () => {
    const { RoleBadge } = await import("@/components/members/RoleBadge");
    render(<RoleBadge role="editor" />);
    const badge = screen.getByText("editor");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("slate");
  });

  it("renders viewer role with slate-50 styles", async () => {
    const { RoleBadge } = await import("@/components/members/RoleBadge");
    render(<RoleBadge role="viewer" />);
    const badge = screen.getByText("viewer");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("slate");
  });
});

// ---------------------------------------------------------------------------
// SpaceMembersPanel
// ---------------------------------------------------------------------------

describe("SpaceMembersPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders member list with role badges", async () => {
    mockApi.get.mockResolvedValue({ members: mockMembers });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="admin" />);

    await waitFor(() => {
      expect(screen.getByText("Actor User")).toBeInTheDocument();
      expect(screen.getByText("Other User")).toBeInTheDocument();
    });
  });

  it("shows add member form when caller is ADMIN", async () => {
    mockApi.get.mockResolvedValue({ members: mockMembers });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="admin" />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search by name or email/i)).toBeInTheDocument();
    });
  });

  it("hides add member form when caller is not ADMIN", async () => {
    mockApi.get.mockResolvedValue({ members: mockMembers });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="viewer" />);

    await waitFor(() => {
      expect(screen.queryByPlaceholderText(/search by name or email/i)).not.toBeInTheDocument();
    });
  });

  it("shows remove button for ADMIN on other members", async () => {
    mockApi.get.mockResolvedValue({ members: mockMembers });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="admin" />);

    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: /remove/i }).length).toBeGreaterThan(0);
    });
  });
});
