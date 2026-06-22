import { describe, it, expect, vi, afterEach } from "vitest";
import { generateId } from "@/lib/utils/generate-id";

describe("generateId", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns a UUID-format string when crypto.randomUUID is available", () => {
    const uuid = generateId();
    expect(uuid).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  it("returns a UUID-format string using getRandomValues fallback when randomUUID is unavailable", () => {
    vi.spyOn(crypto, "randomUUID").mockImplementation(undefined as never);
    const uuid = generateId();
    expect(uuid).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  it("returns unique values on consecutive calls", () => {
    const a = generateId();
    const b = generateId();
    expect(a).not.toBe(b);
  });
});
