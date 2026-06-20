# Data Model: Fix Publish — Record Approval on Existing Version

## Affected Entities

### DocumentVersion (existing — no schema change)

| Field | Type | Mutability | Notes |
|---|---|---|---|
| `id` | `UUID` | Immutable | Primary key |
| `document_id` | `UUID` | Immutable | FK to Document |
| `version_number` | `int` | Immutable | Unique per document |
| `content_markdown` | `str` | Immutable | Content body |
| `frontmatter` | `dict` | Immutable | Metadata blob |
| `author_user_id` | `UUID \| None` | Immutable | Set at creation |
| `approver_user_id` | `UUID \| None` | **Mutable** | Set at publish time |
| `approved_at` | `datetime \| None` | **Mutable** | Set at publish time |
| `source_artifact_id` | `UUID \| None` | Immutable | |
| `created_from_proposal_id` | `UUID \| None` | Immutable | |
| `created_at` | `datetime \| None` | Immutable | |

**Change**: `approver_user_id` and `approved_at` were already nullable. The fix correctly mutates them in-place via an UPDATE query rather than inserting a duplicate row.

**Uniqueness constraint (existing)**: `(document_id, version_number)` — this is what the old INSERT violated. The UPDATE does not touch these fields, so no constraint risk.

---

## New Port Method

### `DocumentVersionRepository.update_approval`

Added to the abstract port in `tessera_core/ports/repositories.py`:

```
update_approval(version_id: UUID, approver_id: UUID, approved_at: datetime) → DocumentVersion
```

**Semantics**: SET `approver_user_id = approver_id`, `approved_at = approved_at` WHERE `id = version_id`. Returns the updated version.

**No migration needed** — existing columns updated, no schema change.

---

## State Transitions (unchanged)

```
INGESTED ──(publish)──▶ PUBLISHED
OUTDATED ──(publish)──▶ PUBLISHED
```

Approval metadata is recorded on the existing version during the INGESTED→PUBLISHED or OUTDATED→PUBLISHED transition. No new version record is created.
