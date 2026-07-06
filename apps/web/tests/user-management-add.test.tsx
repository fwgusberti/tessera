import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

// --- companies lib mock ---
vi.mock("@/lib/companies", () => ({
  inviteCompanyMember: vi.fn(),
  searchAddableUsers: vi.fn(),
  addCompanyMember: vi.fn(),
}));

import { inviteCompanyMember, searchAddableUsers, addCompanyMember } from "@/lib/companies";

const mockInvite = inviteCompanyMember as unknown as ReturnType<typeof vi.fn>;
const mockSearch = searchAddableUsers as unknown as ReturnType<typeof vi.fn>;
const mockAdd = addCompanyMember as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AddUserPanel — invite by email (US1)", () => {
  it("submitting a valid email invites and renders an 'invitation sent' confirmation", async () => {
    mockInvite.mockResolvedValue({ status: "sent", email: "new.person@x.com", role: "member" });
    const { AddUserPanel } = await import("@/components/company/AddUserPanel");
    const user = userEvent.setup();
    render(<AddUserPanel />);

    await user.type(screen.getByLabelText(/email/i), "new.person@x.com");
    await user.click(screen.getByRole("button", { name: /send invite/i }));

    await waitFor(() =>
      expect(mockInvite).toHaveBeenCalledWith("new.person@x.com", "member")
    );
    expect(await screen.findByText(/invitation sent/i)).toBeInTheDocument();
  });

  it("a malformed email shows a validation message and does not call the API", async () => {
    const { AddUserPanel } = await import("@/components/company/AddUserPanel");
    const user = userEvent.setup();
    render(<AddUserPanel />);

    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.click(screen.getByRole("button", { name: /send invite/i }));

    expect(await screen.findByText(/valid email/i)).toBeInTheDocument();
    expect(mockInvite).not.toHaveBeenCalled();
  });
});

describe("AddUserPanel — direct-add existing user (US2)", () => {
  it("typing in the existing-user search calls searchAddableUsers (debounced) and renders results", async () => {
    mockSearch.mockResolvedValue([
      { user_id: "u9", display_name: "Grace Hopper", email: "grace@x.com" },
    ]);
    const { AddUserPanel } = await import("@/components/company/AddUserPanel");
    const user = userEvent.setup();
    render(<AddUserPanel />);

    // Switch to the "add existing user" mode.
    await user.click(screen.getByRole("button", { name: /add existing user/i }));
    await user.type(screen.getByLabelText(/search/i), "gra");

    await waitFor(() => expect(mockSearch).toHaveBeenCalledWith("gra"));
    expect(await screen.findByText("Grace Hopper")).toBeInTheDocument();
  });

  it("selecting a result and submitting calls addCompanyMember and appends the member", async () => {
    mockSearch.mockResolvedValue([
      { user_id: "u9", display_name: "Grace Hopper", email: "grace@x.com" },
    ]);
    mockAdd.mockResolvedValue({
      user_id: "u9",
      display_name: "Grace Hopper",
      email: "grace@x.com",
      role: "member",
    });
    const onMemberAdded = vi.fn();
    const { AddUserPanel } = await import("@/components/company/AddUserPanel");
    const user = userEvent.setup();
    render(<AddUserPanel onMemberAdded={onMemberAdded} />);

    await user.click(screen.getByRole("button", { name: /add existing user/i }));
    await user.type(screen.getByLabelText(/search/i), "gra");
    await user.click(await screen.findByText("Grace Hopper"));
    await user.click(screen.getByRole("button", { name: /^add user$/i }));

    await waitFor(() => expect(mockAdd).toHaveBeenCalledWith("u9", "member"));
    await waitFor(() =>
      expect(onMemberAdded).toHaveBeenCalledWith({
        user_id: "u9",
        display_name: "Grace Hopper",
        email: "grace@x.com",
        role: "member",
      })
    );
  });
});

describe("AddUserPanel — role selection (US3)", () => {
  it("the role selector defaults to member for the invite path", async () => {
    mockInvite.mockResolvedValue({ status: "sent", email: "p@x.com", role: "member" });
    const { AddUserPanel } = await import("@/components/company/AddUserPanel");
    const user = userEvent.setup();
    render(<AddUserPanel />);

    const roleSelect = screen.getByLabelText(/role/i) as HTMLSelectElement;
    expect(roleSelect.value).toBe("member");

    await user.type(screen.getByLabelText(/email/i), "p@x.com");
    await user.click(screen.getByRole("button", { name: /send invite/i }));

    await waitFor(() => expect(mockInvite).toHaveBeenCalledWith("p@x.com", "member"));
  });

  it("passes the chosen admin role to inviteCompanyMember", async () => {
    mockInvite.mockResolvedValue({ status: "sent", email: "p@x.com", role: "admin" });
    const { AddUserPanel } = await import("@/components/company/AddUserPanel");
    const user = userEvent.setup();
    render(<AddUserPanel />);

    await user.selectOptions(screen.getByLabelText(/role/i), "admin");
    await user.type(screen.getByLabelText(/email/i), "p@x.com");
    await user.click(screen.getByRole("button", { name: /send invite/i }));

    await waitFor(() => expect(mockInvite).toHaveBeenCalledWith("p@x.com", "admin"));
  });

  it("passes the chosen admin role to addCompanyMember", async () => {
    mockSearch.mockResolvedValue([
      { user_id: "u9", display_name: "Grace Hopper", email: "grace@x.com" },
    ]);
    mockAdd.mockResolvedValue({
      user_id: "u9",
      display_name: "Grace Hopper",
      email: "grace@x.com",
      role: "admin",
    });
    const { AddUserPanel } = await import("@/components/company/AddUserPanel");
    const user = userEvent.setup();
    render(<AddUserPanel />);

    await user.click(screen.getByRole("button", { name: /add existing user/i }));
    await user.selectOptions(screen.getByLabelText(/role/i), "admin");
    await user.type(screen.getByLabelText(/search/i), "gra");
    await user.click(await screen.findByText("Grace Hopper"));
    await user.click(screen.getByRole("button", { name: /^add user$/i }));

    await waitFor(() => expect(mockAdd).toHaveBeenCalledWith("u9", "admin"));
  });
});
