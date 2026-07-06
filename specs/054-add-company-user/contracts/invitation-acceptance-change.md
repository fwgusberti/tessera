# Contract Change: Invitation Acceptance Grants the Assigned Role

**Endpoint**: `POST /v1/companies/{company_id}/join` (existing), `method="invitation"` branch.

## Before

On accepting an invitation the caller was always granted `CompanyRole.MEMBER`:

```python
await company_repo.add_membership(
    CompanyMembership(user_id=user_id, company_id=company_id, role=CompanyRole.MEMBER)
)
# response: "role": "member"
```

## After (FR-011)

The membership is created with the role stored on the invitation at invite time:

```python
await company_repo.add_membership(
    CompanyMembership(user_id=user_id, company_id=company_id, role=invitation.role)
)
# response: "role": invitation.role.value
```

## Behavior

- An invitee whose invitation was created with `role="admin"` becomes a company
  **administrator** on acceptance; `role="member"` (or a legacy invitation with no
  explicit role, defaulted to `member`) becomes a **member**.
- No other part of the join flow changes: the pending/expired/already-member
  guards, `update_status(ACCEPTED)`, onboarding advance, and audit log are
  unchanged.
- **Backward compatibility**: invitations created before migration `0015` (and by
  the legacy bulk `POST /invitations`) carry `role="member"` via the column
  default, so acceptance behavior for them is identical to today.

## Test

- Accepting an `admin`-role invitation yields a `company_memberships` row with
  `role="admin"` and a response `"role": "admin"` (SC-006).
- Accepting a `member`-role / legacy invitation yields `role="member"` (regression
  guard on existing behavior).
