# Research: Document Edit Flow

## 1. Draft storage model

**Decision**: A new `document_drafts` table with `document_id` as its primary
key (one row per document), holding the in-progress, autosaved content
separately from `document_versions`.

**Rationale**: The spec's Assumptions already call for "autosaved
in-progress content ... stored separately from finalized document versions
until a session ends." Keying the table by `document_id` (rather than by
session or by user) directly encodes the accepted "last session to finish
wins" conflict rule (spec Edge Cases / Assumptions) — a second editor's
autosave simply upserts the same row, so there is never a
uniqueness/version-number collision to resolve. It also keeps
`document_versions.version_number` untouched by in-progress edits: a new
version row (and therefore a new version number) is only ever created once,
at finalization, exactly matching FR-012.

**Alternatives considered**:
- *Mark a `document_versions` row as a draft (`is_draft` flag) and update it
  in place.* Rejected: would require making `version_number` nullable and
  assigning it transactionally at finalize time to avoid unique-constraint
  collisions between concurrent drafts, adding schema complexity for no
  behavioral benefit over a dedicated table.
- *One draft row per (document, user).* Rejected: multiplies rows for a
  case the spec already resolves with "last write wins," and complicates
  "resume my draft when I reopen the edit view" into "which of possibly
  several drafts do I resume."

## 2. Session finalization trigger

**Decision**: Client-driven finalization only — an explicit "Done editing"
action, a `pagehide`/`beforeunload` best-effort call using
`fetch(..., {keepalive: true})`, and a client-side inactivity timer (reset on
each keystroke) that calls the same finalize endpoint after an idle period.
No server-side periodic sweep job.

**Rationale**: The repo already uses Celery for document indexing but has no
existing periodic/beat schedule (grepped `apps/api` for
`beat_schedule`/`@shared_task` periodic patterns — none found outside the
Celery package itself), so a server-side sweep would be new operational
infrastructure. Because drafts are durable rows in `document_drafts` (not
transient client state), a crash that skips client-side finalization does
not lose data — the draft simply stays unfinalized until the same or another
editor reopens the document's edit view, at which point it is resumed
(`GET /documents/{id}/draft`) and will be finalized on their next
navigate-away/timeout. This satisfies SC-002/SC-003 without adding a new
class of background job.

**Alternatives considered**:
- *Celery Beat periodic sweep finalizing any draft past its timeout.*
  Rejected for v1 as unnecessary new infrastructure given drafts already
  self-heal via resumption; can be added later if orphaned-draft
  finalization latency becomes an actual problem.
- *WebSocket/SSE-driven session tracking.* Rejected: no existing real-time
  infra in the repo (grepped for `websocket`/`EventSource`/`sse` — no
  matches), and the spec's autosave/finalize behavior does not require
  server-push, only periodic client-initiated calls.

## 3. Autosave transport

**Decision**: Plain periodic REST `PUT /documents/{id}/draft` calls from the
frontend, debounced ~4s after the last keystroke with a hard cap so a
continuously-typing user still flushes at least every ~15s.

**Rationale**: Matches the existing frontend data-fetching pattern (raw
`api.get`/`api.post` calls in `useEffect`, no SWR/React Query, no existing
polling infra) rather than introducing a new transport just for this
feature.

**Alternatives considered**: WebSocket streaming — rejected, no existing
infra and REST is sufficient for a save cadence measured in seconds, not
milliseconds.

## 4. Editable pane

**Decision**: A plain HTML `<textarea>`, no new editor dependency.

**Rationale**: The spec explicitly describes "the editable .md" pane, and
explicitly defers any richer (syntax-highlighted or WYSIWYG) editor to a
future, out-of-scope enhancement. `apps/web/package.json` has no existing
code-editor dependency (CodeMirror/Monaco); adding one now would be scope
creep against the spec's own Assumptions.

**Alternatives considered**: CodeMirror/Monaco for Markdown syntax
highlighting — rejected for this feature; revisit only if a future
enhancement spec calls for it.

## 5. Preview rendering

**Decision**: Reuse the existing `DocumentContent` component
(`apps/web/components/documents/DocumentContent.tsx`, built in feature 045
on `react-markdown` + `remark-gfm`) unmodified, fed the live textarea value
directly (re-rendered synchronously on every keystroke via React state — no
debounce needed for the preview itself, only for the network autosave
call).

**Rationale**: Feature 045 already established safe, dependency-light
Markdown rendering (no `rehype-raw`, so no raw-HTML passthrough) with the
same GFM feature set FR-005/FR-006 require. Reusing it verbatim avoids a
second rendering code path that could drift from the read-only view's
output.

## 6. Permission check

**Decision**: Reuse `can_write_document(user, space_id, memberships,
is_company_admin)` from `tessera_core.permissions.access` (already used by
`POST /documents` for the identical "EDITOR or ADMIN effective space role"
rule) to gate all three new endpoints server-side. The frontend additionally
hides the "Edit" entry point for users it knows lack write access, as a UX
convenience — the server check is what actually satisfies SC-004.

**Rationale**: This is exactly the permission tier the user selected during
`/speckit-specify` ("any space member with write access"), and the helper
already exists and is unit-testable the same way `create_document`'s check
is tested today.

## 7. Audit logging

**Decision**: Emit one audit record (`action="document_edited"`) at session
finalization, when a new `DocumentVersion` is actually created. Individual
autosave ticks (`PUT /draft`) are not individually audited.

**Rationale**: The constitution requires an audit log for "every
state-changing action." Finalization is the point where the document's
durable, visible content actually changes (a new `DocumentVersion` row and
an updated `current_version_id`) — the same granularity already used for
`publish`. Autosave ticks mutate only the ephemeral `document_drafts`
scratch row, not the document's real content; auditing every tick (every
few seconds while a user types) would flood the audit log without recording
any user-visible state change.
