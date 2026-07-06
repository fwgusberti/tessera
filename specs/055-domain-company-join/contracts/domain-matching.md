# Contracts: Domain-Based Company Matching

Most endpoints in this flow already exist and are **unchanged**. This document
records (a) the behavioral change to `create_company`, (b) the new guard on
`create_domain_policy`, and (c) the existing endpoints whose behavior this
feature *activates*, so contract tests can assert against them.

---

## CHANGED — `POST /v1/companies` (create_company)

Creating a company gains a **domain auto-association side effect**. The
request/response shape is unchanged.

**Side effect (new):** After the company and admin membership are created, if the
authenticated founder's email domain `d = extract_domain(email)` satisfies all of:
- `d` is non-empty, AND
- `is_public_email_domain(d)` is `False`, AND
- no existing `DomainJoinPolicy` claims `d`

then a `DomainJoinPolicy{ company_id, domain: d, policy: "request_approval",
verified: true }` is created and a `company.domain_auto_associated` audit record
is written.

**Guarantees:**
- Company creation MUST succeed even if auto-association is skipped or fails
  (public domain, already-claimed, or a race producing `IntegrityError`).
- Auto-created policies are ALWAYS `request_approval` (never `auto_join`).

**Contract tests:**
| Founder email | Expected policy after create |
|---------------|------------------------------|
| `founder@acme.example` (non-public, unclaimed) | one row, `request_approval`, `verified=true`, audit emitted |
| `founder@gmail.com` (public) | no domain policy row |
| `founder@acme.example` when `acme.example` already claimed | no new row, 201 still returned |

---

## CHANGED — `POST /v1/companies/{company_id}/domain-policies` (create_domain_policy)

**New guard (FR-010, defense in depth):** If `is_public_email_domain(body.domain)`
is `True`, respond `422` with
`{"error": {"code": "public_domain_not_allowed", "message": …}}` before any
write. All existing behavior (admin gate, `409 domain_already_claimed`,
verification email) is otherwise unchanged.

**Contract test:** admin POSTs `{"domain": "gmail.com", "policy": "request_approval"}`
→ `422 public_domain_not_allowed`; no policy created, no email sent.

---

## ACTIVATED (unchanged code) — `GET /v1/companies/suggestions`

Now returns `domain_matches` for organically-created companies because a
`verified` policy exists. Response shape unchanged:

```json
{
  "invitations": [ … ],
  "domain_matches": [
    { "company_id": "…", "company_name": "…", "domain": "acme.example",
      "policy": "request_approval" }
  ]
}
```

**Guarantees asserted by tests:**
- A caller whose email domain matches an auto-associated company sees that
  company in `domain_matches`.
- A caller on a public domain, or on a domain owned by a *different* company,
  sees no such match (isolation / FR-010).

---

## ACTIVATED (unchanged code) — `POST /v1/companies/{company_id}/join`

Body `{ "method": "domain_match" }`. With an auto-associated
(`verified=true`, `request_approval`) policy:

- Success → `200 { "status": "pending", "company_id", "company_name" }` and a
  `JoinRequest(pending)` exists; admin notified.
- Re-request while pending → same `pending` response, **no duplicate**
  `JoinRequest`.
- Caller already a member → `409 already_member`.
- Caller's email domain does not own a policy for `company_id` →
  `404 no_domain_policy` (isolation guarantee).

---

## Unchanged — admin decision endpoints (already implemented)

- `GET /v1/companies/{id}/join-requests` — admin-gated list of pending requests
  (requester `user_id`, `user_name`, `user_email`, `requested_at`).
- `POST /v1/companies/{id}/join-requests/{request_id}/approve` — adds
  `CompanyMembership(member)`, notifies requester, audits; `409 already_decided`
  if not pending.
- `POST /v1/companies/{id}/join-requests/{request_id}/deny` — marks denied,
  notifies, audits; `409 already_decided` if not pending.
- `GET /v1/companies/{id}/join-status`, `DELETE /v1/companies/{id}/join-request`
  — used by the pending page; unchanged.

These are covered by contract tests to confirm this feature does not regress
them, but they require no code change.
