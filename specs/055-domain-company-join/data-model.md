# Phase 1 Data Model: Domain-Based Company Matching on Sign-Up

**No new tables or columns.** This feature reuses existing entities and changes
only *when a `DomainJoinPolicy` row is written* and *how it is classified*. The
model below documents the entities as they participate in this flow and the
invariants this feature enforces.

## Entities (existing — participation in this feature)

### DomainJoinPolicy  (`domain_join_policies`)
The association that makes a company matchable by an email domain.

| Field | Type | Notes for this feature |
|-------|------|------------------------|
| `id` | UUID (PK) | — |
| `company_id` | UUID → companies | Owning company. |
| `domain` | string, **UNIQUE** | Lowercased, no leading `@`. Uniqueness ⇒ at most one company per domain. |
| `policy` | enum `auto_join` \| `request_approval` | **Auto-created rows always `request_approval`.** |
| `verified` | bool | **Auto-created rows set `True`** (trusted-by-authentication; approval gate is the safety net). Manual admin rows remain `False` until email verification. |
| `created_at` | datetime | — |
| `verified_at` | datetime \| null | Null for auto-created rows (never went through `verify@domain`). |

**New invariants introduced:**
- A `DomainJoinPolicy` is auto-created at company creation **iff** the founder's
  email domain is non-empty, **non-public**, and **not already claimed**.
- Auto-created ⇒ `policy = request_approval` AND `verified = True`.
- `domain` for any policy (auto or manual) MUST NOT be a public email-provider
  domain (enforced at both write sites).

### Company  (`companies`) — unchanged
Gains a domain association as a creation side effect. `admin_user_id` is the
source of the founder email domain for auto-association and for backfill.

### JoinRequest  (`join_requests`) — unchanged
Created by the existing `domain_match` + `request_approval` branch. Status
`pending` → `approved`/`denied`. `UNIQUE(user_id, company_id)` already prevents
duplicate requests.

### CompanyMembership  (`company_memberships`) — unchanged
Created on approval with `role = member`.

## New domain logic (not persisted): Public Email Domain classifier

Lives in `packages/core/tessera_core/domain/email_domain.py` — pure functions,
no persistence.

```
extract_domain(email: str) -> str
    # lowercase, strip, take substring after the last "@"; "" if no "@".

is_public_email_domain(domain: str) -> bool
    # True if the (lowercased, @-stripped) domain is in the curated
    # public-provider frozenset. Used to exclude gmail/outlook/etc. from
    # matching in BOTH directions.
```

Curated set is the source of truth for the "Public Domain List" spec entity. See
`research.md` Decision 3 for the initial contents.

## State transitions (join flow — existing, shown for completeness)

```
(new user, non-public matching domain exists)
        │  GET /companies/suggestions  → domain_matches: [{company}]
        ▼
   user chooses "Request to Join"
        │  POST /companies/{id}/join {method: domain_match}
        ▼
   JoinRequest(status=pending)  ──────────────►  user on /onboarding/pending
        │                                          (polls join-status)
        │  admin: POST …/approve                   │
        ▼                                          ▼
   status=approved + CompanyMembership(member) → user advanced to /complete
        │  (or) admin: POST …/deny
        ▼
   status=denied → user may create own company or request another
```

## Auto-association state transition (NEW)

```
POST /companies  (create_company)
        │
        ├─ create Company + admin CompanyMembership          (existing)
        │
        ├─ d = extract_domain(founder_email)
        │
        ├─ if d and not is_public_email_domain(d)
        │     and get_by_domain(d) is None:
        │        create DomainJoinPolicy(
        │            company_id, domain=d,
        │            policy=request_approval, verified=True)
        │        write_audit(company.domain_auto_associated)
        │     else:
        │        skip (public, or domain already claimed) — no error
        │
        └─ advance onboarding, return token                  (existing)
```

## Backfill (one-time data migration)

For each `company` with no `domain_join_policies` row:
`d = extract_domain(admin_user.email)`; if `d` is non-public and `get_by_domain(d)`
is empty, insert `DomainJoinPolicy(company_id, d, request_approval, verified=True)`.
On domains shared by multiple companies, the earliest `created_at` company wins.
Idempotent; safe to re-run.
