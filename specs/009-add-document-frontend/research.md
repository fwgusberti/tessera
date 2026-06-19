# Research: Add Document — Frontend

**Feature**: 009-add-document-frontend | **Date**: 2026-06-18

## Decisions

### 1. Modal Implementation Strategy

**Decision**: Implement a bespoke overlay modal using Tailwind CSS utility classes — no third-party dialog/modal library.

**Rationale**: The codebase uses Tailwind CSS v4 throughout and has no existing UI component library (no Radix, shadcn/ui, Headless UI, etc.). Introducing a library for a single modal would add unjustified dependency weight. A lightweight `<dialog>`-overlay pattern covers all requirements: focus trapping via `autoFocus` on first input, keyboard dismissal via `onKeyDown` on the overlay backdrop, ARIA role.

**Alternatives considered**:
- `<dialog>` HTML element: Considered; skip because browser support for `::backdrop` in Tailwind is inconsistent at CSS layer v4. A plain `div` overlay is easier to style uniformly.
- Headless UI / Radix: Feature-complete but adds a dependency solely for this feature; out of proportion with scope.

---

### 2. Space List Reuse

**Decision**: Pass the already-fetched `spaces` array from `DocumentsPage` as a prop to `AddDocumentModal`. The modal itself makes no API calls.

**Rationale**: `DocumentsPage` already fetches `/v1/spaces` on mount. A duplicate fetch inside the modal would cause a redundant network round-trip and could cause a flicker if spaces arrive slightly after the modal opens. Prop-drilling is justified here given the shallow component tree (page → modal).

**Alternatives considered**:
- Re-fetch inside modal: rejected (duplicate call, flicker risk).
- React Context for spaces: overkill for two levels of nesting.

---

### 3. Form State Management

**Decision**: Local `useState` hooks inside `AddDocumentModal` — no form library (React Hook Form, Formik, etc.).

**Rationale**: The form has five fields with simple validation (two required, three with defaults). The existing codebase uses raw `useState` for all forms (login, register, company). Adding a form library for a five-field form is premature.

**Alternatives considered**:
- React Hook Form: Considered; overkill for this scope; not used elsewhere.

---

### 4. Confidentiality Options

**Decision**: Expose three user-facing options — `internal`, `restricted`, `public`. Omit `confidential` from the creation modal.

**Rationale**: The `Document` type in `lib/types.ts` includes `"confidential"` as a valid value, but the API `CreateDocumentRequest` model defaults to `INTERNAL` and the spec scopes MVP to "internal / restricted / public". `confidential` can be added later without breaking changes.

---

### 5. Language Options

**Decision**: Two options in the selector — `pt-BR` (default) and `en`.

**Rationale**: The Space entity stores `default_language` as a free string, but no language registry is defined in the API. The documents test fixtures use `"en"`, and the API defaults to `"pt-BR"`. Two options cover the observed usage. Additional languages can be added as a separate feature.

---

### 6. No Backend Changes Required

**Decision**: The `POST /v1/documents` endpoint in `apps/api/tessera_api/routers/documents.py` is already fully implemented and accepts all required fields (`space_id`, `title`, `language`, `confidentiality`, `content_markdown`, `tags`, `frontmatter`). This feature is purely a frontend addition.

---

### 7. Test Approach

**Decision**: Extend the existing `apps/web/tests/documents.test.tsx` test file with new describe blocks for the modal. Follow the existing pattern: mock `@/lib/api`, mock `@/lib/auth`, render the page, interact with the button, assert modal and submission behaviour.

**Rationale**: All existing document tests live in one file. Adding new describe blocks there keeps document-feature tests co-located. Vitest + React Testing Library is already configured.
