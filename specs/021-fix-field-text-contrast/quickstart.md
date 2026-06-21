# Quickstart: Validate Field Text Contrast Fix

## Prerequisites

- Dev server running: `cd apps/web && npm run dev` (port 3000)
- At least one registered user account (for authenticated pages)

## Setup

No migrations or seed data needed. The fix is a CSS-only change to `globals.css`.

## Validation Scenarios

### SC-001 — Login page (unauthenticated)

1. Open `http://localhost:3000/login`
2. Click into the **Email** field and type any text
3. **Expected**: typed text is clearly dark (slate-900, near-black) against the white field background
4. Repeat for the **Password** field
5. **Expected**: password dots are clearly visible

### SC-002 — Registration page (unauthenticated)

1. Open `http://localhost:3000/register`
2. Type into **Display name**, **Email**, and **Password** fields
3. **Expected**: text is clearly readable in all three fields

### SC-003 — Placeholder text contrast

1. On the login page, look at the Email field **before** typing
2. **Expected**: placeholder text (if any) is a medium gray (slate-400), lighter than but visually distinct from filled text
3. On Admin → Create Space form, look at the placeholder `"Slug (e.g. engineering)"`
4. **Expected**: placeholder is lighter than typed text, not invisible

### SC-004 — Search page

1. Sign in, then open `http://localhost:3000/search`
2. Click the search input and type a query
3. **Expected**: query text is clearly readable

### SC-005 — Admin page — text inputs and selects

1. Open `http://localhost:3000/admin`
2. In the **Create Space** form, type into all four text inputs
3. In the **Space Permissions** form, interact with the role and confidentiality dropdowns
4. **Expected**: text in both inputs and dropdown options is clearly readable

### SC-006 — Add Document modal — textarea

1. Open `http://localhost:3000/documents` and click **+ Add Document**
2. Type in the **Title** field and the **Content (Markdown)** textarea
3. **Expected**: text is clearly readable in both

### SC-007 — Onboarding forms

1. Navigate through onboarding: `/onboarding/profile` → `/onboarding/company`
2. Type into **Full Name**, **Job Title**, **Company Name**, and interact with the Industry / Team Size selects
3. **Expected**: text is clearly readable in inputs and select dropdowns

### SC-008 — Focused state

1. On any page with a form, Tab into a field
2. **Expected**: the focus ring (indigo-500) appears AND text inside remains clearly readable — no color degradation when focused

### SC-009 — Error state

1. On the login page, submit the form with an empty Email
2. **Expected**: the field (with or without a red border/highlight) still shows clearly readable text

### SC-010 — No regressions

1. Scan labels, error messages, and surrounding UI text on each page visited above
2. **Expected**: no surrounding text has become harder to read after the CSS change

## Acceptance Criteria Mapping

| Scenario | Acceptance Criterion |
|----------|---------------------|
| SC-001 to SC-007 | SC-001: all fields display readable text |
| SC-003 | SC-002: placeholder visually distinct from filled text |
| SC-008 & SC-009 | SC-003: all states pass visual inspection |
| SC-010 | SC-004: no new contrast issues introduced |

## CSS Diff to Verify

After implementation, `apps/web/app/globals.css` should contain (see [contracts/css-rules.md](./contracts/css-rules.md)):

```css
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="color"]):not([type="file"]),
textarea,
select {
  color: var(--color-slate-900);
}

::placeholder {
  color: var(--color-slate-400);
  opacity: 1;
}
```
