# Research: Fix Chat Submit Crash on UUID Generation

**Feature**: 025-fix-crypto-uuid  
**Phase**: 0 — Research

---

## Root Cause

**Decision**: `crypto.randomUUID()` is restricted to [Secure Contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts) (HTTPS + `localhost`).

**Rationale**: The Web Crypto API's `randomUUID()` method is only available when the browser considers the page origin "secure". On HTTP (including `http://0.0.0.0` or `http://192.168.x.x` development servers that are not `localhost`), the method is `undefined`, so calling it throws `TypeError: crypto.randomUUID is not a function`.

**Affected line**: `ChatInterface.tsx:27` — `const turnId = crypto.randomUUID();`

---

## Fix Options Evaluated

### Option A: `uuid` npm package

- **Pros**: Well-known, battle-tested, works everywhere, no custom code.
- **Cons**: Adds a new runtime dependency for a one-liner problem. Package is 2 kB gzipped but unnecessary.
- **Rejected because**: Adding a dependency for something solvable in ~6 lines of native code adds permanent maintenance surface.

### Option B: `Math.random()`-based generator

- **Pros**: Zero dependencies, works anywhere.
- **Cons**: `Math.random()` is not cryptographically random. UUID v4 is supposed to use a CSPRNG. In practice the IDs are only used as ephemeral React keys within a single browser session, so security is not a concern — but it violates the letter of the UUID v4 spec.
- **Rejected because**: `crypto.getRandomValues()` (Option C) is available in all relevant contexts and maintains the cryptographic quality.

### Option C: `crypto.getRandomValues()` fallback (chosen)

- **Pros**: `crypto.getRandomValues()` is available in all browsers including non-secure contexts (it predates the secure-context restriction on `randomUUID`). Produces genuine UUID v4. No new dependency. One small utility function.
- **Cons**: Slightly more code than a single `crypto.randomUUID()` call.
- **Chosen because**: Meets all requirements (unique, cryptographically random, no dependencies, works in HTTP dev environments) with minimal code.

---

## Implementation Decision

**Decision**: Extract a `generateId()` utility that calls `crypto.randomUUID()` when available and falls back to a `crypto.getRandomValues()`-based UUID v4 generator.

**Placement**: `apps/web/lib/utils/generate-id.ts` — consistent with the existing `lib/` layer pattern.

**Test strategy**: Vitest + jsdom already exposes `crypto.randomUUID`. Tests will cover:
1. Happy path (randomUUID available) — returns a UUID-shaped string.
2. Fallback path (randomUUID stubbed as `undefined`) — returns a UUID-shaped string from `getRandomValues`.
3. Uniqueness — consecutive calls return different values.

---

## jsdom Compatibility Confirmed

jsdom (version used: `^24.1.3`) provides `crypto.randomUUID` via `@sinonjs/fake-timers` + node:crypto bridge. Both `randomUUID` and `getRandomValues` are available. The fallback can be exercised in tests by temporarily setting `crypto.randomUUID = undefined`.
