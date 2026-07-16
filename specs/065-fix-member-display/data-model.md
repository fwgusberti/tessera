# Data Model: Human-Readable Member Identity in User Management

**Feature**: `065-fix-member-display` | **Date**: 2026-07-12

No schema changes. All tables below already exist; this feature adds one
read-only domain projection over them.

## Existing entities (unchanged)

### SpaceMembership (write model)

`packages/core/tessera_core/domain/space_membership.py` — Pydantic entity
backing table `space_memberships`.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| space_id | UUID | FK → spaces.id |
| user_id | UUID | FK → users.id |
| role | SpaceRole | `admin` \| `editor` \| `viewer` |
| invited_by_user_id | UUID \| None | |
| created_at / updated_at | datetime \| None | |

Remains the model for all mutations (invite, change role, remove). Unchanged.

### User (identity source)

Table `users` (`UserModel`) — supplies the two identity facts:

| Field | Type | Notes |
|-------|------|-------|
| display_name | str | May be blank ("") — spec edge case |
| email | str | Always present for registered users (spec assumption) |

### Space (tenant scope anchor)

Table `spaces` carries `company_id`; joined by the new query solely to
enforce tenant scoping (Constitution VI). No fields returned from it.

## New entity

### SpaceMemberListing (read model / projection) — NEW

`packages/core/tessera_core/domain/space_member_listing.py` — plain class
(no framework imports), mirroring `CompanyMemberListing`.

| Field | Type | Source |
|-------|------|--------|
| id | UUID | space_memberships.id |
| space_id | UUID | space_memberships.space_id |
| user_id | UUID | space_memberships.user_id |
| display_name | str | users.display_name (may be "") |
| email | str | users.email |
| role | SpaceRole | space_memberships.role |
| invited_by_user_id | UUID \| None | space_memberships.invited_by_user_id |
| created_at | datetime \| None | space_memberships.created_at |
| updated_at | datetime \| None | space_memberships.updated_at |

**Relationships**: one `SpaceMemberListing` per `SpaceMembership` row of the
requested space; identity fields come from the joined `users` row
(inner join — a membership always references an existing user).

**Validation rules**:
- Produced only by
  `SpaceMembershipRepository.list_by_space_with_identity(space_id, company_id)`;
  the query MUST filter `spaces.company_id == company_id` (tenant scope) and
  MUST order by `users.display_name` (presentation default).
- `display_name` is passed through verbatim (blank allowed); fallback
  labeling is a presentation concern (see contract), not a data rule.

**State transitions**: none — read-only projection; all state changes go
through `SpaceMembership`.

## Port change

`packages/core/tessera_core/ports/repositories/space_membership.py`
(`SpaceMembershipRepository`) gains:

```python
@abstractmethod
async def list_by_space_with_identity(
    self, space_id: UUID, company_id: UUID
) -> list[SpaceMemberListing]: ...
```

Existing methods are untouched. `list_by_space` remains for callers that need
bare memberships (permission checks in other routes, MembershipService).
