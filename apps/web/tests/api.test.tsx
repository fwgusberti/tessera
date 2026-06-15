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
