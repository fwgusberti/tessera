# Data Model: Fix Company Membership space_id

## No Schema Changes

This feature requires no database schema changes. The defect is entirely in the application-layer mapping code.

## Affected Domain Entities (unchanged)

### CompanyMembership

| Field | Type | Source column |
|---|---|---|
| `id` | `UUID` | `company_memberships.id` |
| `user_id` | `UUID` | `company_memberships.user_id` |
| `company_id` | `UUID` | `company_memberships.company_id` |
| `role` | `CompanyRole` enum | `company_memberships.role` |
| `joined_at` | `datetime` | `company_memberships.joined_at` |

**Invariant**: `CompanyMembership` MUST NOT have a `space_id` field. It is scoped to a company, not a space.

### SpaceMembership (distinct — not conflated)

| Field | Type | Source column |
|---|---|---|
| `id` | `UUID` | `space_memberships.id` |
| `space_id` | `UUID` | `space_memberships.space_id` |
| `user_id` | `UUID` | `space_memberships.user_id` |
| `role` | `SpaceRole` enum | `space_memberships.role` |
| `invited_by_user_id` | `UUID \| None` | `space_memberships.invited_by_user_id` |
| `created_at` | `datetime` | `space_memberships.created_at` |
| `updated_at` | `datetime` | `space_memberships.updated_at` |

## Mapper Functions (post-fix)

| Function name | Input type | Output type | Location |
|---|---|---|---|
| `_company_membership_from_model` | `CompanyMembershipModel` | `CompanyMembership` | `repo.py:985` (renamed) |
| `_membership_from_model` | `SpaceMembershipModel` | `SpaceMembership` | `repo.py:1372` (unchanged) |
