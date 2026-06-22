# API Contracts: Company Menu

## New endpoint

### GET /v1/companies/me

Returns all companies the authenticated user is a member of.

**Auth**: Bearer token required.

**Response 200**:
```json
{
  "companies": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Acme Corp",
      "role": "admin"
    }
  ]
}
```

**Response 401**: User not authenticated.

**Notes**:
- Results are ordered by company name (ascending).
- Returns an empty `companies` array (not 404) when the user has no memberships.

---

## Unchanged endpoints (used by this feature)

### POST /v1/companies
Creates a new company and makes the caller an admin member.

**Auth**: Bearer token required.

**Request body**:
```json
{
  "name": "string (required, 1–255 chars)",
  "industry": "string (optional)",
  "team_size": "string (optional, one of: 1-10|11-50|51-200|201-1000|1000+)"
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "name": "string",
  "industry": "string | null",
  "team_size": "string | null",
  "role": "admin",
  "created_at": "ISO 8601 datetime"
}
```

**Response 422**: Invalid `team_size` value.
