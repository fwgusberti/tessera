import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "@/lib/api";

const mockApi = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

const mockSpaces = [
  { id: "s1", slug: "eng", name: "Engineering", sector: "Tech", default_language: "en", confidence_threshold: 0.7, retention_policy: {} },
];

const mockMetrics = { correct_answer_rate: null, dont_know_rate: null, documents_with_drift: 2, time_to_approval_p50: null, time_to_approval_p90: null, total_queries: 10 };

describe("Admin page — Create Space form", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/admin/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path === "/v1/metrics") return Promise.resolve(mockMetrics);
      return Promise.resolve({ spaces: [] });
    });
  });

  it("renders the Create Space form with required fields", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Slug (e.g. engineering)")).toBeInTheDocument();
    });

    expect(screen.getByPlaceholderText("Name (e.g. Engineering)")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Sector (e.g. Technology)")).toBeInTheDocument();
  });

  it("shows inline validation error and makes no API call when slug is empty", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Slug (e.g. engineering)")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Name (e.g. Engineering)"), { target: { value: "Test Space" } });
    fireEvent.change(screen.getByPlaceholderText("Sector (e.g. Technology)"), { target: { value: "Tech" } });

    const submitButton = screen.getByRole("button", { name: /create space/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/slug is required/i)).toBeInTheDocument();
    });

    expect(mockApi.post).not.toHaveBeenCalledWith("/v1/spaces", expect.anything());
  });

  it("appends new space to table and resets form on successful creation", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    const newSpace = { id: "s2", slug: "qa", name: "QA Team", sector: "Quality", default_language: "en", confidence_threshold: 0.7, retention_policy: {} };
    mockApi.post.mockResolvedValue({ space: newSpace });

    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Slug (e.g. engineering)")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Slug (e.g. engineering)"), { target: { value: "qa" } });
    fireEvent.change(screen.getByPlaceholderText("Name (e.g. Engineering)"), { target: { value: "QA Team" } });
    fireEvent.change(screen.getByPlaceholderText("Sector (e.g. Technology)"), { target: { value: "Quality" } });

    fireEvent.click(screen.getByRole("button", { name: /create space/i }));

    await waitFor(() => {
      expect(screen.getAllByText("QA Team").length).toBeGreaterThan(0);
    });

    expect((screen.getByPlaceholderText("Slug (e.g. engineering)") as HTMLInputElement).value).toBe("");
  });
});

describe("Admin page — Connectors section", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/admin/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path === "/v1/metrics") return Promise.resolve(mockMetrics);
      return Promise.resolve({ spaces: [] });
    });
  });

  it("shows JSON validation error when config is not valid JSON", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Type (e.g. confluence)")).toBeInTheDocument();
    });

    const connectorHeading = screen.getByRole("heading", { name: /connectors/i });
    const connectorSection = connectorHeading.closest("section")!;
    const connectorSpaceSelect = within(connectorSection).getAllByRole("combobox")[0];
    fireEvent.change(connectorSpaceSelect, { target: { value: "s1" } });
    fireEvent.change(screen.getByPlaceholderText("Type (e.g. confluence)"), { target: { value: "confluence" } });
    fireEvent.change(screen.getByPlaceholderText(/Config JSON/i), { target: { value: "not-json" } });

    fireEvent.click(screen.getByRole("button", { name: /create connector/i }));

    await waitFor(() => {
      expect(within(connectorSection).getByText(/valid JSON/i)).toBeInTheDocument();
    });
  });

  it("creates connector and displays it in the session list", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    mockApi.post.mockResolvedValue({ connector: { id: "c1", type: "confluence", schedule: null } });

    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Type (e.g. confluence)")).toBeInTheDocument();
    });

    const connectorHeading = screen.getByRole("heading", { name: /connectors/i });
    const connectorSection = connectorHeading.closest("section")!;
    const connectorSpaceSelect = within(connectorSection).getAllByRole("combobox")[0];
    fireEvent.change(connectorSpaceSelect, { target: { value: "s1" } });
    fireEvent.change(screen.getByPlaceholderText("Type (e.g. confluence)"), { target: { value: "confluence" } });
    fireEvent.change(screen.getByPlaceholderText(/Config JSON/i), { target: { value: '{"token":"abc"}' } });

    fireEvent.click(screen.getByRole("button", { name: /create connector/i }));

    await waitFor(() => {
      expect(within(connectorSection).getByRole("button", { name: /sync now/i })).toBeInTheDocument();
    });
  });

  it("shows job ID after triggering sync", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    mockApi.post
      .mockResolvedValueOnce({ connector: { id: "c1", type: "confluence", schedule: null } })
      .mockResolvedValueOnce({ job_id: "job-abc-123" });

    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Type (e.g. confluence)")).toBeInTheDocument();
    });

    const connectorHeading = screen.getByRole("heading", { name: /connectors/i });
    const connectorSection = connectorHeading.closest("section")!;
    const connectorSpaceSelect = within(connectorSection).getAllByRole("combobox")[0];
    fireEvent.change(connectorSpaceSelect, { target: { value: "s1" } });
    fireEvent.change(screen.getByPlaceholderText("Type (e.g. confluence)"), { target: { value: "confluence" } });
    fireEvent.change(screen.getByPlaceholderText(/Config JSON/i), { target: { value: '{"token":"abc"}' } });
    fireEvent.click(screen.getByRole("button", { name: /create connector/i }));

    await waitFor(() => {
      expect(within(connectorSection).getByRole("button", { name: /sync now/i })).toBeInTheDocument();
    });

    fireEvent.click(within(connectorSection).getByRole("button", { name: /sync now/i }));

    await waitFor(() => {
      expect(within(connectorSection).getByText(/job-abc-123/i)).toBeInTheDocument();
    });
  });
});

