# Research: UI Compliance with Implemented Functionality

**Date**: 2026-06-12
**Feature**: 003-fix-ui-compliance

## Findings Summary

No external research was required. All technology choices are fully determined by the existing codebase.
This document records the decisions made and rationale applied during the planning phase.

---

## Decision 1: Data Fetching Pattern

**Decision**: Retain the existing `useEffect` + `useState` pattern used in `search/page.tsx`, `proposals/page.tsx`, `admin/page.tsx`, and `metrics/page.tsx`.

**Rationale**: All existing pages use this pattern. Introducing a data-fetching library (SWR, React Query) for new pages would create inconsistency without delivering a proportional improvement, since none of the new pages require complex caching, deduplication, or background refetch behavior.

**Alternatives considered**:
- **SWR**: Would simplify loading/error states and auto-revalidation, but adds a dependency and breaks parity with existing pages. Rejected for this iteration.
- **React Query**: Same tradeoffs as SWR, higher complexity. Rejected.

---

## Decision 2: Form Handling

**Decision**: Use native HTML form elements with React controlled state (`useState` per field). No form library.

**Rationale**: The forms in scope (space creation, permission assignment, connector creation, agent credential creation) are all small (2–5 fields each). A form library would add complexity for this size. The existing codebase has no form library; introducing one would require consensus beyond this feature's scope.

**Alternatives considered**:
- **react-hook-form**: Good for complex validation and large forms. Overkill for 5-field forms. Rejected.
- **Formik**: Similar tradeoffs. Rejected.

---

## Decision 3: Page Routing — Documents

**Decision**: Two new routes: `/documents` (list) and `/documents/[id]` (detail). The list page includes a space filter dropdown; the detail page shows content + version history + publish action.

**Rationale**: Next.js App Router dynamic segments (`[id]`) are the idiomatic way to handle entity detail pages. Separating list and detail avoids loading all document content on the list page.

**Alternatives considered**:
- **Single page with side panel** (like proposals): Appropriate for proposals because the review action happens inline. For documents, content may be long and version history adds vertical space — a dedicated page is cleaner.

---

## Decision 4: Connector and Agent Credentials UI Location

**Decision**: Connector management and agent credentials management are placed under the Admin page as collapsible or tabbed sections, not separate routes.

**Rationale**: These are admin-only operations rarely accessed by regular users. Keeping them under `/admin` avoids polluting the navigation bar with admin-specific routes. The Admin page already has a similar multi-section structure (spaces table + metrics summary).

**Alternatives considered**:
- **Separate `/connectors` and `/credentials` routes**: Cleaner separation but adds navigation complexity. Rejected since the Admin page is the natural home for infrequently used admin tools.

---

## Decision 5: API Endpoint Usage

**Decision**: Use the existing `api` helper in `apps/web/lib/api.ts` for all new data fetching. No new fetch calls bypass it.

**Rationale**: The spec requirement SC-006 mandates this explicitly. The helper handles credentials, base URL, and error extraction uniformly.

---

## Decision 6: Metrics Page Navigation

**Decision**: Add a "Metrics" `<a>` tag to the nav in `apps/web/app/layout.tsx`, alongside the existing Search, Proposals, Admin links.

**Rationale**: The page already exists and is fully functional. The only gap is the missing nav link.

---

## API Surface Audit (Backend vs. UI Gap)

| API Endpoint | Method | UI Coverage (before) | UI Coverage (after) |
|---|---|---|---|
| `/v1/spaces` | GET | Admin page (read-only) | Admin page + Home |
| `/v1/spaces` | POST | ❌ None | Admin page (form) |
| `/v1/spaces/{id}/permissions` | POST | ❌ None | Admin page (form) |
| `/v1/spaces/{id}/connectors` | POST | ❌ None | Admin page (form) |
| `/v1/connectors/{id}/sync` | POST | ❌ None | Admin page (button) |
| `/v1/documents` | GET | ❌ None | `/documents` page |
| `/v1/documents/{id}` | GET | ❌ None | `/documents/[id]` page |
| `/v1/documents/{id}/versions` | GET | ❌ None | `/documents/[id]` page |
| `/v1/documents/{id}/publish` | POST | ❌ None | `/documents/[id]` page |
| `/v1/search` | POST | ✅ `/search` | No change |
| `/v1/assistant/answer` | POST | ✅ `/search` | No change |
| `/v1/proposals` | GET | ✅ `/proposals` | No change |
| `/v1/proposals/{id}/approve` | POST | ✅ `/proposals` | No change |
| `/v1/proposals/{id}/reject` | POST | ✅ `/proposals` | No change |
| `/v1/metrics` | GET | ✅ `/metrics` (no nav) | `/metrics` + nav link |
| `/v1/agent-credentials` | POST | ❌ None | Admin page (form) |
| `/v1/agent-credentials/{id}/revoke` | POST | ❌ None | Admin page (button) |
| `/v1/admin/spaces` | GET | Admin page (partial) | Admin page |
| `/v1/admin/spaces/{id}/retention` | PUT | ❌ None | Out of scope (v1) |
| `/health` | GET | ❌ None | Home page (optional) |

**Out of scope**: `/v1/admin/spaces/{id}/retention` — retention policy management requires more complex UX (date pickers, policy types) and is not mentioned in the spec.

---

## Resolved Clarifications

None — the spec contained no NEEDS CLARIFICATION markers.
