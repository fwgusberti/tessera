import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/members", () => ({
  getMemberSpaceAccess: vi.fn(),
  addSpaceMember: vi.fn(),
  changeSpaceMemberRole: vi.fn(),
  removeSpaceMember: vi.fn(),
}));

import {
  getMemberSpaceAccess,
  addSpaceMember,
  changeSpaceMemberRole,
  removeSpaceMember,
} from "@/lib/members";

const mockGet = getMemberSpaceAccess as unknown as ReturnType<typeof vi.fn>;
const mockAdd = addSpaceMember as unknown as ReturnType<typeof vi.fn>;
const mockChange = changeSpaceMemberRole as unknown as ReturnType<typeof vi.fn>;
const mockRemove = removeSpaceMember as unknown as ReturnType<typeof vi.fn>;

const MEMBER = {
  user_id: "u1",
  display_name: "Fresh Member",
  email: "fresh@acme.test",
};

const directRow = {
  id: "s-eng",
  name: "Engineering",
  slug: "engineering",
  parent_space_id: null,
  direct_role: "viewer" as const,
  effective_role: "viewer" as const,
  is_direct: true,
};

const inheritedRow = {
  id: "s-docs",
  name: "Docs",
  slug: "docs",
  parent_space_id: "s-eng",
  direct_role: null,
  effective_role: "viewer" as const,
  is_direct: false,
};

const noAccessRow = {
  id: "s-fin",
  name: "Finance",
  slug: "finance",
  parent_space_id: null,
  direct_role: null,
  effective_role: null,
  is_direct: false,
};

function accessResponse(spaces: unknown[]) {
  return { member: MEMBER, spaces };
}

async function renderPanel() {
  const { MemberSpaceAccessPanel } = await import(
    "@/components/members/MemberSpaceAccessPanel"
  );
  render(<MemberSpaceAccessPanel member={MEMBER} />);
}

async function rowFor(name: string): Promise<HTMLElement> {
  const cell = await screen.findByText(name);
  const row = cell.closest("tr");
  expect(row).not.toBeNull();
  return row as HTMLElement;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("confirm", vi.fn(() => true));
});

describe("MemberSpaceAccessPanel — rendering access states (FR-001)", () => {
  it("renders every space with its access state", async () => {
    mockGet.mockResolvedValue(accessResponse([directRow, inheritedRow, noAccessRow]));
    await renderPanel();

    expect(await screen.findByText("Engineering")).toBeInTheDocument();
    expect(screen.getByText("Docs")).toBeInTheDocument();
    expect(screen.getByText("Finance")).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith("u1");

    // direct: role select carrying the current role
    const direct = await rowFor("Engineering");
    expect(
      (within(direct).getByRole("combobox") as HTMLSelectElement).value
    ).toBe("viewer");

    // inherited-only: informational, no controls
    const inherited = await rowFor("Docs");
    expect(within(inherited).getByText(/inherited/i)).toBeInTheDocument();

    // no access: explicit "no access" state
    const none = await rowFor("Finance");
    expect(within(none).getByText(/no access/i)).toBeInTheDocument();
  });
});

describe("MemberSpaceAccessPanel — grant (FR-002)", () => {
  it("a no-access row offers grant with the role select defaulting to viewer", async () => {
    mockGet.mockResolvedValue(accessResponse([noAccessRow]));
    await renderPanel();

    const row = await rowFor("Finance");
    const select = within(row).getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("viewer");
    expect(within(row).getByRole("button", { name: /grant/i })).toBeInTheDocument();
  });

  it("granting calls the space-member endpoint and updates the row in place", async () => {
    mockGet
      .mockResolvedValueOnce(accessResponse([noAccessRow]))
      .mockResolvedValueOnce(
        accessResponse([
          { ...noAccessRow, direct_role: "editor", effective_role: "editor", is_direct: true },
        ])
      );
    mockAdd.mockResolvedValue({});
    const user = userEvent.setup();
    await renderPanel();

    const row = await rowFor("Finance");
    await user.selectOptions(within(row).getByRole("combobox"), "editor");
    await user.click(within(row).getByRole("button", { name: /grant/i }));

    await waitFor(() => expect(mockAdd).toHaveBeenCalledWith("s-fin", "u1", "editor"));

    // row updates in place: now direct with revoke offered
    await waitFor(() =>
      expect(
        within(screen.getByText("Finance").closest("tr") as HTMLElement).getByRole(
          "button",
          { name: /revoke/i }
        )
      ).toBeInTheDocument()
    );
  });
});

describe("MemberSpaceAccessPanel — change role and revoke (FR-003)", () => {
  it("a direct row offers change-role, calling the PUT wrapper", async () => {
    mockGet
      .mockResolvedValueOnce(accessResponse([directRow]))
      .mockResolvedValueOnce(
        accessResponse([
          { ...directRow, direct_role: "editor", effective_role: "editor" },
        ])
      );
    mockChange.mockResolvedValue({});
    const user = userEvent.setup();
    await renderPanel();

    const row = await rowFor("Engineering");
    await user.selectOptions(within(row).getByRole("combobox"), "editor");

    await waitFor(() =>
      expect(mockChange).toHaveBeenCalledWith("s-eng", "u1", "editor")
    );
    await waitFor(() =>
      expect(
        (
          within(screen.getByText("Engineering").closest("tr") as HTMLElement).getByRole(
            "combobox"
          ) as HTMLSelectElement
        ).value
      ).toBe("editor")
    );
  });

  it("a direct row offers revoke, calling the DELETE wrapper and updating in place", async () => {
    mockGet
      .mockResolvedValueOnce(accessResponse([directRow]))
      .mockResolvedValueOnce(
        accessResponse([
          { ...directRow, direct_role: null, effective_role: null, is_direct: false },
        ])
      );
    mockRemove.mockResolvedValue(undefined);
    const user = userEvent.setup();
    await renderPanel();

    const row = await rowFor("Engineering");
    await user.click(within(row).getByRole("button", { name: /revoke/i }));

    await waitFor(() => expect(mockRemove).toHaveBeenCalledWith("s-eng", "u1"));
    await waitFor(() =>
      expect(
        within(screen.getByText("Engineering").closest("tr") as HTMLElement).getByText(
          /no access/i
        )
      ).toBeInTheDocument()
    );
  });

  it("an inherited-only row is informational — no revoke offered", async () => {
    mockGet.mockResolvedValue(accessResponse([inheritedRow]));
    await renderPanel();

    const row = await rowFor("Docs");
    expect(within(row).queryByRole("button", { name: /revoke/i })).not.toBeInTheDocument();
    expect(within(row).getByText(/inherited/i)).toBeInTheDocument();
  });
});
