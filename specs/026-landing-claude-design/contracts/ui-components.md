# UI Component Contracts: Landing Page Claude-Chat Design

## ChatInterface

**File**: `apps/web/components/chat/ChatInterface.tsx`

**Props**: None (unchanged). The component owns all state internally.

**Behavior contract**:

| Condition | Rendered view |
|-----------|--------------|
| `turns.length === 0` | Welcome view (FR-001, FR-002, FR-003, FR-004) |
| `turns.length > 0` | Conversation view (FR-005, FR-006, FR-007) |

### Welcome view layout

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│                     (centered)                         │
│                                                        │
│              Tessera                                   │
│     Your knowledge, always answered.                   │
│                                                        │
│  ┌──────────────────────────────────────────┐ [Ask]   │
│  │ Ask your question…                       │         │
│  └──────────────────────────────────────────┘         │
│                                                        │
│  [What's in our product roadmap?]                     │
│  [Summarize the latest meeting notes]                  │
│  [Find our onboarding documentation]                   │
│  [What changed in the last release?]                   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

- `h1`: "Tessera" — `text-4xl font-bold text-slate-900`
- Tagline: `text-lg text-slate-500`
- Textarea + Ask button: centered, `max-w-2xl`
- Starter-prompt chips: `flex flex-wrap gap-2 justify-center`

### Conversation view layout

```
┌────────────────────────────────────────────────────────┐
│  Tessera                      [New conversation]       │
├────────────────────────────────────────────────────────┤
│  ↑ scrollable message history                          │
│                                                        │
│  [MessageBubble for each turn]                         │
│                                                        │
│  ↓ scrollable message history                          │
├────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐ [Ask]        │  ← sticky bottom
│  │ Ask your question…                   │              │
│  └──────────────────────────────────────┘              │
└────────────────────────────────────────────────────────┘
```

- Header: `text-xl font-semibold text-slate-900` + "New conversation" text button
- Messages: natural flow, no explicit overflow container (body scrolls)
- Input bar: `position: sticky; bottom: 0; background: white; border-top`
- Input bar max-width: `max-w-3xl mx-auto`

**Preserved behaviors** (existing tests must still pass):
- Textarea (`role="textbox"`) always present
- Ask button (`role="button", name=/ask/i`) always present
- Ask button disabled when input is empty or whitespace
- On submit: `askAssistant(question, history)` called, input cleared
- On error: input restored with the failed question
- "New conversation" button appears only when `turns.length > 0`
- Clicking "New conversation" clears all turns

---

## StarterPromptChip (internal sub-component or inline)

**Not exported**. Used only inside `ChatInterface` welcome view.

**Props**:
```ts
{ label: string; onClick: () => void }
```

**Visual**: `rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:border-indigo-400 hover:text-indigo-600 transition-colors bg-white`

**Behavior**: clicking calls `setInput(label)` and `inputRef.current?.focus()`.

---

## Landing page (`app/page.tsx`)

**Before** (removed): `StatCard`, `NavCard`, stats fetch (`/v1/spaces`, `/v1/metrics`), loading state.

**After**: `AuthGuard` → full-height wrapper → `<ChatInterface />`.

```tsx
<AuthGuard>
  {/* min-h accounts for NavBar (py-3 + text-xl = 3.25rem) */}
  <div className="-mx-4 -my-8 min-h-[calc(100dvh-3.25rem)] flex flex-col">
    <ChatInterface />
  </div>
</AuthGuard>
```

**Rationale for `-mx-4 -my-8`**: The root `<main>` has `px-4 py-8`; the negative margins undo that padding so the chat fills edge-to-edge and top-to-bottom within the available viewport area below the NavBar.
