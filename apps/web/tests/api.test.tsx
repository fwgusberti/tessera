import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import { api, configureApi } from "@/lib/api";

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

const mockGetAccessToken = vi.fn(() => "access-tok");
const mockRefreshIfNeeded = vi.fn(async () => "access-tok");
const mockForceRefresh = vi.fn(async () => "new-tok");
const mockOnUnauthorized = vi.fn();
const mockOnTenantSelectionRequired = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  mockGetAccessToken.mockReturnValue("access-tok");
  mockRefreshIfNeeded.mockResolvedValue("access-tok");
  mockForceRefresh.mockResolvedValue("new-tok");
  configureApi({
    getAccessToken: mockGetAccessToken,
    refreshIfNeeded: mockRefreshIfNeeded,
    forceRefresh: mockForceRefresh,
    onUnauthorized: mockOnUnauthorized,
    onTenantSelectionRequired: mockOnTenantSelectionRequired,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api / auth injection", () => {
  it("injects Authorization: Bearer header on every request", async () => {
    mockFetch.mockReturnValue(jsonResponse({ data: "ok" }));
    await api.get("/v1/spaces");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/spaces"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer access-tok",
        }),
      })
    );
  });

  it("calls refreshIfNeeded before each request", async () => {
    mockFetch.mockReturnValue(jsonResponse({ data: "ok" }));
    await api.get("/v1/spaces");
    expect(mockRefreshIfNeeded).toHaveBeenCalledTimes(1);
  });

  it("on 401 response, calls forceRefresh and retries the original request", async () => {
    mockFetch
      .mockReturnValueOnce(jsonResponse({ error: { message: "Unauthorized" } }, 401))
      .mockReturnValueOnce(jsonResponse({ spaces: [] }));

    const result = await api.get<{ spaces: unknown[] }>("/v1/spaces");

    expect(mockForceRefresh).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ spaces: [] });
  });

  it("on second consecutive 401 after retry, calls onUnauthorized and throws", async () => {
    mockFetch
      .mockReturnValueOnce(jsonResponse({ error: { message: "Unauthorized" } }, 401))
      .mockReturnValueOnce(jsonResponse({ error: { message: "Unauthorized" } }, 401));

    await expect(api.get("/v1/spaces")).rejects.toThrow();
    expect(mockOnUnauthorized).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("does not retry on non-401 errors", async () => {
    mockFetch.mockReturnValue(jsonResponse({ error: { message: "Not Found" } }, 404));

    await expect(api.get("/v1/spaces")).rejects.toThrow("Not Found");
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockForceRefresh).not.toHaveBeenCalled();
  });
});

describe("api / credential_not_scoped interception", () => {
  const RAW_MESSAGE = "Credential is not scoped to a tenant; call /auth/select-tenant first";

  it("invokes onTenantSelectionRequired and throws friendly copy on 403 credential_not_scoped", async () => {
    mockFetch.mockReturnValue(
      jsonResponse({ error: { code: "credential_not_scoped", message: RAW_MESSAGE } }, 403)
    );

    let thrown: unknown;
    try {
      await api.get("/v1/spaces");
    } catch (err) {
      thrown = err;
    }

    expect(mockOnTenantSelectionRequired).toHaveBeenCalledTimes(1);
    expect(thrown).toBeInstanceOf(Error);
    const message = (thrown as Error).message;
    expect(message).toContain("Please choose a company to continue.");
    expect(message).not.toContain("Credential is not scoped to a tenant");
  });

  it("keeps the ApiError code and status on interception", async () => {
    mockFetch.mockReturnValue(
      jsonResponse({ error: { code: "credential_not_scoped", message: RAW_MESSAGE } }, 403)
    );

    let thrown: unknown;
    try {
      await api.get("/v1/spaces");
    } catch (err) {
      thrown = err;
    }

    expect(thrown).toMatchObject({ code: "credential_not_scoped", status: 403 });
  });

  it("does not intercept other 403 codes", async () => {
    mockFetch.mockReturnValue(
      jsonResponse({ error: { code: "not_a_member", message: "Not a member of this company" } }, 403)
    );

    await expect(api.get("/v1/spaces")).rejects.toThrow("Not a member of this company");
    expect(mockOnTenantSelectionRequired).not.toHaveBeenCalled();
  });

  it("does not invoke the callback on successful responses", async () => {
    mockFetch.mockReturnValue(jsonResponse({ data: "ok" }));

    await api.get("/v1/spaces");
    expect(mockOnTenantSelectionRequired).not.toHaveBeenCalled();
  });
});
