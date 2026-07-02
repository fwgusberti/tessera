# Reused Endpoints (no changes)

This feature introduces zero new backend endpoints and zero changes to
existing endpoint request/response shapes. It reuses the following, all
already implemented in `apps/api/tessera_api/routers/documents.py` and
`apps/api/tessera_api/routers/spaces.py`, already `company_id`-scoped via
`CompanyContext`:

| Endpoint | Used for | Change required |
|---|---|---|
| `GET /v1/documents/{document_id}` | Document header data (title, state, confidentiality, tags, owner, `space_id`) and current version | None — already called by the existing page |
| `GET /v1/documents/{document_id}/versions` | Version history list | None — already called by the existing page |
| `POST /v1/documents/{document_id}/publish` | Publish action | None — same request/response, only the triggering button is restyled |
| `POST /v1/documents/{document_id}/reindex` | Reindex action | None — same request/response, only the triggering button is restyled |
| `GET /v1/spaces/{space_id}` | Document's own space name/slug, for the breadcrumb's second-to-last segment | None — new *usage* on this page, not a new endpoint (already used by `app/spaces/[id]/page.tsx`) |
| `GET /v1/spaces/{space_id}/ancestors` | Ancestor chain for the breadcrumb | None — new *usage* on this page, not a new endpoint (already used by `app/spaces/[id]/page.tsx`) |

## Failure handling (new, frontend-only)

Both space-lookup calls are additive to what the page already fetches. If
either fails (e.g., transient error, or a 403/404 in the defensive case where a
document's space is no longer accessible), the page MUST still render the
document, header, content, actions, and version history — only the breadcrumb
falls back to a plain "← Documents" link, matching current behavior. This is a
frontend-only degradation path; it does not require any backend change.
