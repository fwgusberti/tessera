# Data Model: Fix Document Publish — Auto-Assign Owner

## Affected Entities

### Document (existing — no schema change)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `UUID` | Primary key |
| `space_id` | `UUID` | FK to Space |
| `owner_user_id` | `UUID \| None` | **Set at creation time** (previously left as None) |
| `title` | `str` | |
| `language` | `str` | Default `"pt-BR"` |
| `confidentiality` | `Confidentiality` | |
| `tags` | `list[str]` | |
| `validity_until` | `date \| None` | |
| `state` | `DocumentLifecycleState` | `INGESTED → PUBLISHED` on publish |
| `current_version_id` | `UUID \| None` | |
| `created_at` / `updated_at` | `datetime \| None` | |

**Change**: `owner_user_id` is populated from the authenticated creator's ID in `POST /documents`. No column migration required — the column already exists as nullable.

---

## No New Entities

This fix does not introduce any new domain entities, database tables, or migrations. It populates an existing nullable column at the correct lifecycle moment.

---

## State Transitions (unchanged)

```
INGESTED ──(publish with owner)──▶ PUBLISHED
INGESTED ──(publish, owner was None → auto-assigned)──▶ PUBLISHED
OUTDATED ──(publish with owner)──▶ PUBLISHED
```

`assign_owner()` does not change state — it is applied before `publish_document()` in the case of legacy documents.

---

## User Identity in Auth Token

The authenticated user is extracted from the JWT `sub` claim (a UUID string equal to `user.id`) or the session cookie. After the `require_user` fix, `user_info["id"]` is always available and equals the database `User.id`.
