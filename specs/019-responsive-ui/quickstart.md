# Quickstart Validation Guide: Responsive UI for Smartphones

**Feature**: 019-responsive-ui | **Date**: 2026-06-20

This guide describes how to validate the responsive changes end-to-end after implementation. It covers the tools, viewports, and expected outcomes. See [contracts/responsive-ui.md](contracts/responsive-ui.md) for the full acceptance criteria.

---

## Prerequisites

- The web app is running locally: `cd apps/web && npm run dev` (default port 3000)
- A test user account exists (register via `/register` if not)
- Chrome DevTools or Firefox DevTools available for viewport simulation
- At least one Space and one published Document exist (create via the UI or seed script)

---

## Viewport Profiles to Test

| Profile | Width | Device equivalent |
|---------|-------|------------------|
| **Primary** | 390px | iPhone 14 / 15 |
| **Small** | 320px | iPhone SE (1st gen) |
| **Large mobile** | 430px | iPhone Plus / Android large |
| **Desktop (regression)** | 1280px | Standard laptop |

---

## Scenario 1: Navigation on Mobile

**Setup**: Open DevTools → Toggle device toolbar → set width to 390px.

**Steps**:
1. Navigate to `http://localhost:3000`.
2. Confirm the hamburger button (☰) is visible in the top-right area of the navbar.
3. Confirm that Search, Documents, Proposals, Metrics, Admin, Sign out links are NOT visible.
4. Tap the hamburger button.
5. Confirm the mobile menu opens and all nav links are listed vertically.
6. Tap "Documents".
7. Confirm the menu closes and the Documents page loads.
8. Press Escape (or tap outside) — confirm menu closes.

**Expected**: See [NavBar contract](contracts/responsive-ui.md#navbar).

---

## Scenario 2: Documents List on Mobile

**Setup**: Viewport 390px. Log in and navigate to `/documents`.

**Steps**:
1. Select a space from the space selector. Confirm the selector spans full width.
2. Scroll the document list.
3. Confirm no horizontal scrollbar appears at the page level.
4. Confirm Title and State columns are visible.
5. Confirm the Confidentiality column is hidden.

**At 1280px**:
6. Confirm all 3 columns (Title, State, Confidentiality) are visible.

**Expected**: See [Documents List Page contract](contracts/responsive-ui.md#documents-list-page).

---

## Scenario 3: Document Detail on Mobile

**Setup**: Viewport 390px. Navigate to a published document.

**Steps**:
1. Confirm the document title and Reindex/Publish button(s) are stacked vertically (not side by side).
2. Confirm the title does not overflow the viewport.
3. Scroll to the version history table — confirm no horizontal overflow.

**Expected**: See [Document Detail Page contract](contracts/responsive-ui.md#document-detail-page).

---

## Scenario 4: Login / Register Forms on Mobile

**Setup**: Viewport 390px. Simulate mobile keyboard by opening the DevTools keyboard overlay (Chrome: "Show soft keyboard" in device emulation), OR physically use a mobile device.

**Steps (login)**:
1. Navigate to `/login`.
2. Tap the email field — virtual keyboard appears.
3. Confirm the Submit ("Sign in") button is visible or reachable by scrolling up.
4. Enter credentials and submit.
5. Confirm error messages (if credentials are wrong) are visible without scrolling.

**Steps (register)**:
1. Navigate to `/register`. Repeat the keyboard check.

**Expected**: See [Login and Register Pages contract](contracts/responsive-ui.md#login-and-register-pages).

---

## Scenario 5: Onboarding Flow on Mobile

**Setup**: Viewport 390px. Use a fresh account that hasn't completed onboarding.

**Steps**:
1. Navigate to `/onboarding/profile`.
2. Confirm the ProgressStepper (4 steps) fits within the viewport — no horizontal scrollbar.
3. Confirm the white card has comfortable padding.
4. Fill in the form and tap "Continue".
5. Repeat for `/onboarding/company`, `/onboarding/invite`, `/onboarding/complete`.
6. On each step, confirm the Continue/Submit button is tappable without zooming.

**At 320px**: Repeat step 2 for ProgressStepper — confirm it still fits.

**Expected**: See [ProgressStepper contract](contracts/responsive-ui.md#progressstepper) and [Onboarding Layout contract](contracts/responsive-ui.md#onboarding-layout).

---

## Scenario 6: Add Document Modal on Mobile

**Setup**: Viewport 390px. Navigate to `/documents`.

**Steps**:
1. Tap "Add Document".
2. Confirm the modal dialog is fully visible within the viewport.
3. Confirm Language and Confidentiality selects are stacked vertically.
4. Fill in Title and Space, then tap Save.
5. Confirm the modal closes and the new document appears in the list.

**At 320px**:
6. Repeat — confirm no horizontal clipping of modal content.

**Expected**: See [AddDocumentModal contract](contracts/responsive-ui.md#adddocumentmodal).

---

## Scenario 7: Desktop Regression Check

**Setup**: Viewport 1280px.

**Steps**:
1. Verify the hamburger button is NOT visible.
2. Verify all nav links are visible horizontally.
3. Spot-check Documents, Document detail, Login, and Onboarding pages — confirm layouts match the pre-feature baseline visually.

**Expected**: See [Global Rules — Desktop unchanged](contracts/responsive-ui.md#global-rules).

---

## Automated Test Coverage

After implementation, run:

```bash
cd apps/web
npm test          # Vitest unit + component tests (includes NavBar mobile menu tests)
npx playwright test --project=chromium   # If Playwright is configured
```

All existing tests must pass. New tests in `tests/navbar.test.tsx` must cover the hamburger toggle behavior.

---

## Overflow Audit (Manual Script)

In Chrome DevTools console, run on each page at 390px to check for horizontal overflow:

```js
// Paste in DevTools Console
const overflowing = [];
document.querySelectorAll('*').forEach(el => {
  if (el.scrollWidth > document.documentElement.clientWidth) {
    overflowing.push({ el, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth });
  }
});
console.table(overflowing);
```

**Expected**: Empty array on all pages after this feature is implemented.
