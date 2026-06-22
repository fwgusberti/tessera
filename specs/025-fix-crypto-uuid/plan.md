# Implementation Plan: Fix Chat Submit Crash on UUID Generation

**Branch**: `025-fix-crypto-uuid` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/025-fix-crypto-uuid/spec.md`

---

## Summary

The chat interface crashes on submit because `crypto.randomUUID()` is only available in secure browser contexts (HTTPS + `localhost`). The fix extracts a `generateId()` utility that calls `randomUUID()` when available and falls back to `crypto.getRandomValues()`-based UUID v4 generation for HTTP development environments. No server-side changes, no new dependencies, and no visible behaviour changes are required.

---

## Technical Context

**Language/Version**: TypeScript 5, React 19

**Primary Dependencies**: Next.js 15.5 (app router), Vitest 2, @testing-library/react 16, jsdom 24

**Storage**: N/A — `turnId` is ephemeral client-side React state; it is never persisted

**Testing**: Vitest + jsdom + @testing-library/react (existing stack in `apps/web`)

**Target Platform**: Browser — both HTTPS production and HTTP development (non-secure contexts)

**Project Type**: Web application (Next.js frontend, `apps/web`)

**Performance Goals**: UUID generation is O(1) and imperceptible; no new latency introduced

**Constraints**: No new npm runtime dependencies; fix must work in jsdom test environment; TypeScript strict mode must pass

**Scale/Scope**: Single utility function (~6 lines) + one `ChatInterface.tsx` call site change

---

## Constitution Check

*GATE: Checked before Phase 0. Rechecked after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Domain-Driven Architecture | ✅ Compliant | Fix is in the component/utility layer; no domain model touched |
| II. Separation of Concerns | ✅ Compliant | UUID generation extracted into a dedicated utility |
| III. Data Locality & Consent | ✅ Compliant | `turnId` is ephemeral client state, never persisted |
| IV. TDD (non-negotiable) | ✅ Compliant | Tests written for `generateId()` covering both code paths and uniqueness |
| V. Quality Gates | ✅ Compliant | `tsc --noEmit` must pass; frontend has no Ruff/Black obligation |
| UI Design System | ✅ Compliant | No UI changes; no new Tailwind classes |

No violations. Complexity Tracking section is empty.

---

## Project Structure

### Documentation (this feature)

```text
specs/025-fix-crypto-uuid/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── generate-id.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code

```text
apps/web/
├── lib/
│   └── utils/
│       └── generate-id.ts     # NEW — UUID utility with getRandomValues fallback
├── components/
│   └── chat/
│       └── ChatInterface.tsx   # MODIFIED — import generateId, replace randomUUID call
└── tests/
    └── generate-id.test.ts    # NEW — unit tests for generateId utility
```

**Structure Decision**: Single Next.js web app (`apps/web`). Change is entirely in the frontend layer — no backend, no new apps or packages.

---

## Implementation Details

### New File: `apps/web/lib/utils/generate-id.ts`

```typescript
export function generateId(): string {
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) => {
    const n = parseInt(c, 10);
    return (
      n ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (n / 4)))
    ).toString(16);
  });
}
```

The template string `"10000000-1000-4000-8000-100000000000"` is a standard RFC 4122 UUID v4 skeleton. Digits `0`, `1`, and `8` are the only positions that vary based on the random byte; all other characters are literal hex digits or hyphens already correct for UUID v4.

### Modified File: `apps/web/components/chat/ChatInterface.tsx`

One call site change at line 27:

```diff
- const turnId = crypto.randomUUID();
+ const turnId = generateId();
```

Plus the import at the top of the file:

```diff
+ import { generateId } from "@/lib/utils/generate-id";
```

### New File: `apps/web/tests/generate-id.test.ts`

Three test cases (see quickstart.md for scenarios):
1. **Happy path**: `crypto.randomUUID` available → returns UUID-format string.
2. **Fallback path**: `crypto.randomUUID` stubbed to `undefined` → returns UUID-format string via `getRandomValues`.
3. **Uniqueness**: two consecutive calls return different strings.

---

## Phase 0 Artifacts

- [research.md](research.md) — Root cause analysis and option evaluation

## Phase 1 Artifacts

- [data-model.md](data-model.md) — No persistent model changes; ephemeral `ChatTurn.id` field unchanged
- [contracts/generate-id.md](contracts/generate-id.md) — `generateId()` function contract
- [quickstart.md](quickstart.md) — Validation scenarios for manual and automated testing
