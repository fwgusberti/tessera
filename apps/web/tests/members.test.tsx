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

// ---------------------------------------------------------------------------
// SpaceMembersPanel — member identity display (feature 065, US1)
// ---------------------------------------------------------------------------

describe("SpaceMembersPanel identity display", () => {
  const NAMED_UUID = "aaaaaaaa-1111-2222-3333-444444444444";
  const BLANK_NAME_UUID = "bbbbbbbb-1111-2222-3333-444444444444";
  const NO_IDENTITY_UUID = "cccccccc-1111-2222-3333-444444444444";

  const identityMembers = [
    {
      id: "im1",
      space_id: SPACE_ID,
      user_id: NAMED_UUID,
      display_name: "Ana Souza",
      email: "ana@example.com",
      role: "admin",
      invited_by_user_id: null,
      created_at: "2026-07-01T12:00:00Z",
    },
    {
      id: "im2",
      space_id: SPACE_ID,
      user_id: BLANK_NAME_UUID,
      display_name: "",
      email: "blank-name@example.com",
      role: "viewer",
      invited_by_user_id: null,
      created_at: "2026-07-01T13:00:00Z",
    },
    {
      id: "im3",
      space_id: SPACE_ID,
      user_id: NO_IDENTITY_UUID,
      display_name: "",
      email: "",
      role: "viewer",
      invited_by_user_id: null,
      created_at: "2026-07-01T14:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the display name primary with the email beneath in muted text", async () => {
    mockApi.get.mockResolvedValue({ members: [identityMembers[0]] });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="viewer" />);

    const name = await screen.findByText("Ana Souza");
    expect(name).toBeInTheDocument();
    const email = screen.getByText("ana@example.com");
    expect(email).toBeInTheDocument();
    expect(email.className).toContain("text-slate-500");
  });

  it("uses the email as the primary label when display_name is blank, without a duplicated secondary line", async () => {
    mockApi.get.mockResolvedValue({ members: [identityMembers[1]] });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="viewer" />);

    const emailNodes = await screen.findAllByText("blank-name@example.com");
    expect(emailNodes).toHaveLength(1);
    expect(emailNodes[0].className).toContain("font-medium");
  });

  it('renders "Unknown user" when both display_name and email are blank', async () => {
    mockApi.get.mockResolvedValue({ members: [identityMembers[2]] });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="viewer" />);

    expect(await screen.findByText("Unknown user")).toBeInTheDocument();
  });

  it("never renders a member's UUID anywhere in the table", async () => {
    mockApi.get.mockResolvedValue({ members: identityMembers });

    const { SpaceMembersPanel } = await import("@/components/members/SpaceMembersPanel");
    const { container } = render(<SpaceMembersPanel spaceId={SPACE_ID} myRole="admin" />);

    await screen.findByText("Ana Souza");
    const rendered = container.textContent ?? "";
    expect(rendered).not.toContain(NAMED_UUID);
    expect(rendered).not.toContain(BLANK_NAME_UUID);
    expect(rendered).not.toContain(NO_IDENTITY_UUID);
  });
});
