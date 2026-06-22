import { vi, describe, it, expect, beforeEach } from "vitest";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import { api, configureApi } from "@/lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  configureApi({
    getAccessToken: () => "tok",
    refreshIfNeeded: async () => "tok",
    forceRefresh: async () => "tok",
    onUnauthorized: () => {},
  });
});

describe("api / network error handling", () => {
  it("translates TypeError 'Failed to fetch' to a user-friendly message", async () => {
    mockFetch.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(api.post("/v1/companies", { name: "X" })).rejects.toThrow(
      "Could not reach the server. Please check your connection and try again."
    );
  });
});
