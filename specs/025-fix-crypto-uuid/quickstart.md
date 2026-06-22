# Quickstart: Validate the UUID Fix

**Feature**: 025-fix-crypto-uuid

---

## Prerequisites

- Node.js ≥ 18
- `cd apps/web && npm install` (dependencies already installed in the repo)

---

## Validation Scenarios

### 1. Unit tests pass (primary gate)

```bash
cd apps/web
npx vitest run tests/generate-id.test.ts
```

**Expected**: All three test cases pass — happy path (randomUUID available), fallback path (randomUUID stubbed away), and uniqueness.

### 2. Full test suite shows no regressions

```bash
cd apps/web
npx vitest run
```

**Expected**: All existing `chat.test.tsx` tests continue to pass. The mock for `askAssistant` already handles `randomUUID` internally via jsdom, so no test changes are needed.

### 3. TypeScript compilation is clean

```bash
cd apps/web
npx tsc --noEmit
```

**Expected**: Zero type errors.

### 4. Manual browser validation (HTTP dev context)

Start the dev server over a network interface (not `localhost`):

```bash
cd apps/web
HOSTNAME=0.0.0.0 npx next dev --turbopack --port 3000
```

Then open `http://<your-machine-ip>:3000` in a browser (not `http://localhost:3000`). This is a non-secure context where `crypto.randomUUID` is unavailable.

**Steps**:
1. Navigate to the chat page.
2. Type any question and press Enter or click "Ask".
3. Open browser DevTools console.

**Expected outcomes**:
- No `TypeError: crypto.randomUUID is not a function` error in the console.
- The question appears as a pending turn immediately after submission.
- The response appears once the server replies.
- Submitting multiple questions in rapid succession creates separate, independently rendered turns.

### 5. Secure context (HTTPS / localhost) — no regression

Open `http://localhost:3000` in a browser (secure context, `randomUUID` available).

**Expected**: Identical behavior to scenario 4 — the `if` branch is taken and `crypto.randomUUID()` is used directly.

---

## Success Criteria Cross-Reference

| Spec ID | Test / Scenario | Status |
|---|---|---|
| SC-001 | Scenarios 1, 4 | Validates no runtime error on submit |
| SC-002 | Scenario 1 (uniqueness test) | Validates unique IDs per turn |
| SC-003 | Scenario 2 (full suite), Scenario 4 | Validates no visible regressions |
