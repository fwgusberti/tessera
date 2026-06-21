# Quickstart & Validation Guide: UI Color Compliance

**Feature**: 018-ui-color-compliance | **Date**: 2026-06-20

## Prerequisites

- Docker Compose stack running (`docker compose up` from repo root)
- Web dev server running: `cd apps/web && npm run dev`
- Browser at `http://localhost:3000` (or `http://<HOST>:3000` if using HOST env)
- A registered user account (or use the seed data if available)

---

## Automated Verification (static)

Run this grep from the repo root to confirm zero remaining violations after migration:

```bash
# Must return 0 matches — any output is a violation
grep -rn "\bblue-[0-9]" apps/web/app apps/web/components \
  --include="*.tsx" --include="*.ts" --include="*.css" \
  | grep -v node_modules | grep -v .next | grep -v coverage

grep -rn "\bgray-[0-9]" apps/web/app apps/web/components \
  --include="*.tsx" --include="*.ts" --include="*.css" \
  | grep -v node_modules | grep -v .next | grep -v coverage
```

Both commands must produce **no output**.

---

## Automated Test Suite

```bash
cd apps/web
npm test
```

All tests must pass without modification. The test suite covers routing and data behaviour; any failure here indicates a behavioural regression introduced by the migration (which should not be possible for a CSS-class-only change).

---

## Visual Walkthrough (manual)

Open each route below and verify the listed conditions. All interactive elements should be **indigo** (not blue); all neutral surfaces should be **slate** (visually nearly identical to gray, but constitutionally distinct).

### 1. Login — `/login`

- Form inputs show **indigo** focus ring when tabbed to
- "Sign in" button is **indigo-600** background, **indigo-700** on hover
- "Create account" link is **indigo** text
- No blue-tinted elements visible

### 2. Register — `/register`

- Same form field and button treatment as Login
- "Sign in" link is **indigo** text

### 3. Dashboard — `/`

- Page header text uses **slate** scale (nearly indistinguishable from gray visually)
- Quick-nav cards show **indigo** border on hover (not blue)

### 4. Documents — `/documents`

- "Add Document" button: **indigo-600** default, **indigo-700** hover
- Document title links: **indigo** text
- Table header row: **slate-50** background
- `archived` badge: **slate-100** background with **slate-600** text (not gray)

### 5. Document Detail — `/documents/<id>`

- Back link: **indigo** text
- "Reindex" button: **indigo-600** / **indigo-700**
- Version history table: **slate** header

### 6. Add Document Modal

- All form inputs: **indigo** focus ring
- "Add" button: **indigo-600** / **indigo-700**
- "Cancel" button: **slate** border and text, **slate-50** hover

### 7. Search — `/search`

- Mode toggle (Search / Ask): active button **indigo-600**; inactive **white** with border
- Search input: **indigo** focus ring
- "Search" submit button: **indigo-600**
- Snippet snippets: **slate** backgrounds

### 8. Admin — `/admin`

- All form inputs: **indigo** focus ring
- All "Create" / "Submit" buttons: **indigo-600** / **indigo-700**
- Table headers: **slate-50** background
- Muted/secondary text: **slate** scale

### 9. Proposals — `/proposals`

- Selected proposal card: **indigo-500** border + **indigo-50** background tint
- Unselected hover: **slate-50**

### 10. Metrics — `/metrics`

- All text labels and values: **slate** scale

### 11. Onboarding — `/onboarding/*`

**Progress stepper** (ProgressStepper component):
- Completed step: **indigo-600** filled circle
- Current step: **indigo-100** bg + **indigo-700** text + **indigo-600** border
- Pending step: **slate-100** bg + **slate-400** text
- Connector line (completed): **indigo-600**
- Connector line (pending): **slate-200**

**Profile step** (`/onboarding/profile`):
- Form inputs: **indigo** focus ring
- "Continue" button: **indigo-600** / **indigo-700**

**Company step** (`/onboarding/company`):
- "Search" spinner: **indigo-600** border-t-transparent spinner
- Invitation card (CompanySuggestions): **indigo-200** border + **indigo-50** background
- "Join" button on invitation: **indigo-600** / **indigo-700**
- "Request to join" button on match card: **slate** border + text

**Invite step** (`/onboarding/invite`):
- Email chip tags: **indigo-100** bg + **indigo-800** text
- Chip close button: **indigo-500** / **indigo-700** hover
- Email input container: **indigo** focus ring
- "Send Invites" button: **indigo-600** / **indigo-700**

**Complete/Pending steps**: Primary button **indigo-600** / **indigo-700**

### 12. NavBar (all pages)

- Logo and nav links: **slate-900** / **slate-600**
- Nav link hover: **slate-900**
- Bottom border: **slate-200**

### 13. Space Selector (documents page)

- Dropdown: **indigo** focus ring when selected

---

## Focus State Verification (accessibility)

Tab through the following pages and confirm every interactive element shows a visible **indigo** focus ring:

1. `/login` — email input, password input, submit button
2. `/documents` — "Add Document" button, space selector dropdown

No element should show a **blue** focus ring after migration.

---

## Error State Non-Regression

1. Visit `/login`, submit with wrong credentials → error message appears in **red** (not indigo)
2. Visit `/register`, submit with mismatched passwords → validation error in **red**

These must be unchanged from pre-migration behaviour.
