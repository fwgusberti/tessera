# Quickstart & Validation Guide: Frontend Spaces Page

## Prerequisites

- Backend API running at `http://localhost:8000` (or `NEXT_PUBLIC_API_URL`)
- At least one company with 2+ spaces seeded in the database
- A test user who is a member of at least one space and has no membership in another
- Next.js dev server: `cd apps/web && npm run dev`

---

## Scenario 1 — Browse Spaces (P1 core)

**Setup**: Log in as a user who has access to 2 spaces in their active company.

**Steps**:
1. Navigate to `http://localhost:3000/spaces`
2. Confirm the page renders without errors
3. Confirm each space is displayed as a card showing: space name, sector, role badge
4. Confirm cards are sorted alphabetically by name
5. Confirm only spaces from the active company appear (switch company via CompanyMenu and reload — the list must change)

**Expected**: Cards for each accessible space, alphabetically ordered, with correct role badges.

---

## Scenario 2 — Navigate to Members and Documents (P2)

**Setup**: At least one space visible in the listing.

**Steps**:
1. On any space card, click "Members"
2. Confirm navigation to `/spaces/{id}/members`
3. Press the browser back button
4. Confirm return to `/spaces`
5. On any space card, click "Documents"
6. Confirm navigation to `/documents?space={id}` with documents pre-filtered to that space

**Expected**: Both links work; back navigation returns to `/spaces`.

---

## Scenario 3 — Spaces NavBar Link (P3)

**Steps**:
1. While authenticated, check the top navigation bar
2. Confirm a "Spaces" link is present between Documents and Search (or consistent with ordering)
3. Click "Spaces" — confirm navigation to `/spaces`
4. Confirm the "Spaces" link is visually highlighted (indigo) when on `/spaces` or `/spaces/[id]/members`
5. Log out — confirm the "Spaces" link is not shown

**Expected**: "Spaces" link present for authenticated users, highlighted on `/spaces/*`, absent when unauthenticated.

---

## Scenario 4 — Empty State

**Setup**: Log in as a user with no spaces in the active company.

**Steps**:
1. Navigate to `/spaces`
2. Confirm the page shows a meaningful empty-state message (not a blank screen or spinner)

**Expected**: Clear message explaining no spaces are available.

---

## Scenario 5 — Error State

**Setup**: Start with the API server stopped or returning errors.

**Steps**:
1. Navigate to `/spaces`
2. Confirm the page shows an error message (not a blank screen)

**Expected**: Red/styled error message indicating the data could not be loaded.

---

## Scenario 6 — Authentication Guard

**Steps**:
1. Log out
2. Navigate directly to `http://localhost:3000/spaces`
3. Confirm redirect to `/login?redirect=%2Fspaces`

**Expected**: Unauthenticated users are redirected to login.

---

## Running Frontend Tests

```bash
cd apps/web
npm test -- --reporter=verbose
# or with coverage:
npm test -- --coverage
```

Tests to verify:
- `tests/spaces.test.tsx` — spaces page (loading, empty state, error state, card rendering, sorting, navigation links)
- `tests/space-card.test.tsx` — SpaceCard component (role badge, links, long names)
- `tests/navbar.test.tsx` — updated to assert "Spaces" link presence, active state on `/spaces`, hidden when unauthenticated
