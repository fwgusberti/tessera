# Quickstart: Documents Navigation Link

## Prerequisites

- Node.js installed; `apps/web` dependencies installed (`npm install` in `apps/web`)

## Validation Steps

### 1. Run the unit tests

```bash
cd apps/web
npx vitest run tests/navbar.test.tsx
```

**Expected**: All tests pass, including the new assertion for the "Documents" link.

### 2. Visual check in the browser

```bash
cd apps/web
npm run dev
```

Open `http://localhost:3000`, log in, and confirm:
- "Documents" appears in the nav bar between "Search" and "Proposals".
- Clicking it navigates to `/documents`.
- Logging out and clicking "Documents" redirects to `/login`.
