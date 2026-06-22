# Quickstart: Validating the Company Menu

## Prerequisites

- Local stack running: `make dev` from repo root
- At least one user account registered and logged in
- A second user account (for multi-company membership tests)

## Setup

```bash
# Seed a second company for the test user via the API
curl -X POST http://localhost:8000/v1/companies \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Second Corp"}'
```

## Validation Scenarios

### S1 — Single-company user sees name, no switcher

1. Log in as a user with exactly one company.
2. Observe the NavBar.
3. **Expected**: Company name visible; no dropdown/switcher shown.

### S2 — Multi-company user can switch

1. Log in as a user with two or more companies (created in setup above).
2. Click the company name in the NavBar.
3. **Expected**: Dropdown lists all companies; current one is visually distinguished (e.g., checkmark or bold).
4. Select the second company.
5. **Expected**: Company name updates to the selected one; selection persists on page reload.

### S3 — Create new company from the menu

1. Open the company menu.
2. Select "Create new company."
3. **Expected**: Modal appears with name field (required), industry and team_size (optional).
4. Submit with a valid name.
5. **Expected**: New company appears in the menu list and becomes the active company.

### S4 — Invalid company name shows error

1. Open create modal.
2. Submit with empty name.
3. **Expected**: Inline error message; no company created; modal stays open.

### S5 — Admin sees "Company settings"

1. Log in as the admin (creator) of a company.
2. Open the company menu.
3. **Expected**: "Company settings" option is visible.
4. Click it.
5. **Expected**: Navigates to `/settings/company`.

### S6 — Non-admin does NOT see "Company settings"

1. Log in as a user with `role: member` in the active company.
2. Open the company menu.
3. **Expected**: "Company settings" is absent from the menu.

### S7 — No-company user sees prompt

1. Log in as a newly registered user with no company membership.
2. Observe the NavBar company area.
3. **Expected**: Prompt to create or join a company is shown.

### S8 — Mobile viewport

1. Resize browser to ≤ 768 px (or use DevTools responsive mode).
2. Open the hamburger menu.
3. **Expected**: Company menu section is accessible within the mobile nav; all tap targets ≥ 44×44 px.

## API endpoint check

```bash
# Confirm GET /v1/companies/me returns correct shape
curl http://localhost:8000/v1/companies/me \
  -H "Authorization: Bearer <token>"

# Expected:
# {"companies": [{"id": "...", "name": "...", "role": "admin|member"}]}
```

See [contracts/api.md](contracts/api.md) for full request/response details.