describe("Admin page — Agent Credentials section", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/admin/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path === "/v1/metrics") return Promise.resolve(mockMetrics);
      return Promise.resolve({ spaces: [] });
    });
  });

  it("displays one-time token with copy button on successful credential creation", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    mockApi.post.mockResolvedValue({
      credential: { id: "cr1", name: "CI Agent", max_confidentiality: "internal", revoked_at: null },
      token: "secret-raw-token-xyz",
    });

    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/credential name/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/credential name/i), { target: { value: "CI Agent" } });
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);

    fireEvent.click(screen.getByRole("button", { name: /create credential/i }));

    await waitFor(() => {
      expect(screen.getByText(/secret-raw-token-xyz/)).toBeInTheDocument();
    });

    expect(screen.getByText(/will not be shown again/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
  });

  it("marks credential as revoked when Revoke is clicked", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    mockApi.post
      .mockResolvedValueOnce({
        credential: { id: "cr1", name: "CI Agent", max_confidentiality: "internal", revoked_at: null },
        token: "secret-token",
      })
      .mockResolvedValueOnce({ credential: { id: "cr1", name: "CI Agent", max_confidentiality: "internal", revoked_at: "2026-06-12T00:00:00Z" } });

    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/credential name/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/credential name/i), { target: { value: "CI Agent" } });
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    fireEvent.click(screen.getByRole("button", { name: /create credential/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /revoke/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /revoke/i }));

    await waitFor(() => {
      expect(screen.getByText(/revoked/i)).toBeInTheDocument();
    });
  });
});

describe("Admin page — Space Permissions form", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.get.mockImplementation((path: string) => {
      if (path === "/v1/admin/spaces") return Promise.resolve({ spaces: mockSpaces });
      if (path === "/v1/metrics") return Promise.resolve(mockMetrics);
      return Promise.resolve({ spaces: [] });
    });
  });

  it("renders the permissions form with space selector and role select", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/idp group/i)).toBeInTheDocument();
    });

    expect(screen.getAllByRole("combobox").length).toBeGreaterThan(0);
  });

  it("shows success message on successful permission creation", async () => {
    const { default: AdminPage } = await import("@/app/admin/page");
    mockApi.post.mockResolvedValue({ permission: { id: "p1" } });

    render(<AdminPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/idp group/i)).toBeInTheDocument();
    });

    const spaceSelects = screen.getAllByRole("combobox");
    fireEvent.change(spaceSelects[0], { target: { value: "s1" } });
    fireEvent.change(screen.getByPlaceholderText(/idp group/i), { target: { value: "admins" } });

    fireEvent.click(screen.getByRole("button", { name: /add permission/i }));

    await waitFor(() => {
      expect(screen.getByText(/permission added/i)).toBeInTheDocument();
    });
  });
});
