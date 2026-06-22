# Contract: generateId()

**Module**: `apps/web/lib/utils/generate-id.ts`

---

## Signature

```typescript
export function generateId(): string
```

## Guarantees

| # | Guarantee |
|---|---|
| 1 | Returns a non-empty string conforming to UUID v4 format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx` (lowercase hex, hyphens at positions 8, 12, 16, 20). |
| 2 | Works in all browser contexts — both secure (HTTPS) and non-secure (HTTP development). |
| 3 | Two successive calls within the same process will never return the same value (probabilistically guaranteed by the CSPRNG). |
| 4 | Has no side effects and performs no I/O. |

## Behavior by Environment

| Condition | Mechanism | Notes |
|---|---|---|
| `crypto.randomUUID` available (HTTPS / localhost) | Delegates directly to `crypto.randomUUID()` | Native, most efficient path |
| `crypto.randomUUID` unavailable (HTTP non-localhost) | Generates UUID v4 via `crypto.getRandomValues(new Uint8Array(1))` | `getRandomValues` works in non-secure contexts |

## Non-Guarantees

- Does **not** guarantee uniqueness across different browser tabs or sessions (no coordination across processes).
- Does **not** guarantee UUID v4 if `crypto` itself is unavailable (no non-browser polyfill is provided — this is a browser-only utility).

## Usage

```typescript
import { generateId } from "@/lib/utils/generate-id";

const turnId = generateId(); // "a3f1c2d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
```
