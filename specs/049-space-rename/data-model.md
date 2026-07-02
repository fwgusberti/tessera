# Data Model: Space Rename

No new entities and no schema change. This feature mutates one existing field on
one existing entity.

## Space (existing — `packages/core/tessera_core/domain/space.py`)

| Field | Type | Change |
|-------|------|--------|
| `name` | `str` | Mutable via this feature. Already `String(255) NOT NULL` at the DB layer (`apps/api/tessera_api/adapters/models/space.py`); no migration required. |
| all other fields | — | Unchanged. Rename MUST NOT touch `slug`, `parent_space_id`, `sector`, `taxonomy`, `retention_policy`, `confidence_threshold`, `default_language`. |

### Validation rules (FR-004)

- `name`, after trimming leading/trailing whitespace, MUST be non-empty.
- `name` MUST be ≤ 255 characters (matches the existing DB column width; no new
  constraint introduced).
- Duplicate names across spaces in the same company remain allowed (FR-008) — no
  uniqueness constraint is added.
- Submitting the current name unchanged is accepted as a no-op success (per the
  spec's Edge Cases).

### State transition

```
Space{name: "Old Name"} --rename(actor: admin, new_name: "New Name")--> Space{name: "New Name"}
```

No other fields change as a side effect. `updated_at` is refreshed by the existing
`onupdate=func.now()` behavior already present on `SpaceModel`, same as for
`set_parent`/`remove_parent`.

## SpaceMembership (existing — read-only for this feature)

Used only to check that the acting user holds the `ADMIN` `SpaceRole` on the space
being renamed. No write. Same read pattern as `SpaceHierarchyService.set_parent`'s
child-admin check.

## AuditRecord (existing — write path)

A new audit record is written on successful rename:

| Field | Value |
|-------|-------|
| `actor_type` | `"user"` |
| `actor_id` | the renaming user's ID |
| `action` | `"space_renamed"` |
| `entity_type` | `"space"` |
| `entity_id` | the space's ID |
| `metadata` | `{"new_name": <new name>}` |

No new columns or tables — this uses the existing `write_audit` adapter already
imported in `apps/api/tessera_api/routers/spaces.py`.
