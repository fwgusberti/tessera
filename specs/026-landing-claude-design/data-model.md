# Data Model: Landing Page Claude-Chat Design

## No backend changes

This feature is purely a UI layout change. No new database tables, API endpoints, or server-side data structures are introduced.

## In-memory React state (unchanged)

The existing `ChatTurn` and `HistoryMessage` types in `apps/web/lib/types.ts` are used without modification.

```ts
// Existing — no changes
type ChatTurn = {
  id: string;
  question: string;
  answer: AssistantAnswer | null;
  status: "pending" | "complete" | "error";
  errorMessage?: string;
};

type HistoryMessage = {
  role: "user" | "assistant";
  content: string;
};
```

## New: StarterPrompt (hardcoded constant)

A `StarterPrompt` is not persisted or fetched — it is a static UI construct. It is represented as a plain string array (no dedicated type needed).

```ts
// Inside ChatInterface.tsx — module-level constant
const STARTER_PROMPTS = [
  "What's in our product roadmap?",
  "Summarize the latest meeting notes",
  "Find our onboarding documentation",
  "What changed in the last release?",
] as const;
```

**Why a plain string array**: The prompts have no ID, icon, or metadata. A `StarterPrompt` object type would be premature structure for 4 static strings.

## Layout state (derived, not stored)

The ChatInterface layout mode (`welcome` vs `conversation`) is derived from `turns.length`:

- `turns.length === 0` → welcome view
- `turns.length > 0` → conversation view

No additional state variable is needed.
