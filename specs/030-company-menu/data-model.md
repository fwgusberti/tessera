# Data Model: Company Menu

## Entities (existing, no schema changes)

### Company
Already in `packages/core/tessera_core/domain/entities.py`.

| Field       | Type            | Notes                        |
|-------------|-----------------|------------------------------|
| id          | UUID            | PK                           |
| name        | str             | required, max 255            |
| industry    | str \| None     | optional                     |
| team_size   | str \| None     | optional                     |
| admin_user_id | UUID          | owner                        |
| created_at  | datetime \| None |                             |

### CompanyMembership
Already in `packages/core/tessera_core/domain/entities.py`.

| Field      | Type        | Notes                              |
|------------|-------------|------------------------------------|
| id         | UUID        | PK                                 |
| user_id    | UUID        | FK → User                          |
| company_id | UUID        | FK → Company                       |
| role       | CompanyRole | `admin` \| `member`                |

### CompanyRole (enum)
`admin`, `member` — already defined.

---

## New client-side state

### ActiveCompany (localStorage)
| Key                        | Type   | Value             |
|----------------------------|--------|-------------------|
| `tessera_active_company_id`| string | UUID of active co |

### CompanyContext (React state)
```ts
interface CompanyEntry {
  id: string;
  name: string;
  role: "admin" | "member";
}

interface CompanyContextValue {
  companies: CompanyEntry[];           // all user's companies
  activeCompany: CompanyEntry | null;  // currently selected
  isLoading: boolean;
  setActiveCompany(id: string): void;
  createAndSetActive(data: CreateCompanyData): Promise<void>;
  reloadCompanies(): Promise<void>;
}
```

---

## New API response shape

### GET /v1/companies/me
Returns the list of companies the authenticated user belongs to, ordered by name.

```json
{
  "companies": [
    { "id": "uuid", "name": "Acme Corp", "role": "admin" },
    { "id": "uuid", "name": "Beta LLC",  "role": "member" }
  ]
}
```

No new DB tables or migrations required. The endpoint reuses `list_memberships_for_user` + `get_by_id`.

---

## Relationships

```
User ──< CompanyMembership >── Company
         role: admin|member
```

Active company is a UI-layer selection stored client-side; it is not stored in the DB.
