# Phase 1 Data Model: Close Company & User Scope Gaps

This feature hardens scoping on **existing** entities. There is exactly one
schema change; every other gap is closed by adding `company_id`-filtered queries
over columns that already exist.

## Tenant-ownership graph (how each resource reaches `company_id`)

```text
companies (company_id)
└── spaces.company_id                      [added in 031, migration 0007]
    ├── documents.space_id
    │   └── update_proposals.document_id   ← US1 scoped via this chain
    ├── connectors.space_id                ← US2 scoped via this chain
    ├── role_permissions.space_id          ← US4 (validate space first)
    └── space_memberships.space_id         ← US4 (validate space first)

agent_credentials.company_id               ← US3 NEW column (migration 0009)
agent_credentials.scoped_space_ids[]       → each must belong to company_id

audit_records.metadata->>'company_id'      ← US5 tag on "query" records
company_memberships.role (ADMIN|MEMBER)    ← US6 authorization source
```

## Schema change — migration `0009_agent_credential_company_id.py`

Add a tenant-owning column to `agent_credentials`.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `company_id` | `UUID` FK → `companies.id` | YES (nullable) | Set on issuance going forward; backfilled for existing rows from the company of the first scoped space. |

- **Index**: `ix_agent_credentials_company` on `company_id` (scoped lookups).
- **Backfill**: `UPDATE agent_credentials ac SET company_id = (SELECT s.company_id
  FROM spaces s WHERE s.id = ac.scoped_space_ids[1])` for rows with ≥1 scoped
  space; rows with none stay NULL.
- **Downgrade**: drop the index and column.
- Nullable (not NOT NULL) so the backfill cannot fail on legacy rows with empty
  `scoped_space_ids`; the issuance path always populates it.

## Domain entity change

`packages/core/tessera_core/domain/entities.py` — `AgentCredential`:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `company_id` | `UUID \| None` | `None` | Owning company; set at issuance. Pure data attribute — no framework import (Principle I/II). |

`Connector`, `UpdateProposal`, `RolePermission`, `SpaceMembership`,
`CompanyMembership` entities are **unchanged**.

## Repository methods (new / changed)

`packages/core/tessera_core/ports/repositories.py` interfaces gain the scoped
signatures; `apps/api/tessera_api/adapters/repo.py` implements them.

| Repository | New method | Query |
|------------|-----------|-------|
| `SqlProposalRepository` | `get_by_id_for_company(proposal_id, company_id)` | `UpdateProposalModel` join `DocumentModel` join `SpaceModel` where `SpaceModel.company_id == company_id`. Returns `None` on miss. |
| `SqlProposalRepository` | `list_for_company(company_id, state=None, space_id=None)` | Same join, plus optional `state` / `space_id` filters. |
| `SqlConnectorRepository` | `get_by_id_for_company(connector_id, company_id)` | `ConnectorModel` join `SpaceModel` where `SpaceModel.company_id == company_id`. |
| `SqlAgentCredentialRepository` | `get_by_id_for_company(credential_id, company_id)` | `AgentCredentialModel` where `company_id == company_id`. |

Existing `SqlSpaceRepository.get_by_id_for_company` and the `validate_space_for_company`
helper (spaces.py) are reused for connector-create, agent-credential issuance,
and member/permission writes — no change.

## Authorization element (US6)

No new entity. A new transport dependency `require_company_admin` reads the
`CompanyMembership.role` already returned by `require_company_context`:

| Element | Source | Rule |
|---------|--------|------|
| Per-company admin | `company_memberships.role == 'admin'` for `(user_id, active company_id)` | Required for connector create/sync, agent-credential issue/revoke, role-permission create, metrics. |
| Platform super-admin | JWT `is_admin` / `users.is_admin` | Retained ONLY for `PUT /v1/users/{id}/platform-role`. |

## Audit records (FR-013 / FR-008)

No schema change to `audit_records`.

| Record | When | Key fields |
|--------|------|-----------|
| `cross_tenant_denied` | Any hardened flow denies a cross-company access | `action="cross_tenant_denied"`, `entity_type` ∈ {`proposal`,`connector`,`agent_credential`,`space`,`role_permission`}, `entity_id`, `metadata={"company_id": …}` |
| `query` (augmented) | Assistant query (existing record) | now also `metadata={"company_id": …}` so `total_queries` can be scoped |

## Validation rules (enforced in handlers/domain)

- A proposal/connector/credential/space resolved for a non-owning company MUST
  behave identically to a missing row (403, generic body) — FR-010.
- Agent-credential issuance MUST reject if **any** `scoped_space_id` is not in
  the active company — FR-006.
- Approve/reject MUST additionally pass `can_approve_proposal` for the caller in
  the target document's space — FR-004.
- Member/permission writes MUST pass `validate_space_for_company` before the
  domain role check — FR-007.
- No company context → 403 for all of the above — FR-011; revoked membership →
  403 via `require_company_context`'s DB re-check — FR-012.
