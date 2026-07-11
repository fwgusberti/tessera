# Phase 1 Data Model: User Badge

This feature introduces **no persistent schema changes**. It reads existing data
and defines transient view/response shapes only.

## Existing entity read (unchanged)

### User (existing `users` table)
Only the caller's own row is read, by primary key from the verified token
subject. Relevant fields:

| Field          | Type        | Used for                                  |
|----------------|-------------|-------------------------------------------|
| `id`           | UUID        | Identity key (equals token `sub`)         |
| `email`        | string      | Primary badge label (FR-002)              |
| `display_name` | string/null | Secondary label + initials when available |
| `is_admin`     | bool        | Passed through for parity with token      |

No `company_id` scoping applies — the read is single-subject (the authenticated
principal's own row). See plan.md → Tenant Isolation.

## Transient shapes (no persistence)

### MeResponse (API → client, `GET /v1/auth/me`)
```
{
  "id":           string (UUID),
  "email":        string,
  "display_name": string | null,
  "is_admin":     boolean
}
```
- Derived solely from the token subject and that user's own row.
- `display_name` is `null` when the user has not set one (fallback to email).

### BadgeIdentity (web, in-memory view model)
Assembled by `UserBadge` from `useAuth().user` (immediate) + `MeResponse`
(enriched):

| Field       | Source                                  | Notes                          |
|-------------|-----------------------------------------|--------------------------------|
| `email`     | `useAuth().user.email` → `MeResponse`   | Rendered immediately           |
| `name`      | `MeResponse.display_name`               | Optional; omitted when null    |
| `initials`  | `initials(name, email)` pure helper     | 1–2 uppercase chars (FR-007)   |

## Validation & derivation rules

- **Initials (FR-007)**: `initials(name?, email)` →
  - name with ≥2 words → first letter of first + last word;
  - single-word name → first two letters of that word;
  - no name → first two letters of email local-part.
  - Always uppercased, max 2 characters.
- **Truncation (FR-008)**: email/name text truncates within its container; full
  value remains discoverable via the element `title` attribute.
- **Visibility (FR-004)**: badge renders `null` unless
  `status === "authenticated"`.
- **Isolation (FR-006)**: badge contents come only from the current session's own
  identity; no other account's data is fetched or shown.

## State transitions

| Event                          | Badge behavior                                   |
|--------------------------------|--------------------------------------------------|
| Not signed in / signing in     | Not rendered (or neutral placeholder pre-identity) |
| Sign-in completes              | Renders email immediately; enriches with name    |
| Navigate between pages         | Remains rendered (lives in persistent NavBar)    |
| Switch account (out then in)   | Re-derives from new session; badge reflects new  |
| Sign-out / session expiry      | Removed from view                                |
