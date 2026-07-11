# Contract: `UserBadge` component + `initials` helper

Client-side UI contract for the persistent identity badge in the primary
navigation. Presentational only — no interactive account menu (out of scope per
spec Assumptions).

## `initials(name: string | null | undefined, email: string): string`

Pure function. Returns a 1–2 character uppercase marker.

| Input                                   | Output |
|-----------------------------------------|--------|
| name `"Ada Lovelace"`, any email        | `"AL"` |
| name `"Ada"`, any email                 | `"AD"` |
| name `null`, email `"ada@example.com"`  | `"AD"` |
| name `""` (empty), email `"x@y.z"`      | `"X"` (email local-part) |
| name/email with surrounding whitespace  | trimmed before deriving |

Rules: prefer name; ≥2 words → first-of-first + first-of-last; 1 word → first two
letters; else email local-part's first two letters. Always uppercase, ≤2 chars.

## `<UserBadge />`

Consumes `useAuth()` and (when authenticated) `GET /v1/auth/me`.

### Rendering rules
- `status !== "authenticated"` → renders **nothing** (FR-004). While `status` is
  `"loading"`, render nothing or a neutral placeholder — never a misleading
  identity (spec "identity temporarily unavailable").
- Authenticated → render an avatar chip showing `initials(...)` plus text:
  - email always shown as the primary label (FR-002);
  - display name shown when `/auth/me` provides one, above/beside the email.
- Email renders **immediately** from `useAuth().user.email`; name + refined
  initials appear when `/auth/me` resolves (no blank flash).
- Long email/name uses `truncate` + `max-w-*`; full value exposed via `title`
  (FR-008).
- A desktop presentation (in the top bar) and a compact mobile presentation (in
  the mobile menu) are both provided (FR-009).

### Styling (constitution UI system)
- Neutrals: `slate-*`; accent: `indigo-*` (e.g. avatar `bg-indigo-100
  text-indigo-700`, mirroring `RoleBadge`). No `gray-*` or `blue-*`. No
  decorative gradients/shadows.

### Reactivity
- Re-derives when the authenticated user id changes (account switch → new
  identity, FR-005); shows nothing after sign-out.

## Tests (write first — TDD, Vitest + Testing Library)

**`initials` helper**
1. Two-word name → initials of first + last.
2. Single-word name → first two letters.
3. No name → email local-part initials.
4. Whitespace trimmed; output uppercase and ≤2 chars.

**`UserBadge`**
5. Unauthenticated (`status: "unauthenticated"`) → renders nothing.
6. Authenticated → shows email from `useAuth()` before `/auth/me` resolves.
7. After `/auth/me` resolves with a `display_name` → name is shown alongside
   email and initials reflect the name.
8. `/auth/me` returns `display_name: null` → email shown, initials from email.
9. Long email → truncated element carries full value in `title`.
10. Account switch (auth user id changes) → badge updates to the new identity.
