# Data Model: Add Space

No new entities and no schema/migration change. This feature adds a creation
pathway and two small behaviors (slug auto-derivation, sector default) around
one existing entity.

## Space (existing — `packages/core/tessera_core/domain/space.py`)

| Field | Type | Change |
|-------|------|--------|
| `slug` | `str` | Now optional in the *request* (`CreateSpaceRequest.slug: str \| None`); always populated on the persisted `Space` — either the caller's explicit value (unchanged admin-console path) or an auto-derived, collision-checked value. Still `String(100) UNIQUE NOT NULL` at the DB layer; no migration. |
| `name` | `str` | Unchanged validation: non-empty after trim, ≤255 chars — reuses the exact rule already enforced by `SpaceHierarchyService.rename` (049). |
| `sector` | `str` | Now optional in the request, defaulting to `"General"` when omitted. Still `String NOT NULL` at the DB layer; no migration. |
| `parent_space_id` | `UUID \| None` | Now settable **at creation time** via an optional request field, in addition to the existing post-creation `PATCH /spaces/{id}/parent` path. When set, subject to the same validation `set_parent` already enforces (see below). |
| all other fields (`taxonomy`, `retention_policy`, `confidence_threshold`, `default_language`, `company_id`, timestamps) | — | Unchanged. `company_id` is still always derived from the authenticated `CompanyContext`, never from the request body. |

### Validation rules

- `name`, after trimming, MUST be non-empty and ≤255 characters (FR-003) — same
  rule as rename (049), enforced in `SpaceHierarchyService.create` before any
  write.
- If `slug` is omitted, it is derived from `name` via `slugify()` and checked
  against `SpaceRepository.slug_exists`; on collision, a numeric suffix
  (`-2`, `-3`, ...) is appended until unique, truncated to fit the 100-char
  column. If `slug` is explicitly provided (admin console), it passes through
  unchanged, preserving existing behavior.
- If `sector` is omitted or blank, it defaults to `"General"`.
- If `parent_space_id` is provided:
  - It MUST resolve to a space in the caller's own company
    (`get_by_id_for_company`); otherwise rejected (FR-011, cross-tenant case).
  - The caller MUST hold `SpaceRole.ADMIN` on that parent space; otherwise
    rejected (mirrors `set_parent`'s child/parent admin requirement).
  - Placing the new space under that parent MUST NOT exceed the existing
    maximum nesting depth (`_MAX_DEPTH = 10`, same constant `set_parent` already
    enforces) (FR-006).
  - No cycle check is needed — the space does not exist yet, so it cannot be its
    own ancestor.
- Duplicate `name` values across spaces in the same company remain allowed
  (FR-009) — no uniqueness constraint on `name`, consistent with existing
  create/rename behavior.

### State transition

```
(none) --create(actor, company_id, name, sector?, slug?, parent_space_id?)-->
  Space{name, sector: sector ?? "General", slug: slug ?? derived, parent_space_id}
--grant creator SpaceMembership(role=ADMIN)-->
  actor now has full administrative access to the new space
```

## SpaceMembership (existing — write path, unchanged shape)

A `SpaceMembership(space_id=<new space>, user_id=<creator>, role=SpaceRole.ADMIN)`
row is created immediately after the space itself, exactly as today (042) — this
feature does not change how or when that grant happens, only what creation
options can precede it (e.g., a supplied `parent_space_id`).

## AuditRecord (existing — write path, new action)

Two audit records are now written on successful creation (previously one):

| Field | Value |
|-------|-------|
| `actor_type` | `"user"` |
| `actor_id` | the creating user's ID |
| `action` | `"space_created"` **(new)** |
| `entity_type` | `"space"` |
| `entity_id` | the new space's ID |
| `metadata` | `{"company_id": <company id>, "parent_space_id": <parent id or null>}` |

followed by the existing:

| Field | Value |
|-------|-------|
| `actor_type` | `"user"` |
| `actor_id` | the creating user's ID |
| `action` | `"member_invited"` (unchanged) |
| `entity_type` | `"space_membership"` |
| `entity_id` | the new membership's ID |
| `metadata` | `{"space_id", "user_id", "role": "admin"}` (unchanged) |

No new columns or tables — both use the existing `write_audit` adapter already
imported in `apps/api/tessera_api/routers/spaces.py`.
