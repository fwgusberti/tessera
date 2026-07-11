# Data Model: Company Selection at Sign-In (059)

**Date**: 2026-07-11 | **Plan**: [plan.md](./plan.md)

No database entities are created or modified — this feature is a client-side
session-flow fix. The model below describes the client's view of the session
credential and the read models it consumes.

## Client-side session credential (existing, now fully modeled)

Decoded from the stored access token's JWT payload by `decodeJwtUser`
(`apps/web/lib/auth.tsx`). Fields newly surfaced to the web app are marked
**NEW**.

| Field | Type | Source claim | Notes |
|---|---|---|---|
| `id` | `string` | `sub` | User id |
| `email` | `string` | `email` | |
| `isAdmin` | `boolean` | `is_admin` | Global admin flag |
| `tokenKind` **NEW** | `TokenKind` | `token_kind` | Defaults to `"full"` when absent (legacy tokens) |
| `companyId` **NEW** | `string \| null` | `company_id` | Present only on `full` tokens |

```ts
export type TokenKind = "full" | "select" | "onboarding";
```

### Session scope states & transitions

```
                    login (1 membership)
  unauthenticated ────────────────────────────► full ──► app
        │
        │ login (0 memberships)
        ├────────────────────────► onboarding ──► /onboarding (existing flow)
        │
        │ login (2+ memberships)
        └────────────────────────► select ──► /select-company
                                      │
                                      │ POST /auth/select-tenant (valid pick)
                                      ├──────────────────────────► full ──► app
                                      │
                                      │ pick fails (suspended / revoked)
                                      ├──► select (stay; friendly error; list re-fetched)
                                      │
                                      │ sign out OR refresh-token expiry
                                      └──────────────► unauthenticated ──► /login
```

Invariants:

- `POST /v1/auth/refresh` preserves the state (`token_kind` + `company_id`
  are copied from the stored refresh-token row), so background renewal never
  moves the session between states (FR-007).
- The only client transition out of `select` is a successful exchange or a
  sign-out; the client never fabricates a `full` state.
- A `full`-state session visiting `/select-company` is redirected into the
  app (edge case in spec); a `select`-state session visiting any protected
  page is redirected to `/select-company` (FR-004).

## Company membership entry (existing read model, reused)

`CompanyEntry` (`apps/web/lib/companies.ts`), from `GET /v1/companies/me`:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Selection is by id — rename-safe (spec edge case) |
| `name` | `string` | Displayed in the picker (FR-001) |
| `role` | `"admin" \| "member"` | Displayed as a role badge (FR-001) |

Sorted by name server-side. The list is re-fetched after a failed selection
so revoked/suspended entries drop out (FR-006).

## Login response (existing contract, type extended)

`LoginResponse` (`apps/web/lib/types.ts`) gains the field the backend already
sends:

| Field | Type | Notes |
|---|---|---|
| `access_token` | `string` | |
| `refresh_token` | `string` | |
| `token_type` | `"bearer"` | |
| `expires_in` | `number` | seconds |
| `tenant_selection_required` **NEW** | `boolean \| undefined` | Present and `true` only for multi-membership logins |

`POST /v1/auth/select-tenant` returns the same shape **without**
`tenant_selection_required` (`SelectTenantResponse = LoginResponse` minus the
flag; in practice typed as `RefreshResponse`).

## Validation rules (client-side)

- Selection requests send only `{ company_id }`; all authorization
  (membership, company activeness) is server-side — the client treats 403
  codes as display states, never as data.
- Error-code → message mapping (FR-005/FR-006): `company_suspended`,
  `not_a_member` → specific friendly copy; any other failure → generic
  "Something went wrong" copy. The literal backend string for
  `credential_not_scoped` is never rendered anywhere.
