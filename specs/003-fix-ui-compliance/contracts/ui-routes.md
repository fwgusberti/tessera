# UI Route Contracts

**Feature**: 003-fix-ui-compliance
**Date**: 2026-06-12

This document describes the page routes the web application must expose after this feature is complete.

---

## Route Map

| Route | Page | Auth Required | Description |
|---|---|---|---|
| `/` | Home Dashboard | Yes | Summary stats + quick nav |
| `/search` | Search & Assistant | Yes | Semantic search + AI Q&A *(unchanged)* |
| `/proposals` | Proposal Review | Yes | List/approve/reject pending proposals *(unchanged)* |
| `/documents` | Document Browser | Yes | List documents by space with lifecycle state |
| `/documents/[id]` | Document Detail | Yes | View content, versions, publish action |
| `/admin` | Admin Panel | Yes (admin) | Enhanced: spaces + connectors + credentials |
| `/metrics` | Metrics Dashboard | Yes (admin) | Product metrics *(page unchanged, nav link added)* |

---

## Navigation Bar Contract

The global nav in `apps/web/app/layout.tsx` must expose these links:

```
Tessera [logo/home]     Search   Proposals   Metrics   Admin
```

All five links must be present and resolve to the correct routes.

---

## Page Contracts

### `/` — Home Dashboard

**Data fetched**:
- `GET /v1/spaces` → space count
- `GET /v1/metrics` → total_queries, documents_with_drift

**Rendered**:
- Platform name and tagline
- Stat cards: # Spaces, Total Queries, Documents with Drift
- Quick-nav links: Search, Proposals, Admin

**Error state**: Display "–" for each stat card on fetch failure. Never crash.

---

### `/documents` — Document Browser

**Data fetched**:
- `GET /v1/spaces` → populate space filter dropdown
- `GET /v1/documents?space_id={id}` → populate document list when space selected

**Rendered**:
- Space selector dropdown (populated on mount)
- Table/list of documents: title, state badge (color-coded), confidentiality
- Clicking a row navigates to `/documents/[id]`

**Empty state**: "Select a space to see its documents" when no space selected; "No documents in this space" when space has zero documents.

---

### `/documents/[id]` — Document Detail

**Data fetched**:
- `GET /v1/documents/{id}` → document + current_version
- `GET /v1/documents/{id}/versions` → version history list

**Rendered**:
- Document title, state badge, confidentiality label
- Current version content (rendered as markdown or shown as pre-formatted text)
- "Publish" button — shown only when `state === "ingested"` and disabled while request is in flight
- Version history table: version number, approved_at, approver

**Actions**:
- Publish: `POST /v1/documents/{id}/publish` → on success, update displayed state to "published" and hide the button

---

### `/admin` — Admin Panel (Enhanced)

**Sections**:

#### 1. Spaces
- **Data**: `GET /v1/admin/spaces` → space list
- **Rendered**: Table of spaces (name, slug, sector) — same as current
- **New**: "Create Space" form below the table
  - Fields: slug (required), name (required), sector (required), default_language (default: "pt-BR")
  - Submit: `POST /v1/spaces`
  - On success: append new space to list, reset form

#### 2. Space Permissions
- **Rendered**: Space selector dropdown (populated from space list above)
- **Form fields**: idp_group (required), role (select: "viewer" | "editor" | "admin"), max_confidentiality (select: "public" | "internal" | "confidential")
- Submit: `POST /v1/spaces/{id}/permissions`
- On success: show success message, reset form

#### 3. Connectors
- **Rendered**: Space selector, then list of connectors for that space (type, schedule)
- **Form fields**: type (text, required), config (textarea for JSON, required), schedule (optional cron string)
- Submit: `POST /v1/spaces/{id}/connectors`
- Each connector has "Sync Now" → `POST /v1/connectors/{id}/sync` → display returned job_id

#### 4. Agent Credentials
- **Rendered**: List of existing credentials (name, scoped spaces, revoked status)
- **Form fields**: name (required), scoped_space_ids (multi-select from spaces), max_confidentiality (select)
- Submit: `POST /v1/agent-credentials`
- On success: display the raw token in a highlighted box with a copy button and warning that it will not be shown again
- Each active credential has "Revoke" → `POST /v1/agent-credentials/{id}/revoke` → mark as revoked in list

---

## Error Handling Contract

All pages must follow this contract:

- **Loading state**: Spinner or "Loading…" text shown while any fetch is in flight
- **API error**: Inline error message (e.g., "Failed to load spaces: Unauthorized") — no page crash
- **Form validation**: Inline field error message shown synchronously before submitting to the API
- **Action error** (publish, sync, approve, etc.): Inline error below the action button — button re-enabled
