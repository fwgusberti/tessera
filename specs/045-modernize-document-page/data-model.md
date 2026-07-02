# Phase 1 Data Model: Modernize Document Page

This feature is presentation-only. No new database tables, columns, or API
request/response shapes are introduced. The entities below already exist
(`apps/web/lib/types.ts`) and are documented here only to describe how this
feature consumes and composes them client-side.

## Existing entities consumed (unchanged)

### Document
Already defined in `lib/types.ts`. Fields used by this feature: `id`, `space_id`
(new usage — previously unused on this page, now drives the breadcrumb fetch),
`title`, `state`, `confidentiality`, `tags`, `owner_user_id`.

### DocumentVersion
Already defined in `lib/types.ts`. Fields used: `version_number`,
`content_markdown` (now rendered as formatted markdown instead of raw text),
`approved_at`, `approver_user_id`.

### Space / Ancestor
Already defined in `lib/types.ts`. `Ancestor` (`id`, `name`, `slug`) is reused
as-is; the document's own space (`GET /v1/spaces/{space_id}`) is treated as an
`Ancestor`-shaped value (it exposes the same three fields) for breadcrumb
composition — see below.

## Derived client-side view (not persisted, not a new type)

### Breadcrumb trail
A view composed at render time from two existing endpoint responses:

```
breadcrumbAncestors = [...ancestorsResponse.ancestors, {
  id: space.id, name: space.name, slug: space.slug,
}]
breadcrumbCurrentName = document.title
```

This is passed directly into the existing `SpaceBreadcrumb` component's
`ancestors` / `currentName` props. No new interface is added to `types.ts` for
this — it is a plain array literal at the call site, since `Ancestor` already
covers the shape needed.

## State transitions

None. `Document.state` transitions (`ingested` → `published`, `published` →
re-indexed) are unchanged — this feature only restyles the controls that
trigger `POST /v1/documents/{id}/publish` and `POST /v1/documents/{id}/reindex`
and the badges that reflect the resulting state.

## Validation rules

None new. All validation (eligibility to publish/reindex, tenant/company
scoping on every fetch) is enforced server-side today and is unchanged by this
feature.
