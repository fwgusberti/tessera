# API Contracts: Onboarding

**Feature**: 007-user-company-onboarding | **Date**: 2026-06-15

All endpoints are prefixed `/v1`. All requests require `Authorization: Bearer <access_token>` unless marked **public**. Error shape follows the existing convention: `{"error": {"code": "<snake_case>", "message": "<human string>"}}`.

---

## Onboarding Flow Endpoints

### `GET /v1/onboarding/status`

Returns the current user's onboarding progress.

**Response 200**:
```json
{
  "completed": false,
  "current_step": "company",
  "completed_steps": ["profile"],
  "company_join_method": null
}
```

| Field | Type | Notes |
|-------|------|-------|
| `completed` | bool | `true` when all required steps are done |
| `current_step` | string | One of: `profile`, `company`, `invite`, `complete` |
| `completed_steps` | string[] | Steps already persisted |
| `company_join_method` | `"created" \| "joined" \| null` | Set when company step completes. `null` before company step. Used by the completion page to render the correct variant (creator summary vs. joiner welcome screen) without relying on URL state. |

---

### `POST /v1/onboarding/profile`

Save the user's personal profile (Step 1).

**Request**:
```json
{
  "full_name": "Ana Souza",
  "title": "Head of Engineering"
}
```

| Field | Required | Validation |
|-------|----------|------------|
| `full_name` | Yes | 1–100 chars |
| `title` | No | Max 150 chars |

**Response 200**:
```json
{
  "current_step": "company",
  "completed_steps": ["profile"]
}
```

**Errors**:
- `422` — validation failure (missing `full_name`)

---

### `POST /v1/onboarding/complete`

Mark onboarding as fully complete (Step 4 — after invitation step or after joining).

**Request**: empty body `{}`

**Response 200**:
```json
{
  "completed": true,
  "completed_at": "2026-06-15T14:32:00Z"
}
```

---

## Company Endpoints

### `GET /v1/companies/suggestions`

Returns domain-matching companies and/or pending invitations for the authenticated user, to be shown during the Company step.

**Response 200**:
```json
{
  "invitations": [
    {
      "id": "uuid",
      "company_id": "uuid",
      "company_name": "Acme Corp",
      "invited_by": "João Lima",
      "expires_at": "2026-06-22T10:00:00Z"
    }
  ],
  "domain_matches": [
    {
      "company_id": "uuid",
      "company_name": "Acme Corp",
      "domain": "acme.com",
      "policy": "auto_join"
    }
  ]
}
```

Note: If a company appears in both `invitations` and `domain_matches`, the frontend shows the invitation only (FR-020 priority rule). The API returns both so the frontend can implement the display logic.

---

### `POST /v1/companies`

Create a new company (company-creation path of Step 2).

**Request**:
```json
{
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "11-50"
}
```

| Field | Required | Validation |
|-------|----------|------------|
| `name` | Yes | 1–255 chars |
| `industry` | No | Max 100 chars |
| `team_size` | No | One of: `1-10`, `11-50`, `51-200`, `201-1000`, `1000+` |

**Response 201**:
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "11-50",
  "role": "admin",
  "created_at": "2026-06-15T14:00:00Z"
}
```

**Errors**:
- `422` — missing `name`

---

### `POST /v1/companies/{company_id}/join`

Accept an invitation or submit/confirm a domain-based join request.

**Request**:
```json
{
  "method": "invitation",
  "invitation_id": "uuid"
}
```

or

```json
{
  "method": "domain_match"
}
```

| Field | Notes |
|-------|-------|
| `method` | `"invitation"` or `"domain_match"` |
| `invitation_id` | Required when `method = "invitation"` |

**Response 200 — immediate join** (invitation or auto_join policy):
```json
{
  "status": "joined",
  "company_id": "uuid",
  "company_name": "Acme Corp",
  "role": "member"
}
```

**Response 200 — join request pending** (request_approval policy):
```json
{
  "status": "pending",
  "company_id": "uuid",
  "company_name": "Acme Corp"
}
```

**Errors**:
- `404` — company not found
- `409` — invitation expired or already used
- `409` — domain already claimed by another company (should not happen via UI, defensive)
- `403` — domain not verified (defensive)

---

### `GET /v1/companies/{company_id}/join-status`

Poll join request status (used by the holding screen).

**Response 200**:
```json
{
  "status": "pending",
  "company_name": "Acme Corp",
  "requested_at": "2026-06-15T14:05:00Z"
}
```

or

```json
{
  "status": "approved",
  "company_name": "Acme Corp",
  "approved_at": "2026-06-15T15:00:00Z"
}
```

or

```json
{
  "status": "denied"
}
```

---

### `DELETE /v1/companies/{company_id}/join-request`

Cancel a pending join request (from the holding screen). Returns the user to the company step.

**Response 204**: No body.

---

## Invitation Endpoints

### `POST /v1/invitations`

Send team invitations (Step 3 — company creators only).

**Request**:
```json
{
  "emails": ["alice@acme.com", "bob@acme.com"]
}
```

| Field | Required | Validation |
|-------|----------|------------|
| `emails` | Yes | Non-empty list; each must be valid email format; max 50 per request |

**Response 207** (multi-status — some may fail):
```json
{
  "sent": ["alice@acme.com"],
  "failed": [
    {"email": "bob@acme.com", "reason": "already_member"}
  ]
}
```

**Errors**:
- `403` — caller is not a company admin
- `422` — `emails` empty or contains invalid addresses

---

## Domain Policy Endpoints (Admin — Company Admin only)

### `POST /v1/companies/{company_id}/domain-policies`

Register a domain claim and trigger the verification email.

**Request**:
```json
{
  "domain": "acme.com",
  "policy": "auto_join"
}
```

| Field | Required | Validation |
|-------|----------|------------|
| `domain` | Yes | Valid domain format; no leading `@`; lowercase |
| `policy` | Yes | `"auto_join"` or `"request_approval"` |

**Response 201**:
```json
{
  "id": "uuid",
  "domain": "acme.com",
  "policy": "auto_join",
  "verified": false,
  "verification_sent_to": "verify@acme.com"
}
```

**Errors**:
- `409` — domain already claimed by another company
- `403` — caller is not company admin

---

### `GET /v1/domain-verify/{token}` (public)

Domain verification link handler. No auth required — this is the link clicked in the email.

**Response 302**: Redirects to `/settings/domain?verified=true` on success, or `/settings/domain?error=expired` if token is stale (>24h).

---

### `POST /v1/companies/{company_id}/domain-policies/{policy_id}/resend-verification`

Re-send the domain verification email (if the link expired).

**Response 200**:
```json
{
  "verification_sent_to": "verify@acme.com"
}
```

---

## Join Request Admin Endpoints

### `GET /v1/companies/{company_id}/join-requests`

List pending join requests for a company. Company admin only.

**Response 200**:
```json
{
  "requests": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "user_email": "carol@acme.com",
      "user_name": "Carol Nunes",
      "requested_at": "2026-06-15T14:00:00Z"
    }
  ]
}
```

---

### `POST /v1/companies/{company_id}/join-requests/{request_id}/approve`

Approve a join request. Creates a `CompanyMembership` with `role=member`.

**Response 200**:
```json
{"status": "approved"}
```

---

### `POST /v1/companies/{company_id}/join-requests/{request_id}/deny`

Deny a join request.

**Response 200**:
```json
{"status": "denied"}
```
