import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

// --- next/navigation mock ---

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  usePathname: () => "/spaces",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "p1" }),
}));

// --- useAuth mock ---

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// --- api mock ---

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();
});

function apiSpace(overrides: Record<string, unknown>) {
  return {
    id: "s1",
    slug: "s1",
    name: "Engineering",
    sector: "Tech",
    parent_space_id: null,
    default_language: "en",
    confidence_threshold: 0.7,
    retention_policy: {},
    effective_role: "admin",
    is_direct: true,
    ...overrides,
  };
}

async function renderSpaces(spaces: Record<string, unknown>[]) {
  const { default: SpacesPage } = await import("@/app/spaces/page");
  mockApi.get.mockResolvedValue({ spaces });
  render(<SpacesPage />);
  await waitFor(() => screen.getByRole("heading", { name: "Engineering" }));
}

async function openPasswordStep() {
  fireEvent.click(screen.getByRole("button", { name: "Delete" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: /continue/i }));
  await within(dialog).findByLabelText(/password/i);
  return dialog;
}

describe("DeleteSpaceModal", () => {
  it("shows a Delete action only on admin-accessible tiles", async () => {
    await renderSpaces([
      apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" }),
      apiSpace({ id: "s2", name: "Marketing", slug: "s2", effective_role: "viewer" }),
    ]);

    const deleteButtons = screen.getAllByRole("button", { name: "Delete" });
    expect(deleteButtons).toHaveLength(1);
  });

  it("shows a confirmation step first, then a password step, without calling the API", async () => {
    await renderSpaces([apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" })]);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent(/Engineering/);
    expect(dialog).toHaveTextContent(/permanently delete/i);

    // No password input yet, no API call.
    expect(within(dialog).queryByLabelText(/password/i)).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: /continue/i }));

    expect(within(dialog).getByLabelText(/password/i)).toBeInTheDocument();
    expect(mockApi.delete).not.toHaveBeenCalled();
  });

  it("does nothing when cancelled at the confirmation step", async () => {
    await renderSpaces([apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" })]);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: /cancel/i }));

    expect(mockApi.delete).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Engineering" })).toBeInTheDocument();
  });

  it("shows an error and keeps the tile when the password is wrong", async () => {
    await renderSpaces([apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" })]);

    const dialog = await openPasswordStep();
    mockApi.delete.mockRejectedValueOnce(new Error("Current password is incorrect"));

    fireEvent.change(within(dialog).getByLabelText(/password/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/incorrect/i)
    );
    expect(screen.getByRole("heading", { name: "Engineering" })).toBeInTheDocument();
  });

  it("removes the tile immediately on successful deletion", async () => {
    await renderSpaces([apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" })]);

    const dialog = await openPasswordStep();
    mockApi.delete.mockResolvedValueOnce({
      deleted: true,
      space_id: "s1",
      deleted_space_count: 1,
      deleted_document_count: 0,
    });

    fireEvent.change(within(dialog).getByLabelText(/password/i), {
      target: { value: "correct" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: "Engineering" })).not.toBeInTheDocument()
    );
    expect(mockApi.delete).toHaveBeenCalledWith("/v1/spaces/s1", { password: "correct" });
    expect(mockApi.get).toHaveBeenCalledTimes(1);
  });

  it("stays on the password step after a wrong-password error and allows retry", async () => {
    await renderSpaces([apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" })]);

    const dialog = await openPasswordStep();
    mockApi.delete
      .mockRejectedValueOnce(new Error("Current password is incorrect"))
      .mockResolvedValueOnce({
        deleted: true,
        space_id: "s1",
        deleted_space_count: 1,
        deleted_document_count: 0,
      });

    fireEvent.change(within(dialog).getByLabelText(/password/i), { target: { value: "wrong" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(within(dialog).getByLabelText(/password/i)).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText(/password/i), { target: { value: "correct" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: "Engineering" })).not.toBeInTheDocument()
    );
    expect(mockApi.delete).toHaveBeenCalledTimes(2);
  });

  it("sends no request when cancelling at the confirmation step", async () => {
    await renderSpaces([apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" })]);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: /cancel/i }));

    expect(mockApi.delete).not.toHaveBeenCalled();
  });

  it("sends no request when cancelling at the password step", async () => {
    await renderSpaces([apiSpace({ id: "s1", name: "Engineering", effective_role: "admin" })]);

    const dialog = await openPasswordStep();
    fireEvent.click(within(dialog).getByRole("button", { name: /cancel/i }));

    expect(mockApi.delete).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Engineering" })).toBeInTheDocument();
  });
});
