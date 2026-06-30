# Research: Frontend Spaces Page

## API Shape — GET /v1/spaces

**Decision**: Use `GET /v1/spaces` as the primary data source.

**Rationale**: Already exists, returns `{ spaces: Space[] }` scoped to the authenticated company. No backend changes needed.

**Response shape** (observed in `apps/api/tessera_api/routers/spaces.py`):
```json
{
  "spaces": [
    {
      "id": "uuid",
      "slug": "engineering",
      "name": "Engineering",
      "sector": "Tech",
      "default_language": "en",
      "confidence_threshold": 0.7,
      "retention_policy": {}
    }
  ]
}
```

**Tenant scoping**: Enforced server-side via `company_id` extracted from the JWT. The frontend has no control over, or responsibility for, this scoping.

---

## Role Per Space — Strategy

**Decision**: Make parallel `GET /v1/spaces/{id}/members/me` calls (one per space) after the spaces list loads, using `Promise.allSettled`.

**Rationale**: The existing `GET /v1/spaces` response does not include the user's role. Options evaluated:

1. **Parallel per-space calls** (chosen): `Promise.allSettled` over all space IDs. Settled (not all-or-nothing) so a single failed role fetch doesn't break the whole page; graceful degradation shows no badge instead of crashing. Acceptable because space count per company is small (spec assumption: no pagination needed).
2. **Backend enhancement** (`GET /v1/spaces` returning `my_role`): Would require backend changes, contradicting the spec assumption "no backend changes are required."
3. **Sequential calls**: Worst-case latency O(N). Rejected in favor of parallel.

**Response shape** (observed in `apps/api/tessera_api/routers/members.py`):
```json
{
  "membership": {
    "space_id": "uuid",
    "user_id": "uuid",
    "role": "admin" | "editor" | "viewer",
    "created_at": "iso8601"
  }
}
```

**Edge case**: If `members/me` returns 404 (user is not a member of the space), no role badge is shown — the card still renders. This handles spaces the user has access to via IDP group permissions but no direct membership record.

---

## Alphabetical Sort — Client-Side

**Decision**: Sort spaces by `name` in the frontend after fetching, using `localeCompare`.

**Rationale**: The API doesn't guarantee order; sorting client-side is trivial and avoids a backend query change.

---

## Active State Detection for NavBar

**Decision**: Check `pathname.startsWith("/spaces")` for the "Spaces" link active state.

**Rationale**: Consistent with the existing Documents link pattern (`pathname?.startsWith("/documents")`). Covers both `/spaces` and `/spaces/[id]/members`.

---

## Component Architecture

**Decision**: Two new files — `app/spaces/page.tsx` (page) and `components/spaces/SpaceCard.tsx` (card).

**Rationale**: Mirrors the existing pattern:
- Pages live in `app/<route>/page.tsx` (e.g., `app/documents/page.tsx`)
- Reusable components live in `components/<domain>/Component.tsx` (e.g., `components/members/RoleBadge.tsx`)

Separating `SpaceCard` into its own component makes it independently testable and keeps the page lean.

---

## URL Navigation from Space Cards

**Decision**:
- Members link: `/spaces/${space.id}/members` (existing route)
- Documents link: `/documents?space=${space.id}` (existing filter, confirmed in spec 020)

**Rationale**: Both routes already exist; these are pure `<a>` links matching the pattern used throughout the app.

---

## Testing Approach

**Decision**: Vitest + @testing-library/react with jsdom, `vi.mock` for `@/lib/api` and `next/navigation`.

**Rationale**: Consistent with all existing frontend tests (`tests/documents.test.tsx`, `tests/navbar.test.tsx`). Tests mock the API and assert on rendered output. `Promise.allSettled` behavior is tested by having some role calls fail/succeed selectively.

**Alternatives considered**: Contract/integration tests — out of scope for a pure rendering feature with no new API endpoints.
