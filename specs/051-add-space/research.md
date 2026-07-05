# Phase 0 Research: Add Space

No open `NEEDS CLARIFICATION` markers from the Technical Context — the stack,
storage, and testing frameworks all match the existing spaces feature set
(041/044/049). This document records the design decisions made while reconciling
the spec's Assumptions with the current codebase.

## 1. Extend the existing create endpoint vs. add a new one

**Decision**: Extend `POST /v1/spaces` (`apps/api/tessera_api/routers/spaces.py`)
by making `slug` and `sector` optional and adding an optional `parent_space_id`,
rather than adding a second, simplified endpoint for the Spaces-page flow.

**Rationale**: There is exactly one `Space` creation path today, already used by
the admin console (`apps/web/app/admin/page.tsx`) with an explicit `slug`/
`sector`. Making the new fields optional (not renaming or removing existing ones)
keeps that caller working unchanged while letting the new "Add Space" modal send
only `name` (and, from a folder view, `parent_space_id`).

**Alternatives considered**: A dedicated `/spaces/quick-create`-style endpoint —
rejected; it would duplicate the creator-membership-grant and audit logic already
in `create_space`, and give the product two divergent creation code paths for one
entity.

## 2. Slug auto-generation and uniqueness

**Decision**: Add a pure `slugify(name: str) -> str` helper (new
`packages/core/tessera_core/services/slug.py`, stdlib `unicodedata` + `re` only —
normalizes accents, lowercases, replaces non-alphanumerics with hyphens, collapses
repeats, falls back to `"space"` if the result is empty). `SpaceHierarchyService.create`
calls it when the request omits `slug`, then resolves collisions by appending
`-2`, `-3`, ... and checking a new `SpaceRepository.slug_exists(slug) -> bool`
port method (implemented in `SqlSpaceRepository` as a `SELECT EXISTS`), truncating
to fit the existing 100-char column.

**Rationale**: `spaces.slug` is globally unique (`String(100) UNIQUE NOT NULL`),
but the spec's Assumptions say the creation form only asks for a name — the slug
is an internal identifier the user should never see or need to disambiguate.
Centralizing generation in the domain service (rather than the frontend) means
any future caller of `create_space` gets the same guarantee, and keeps the
uniqueness rule enforced server-side where the constraint actually lives.

**Alternatives considered**:
- *Generate the slug client-side and submit it*: rejected — the frontend would
  still need a round trip to check uniqueness (or risk a raw 500 from the DB
  constraint), so centralizing server-side is strictly simpler and safer.
- *Let the `INSERT` fail on the unique constraint and catch `IntegrityError`,
  retrying with a new suffix*: rejected — catching a SQLAlchemy exception inside
  `SpaceHierarchyService` would leak a persistence concern into domain code,
  violating Principle I (Domain-Driven Architecture). A repository port method
  (`slug_exists`) keeps that check behind the existing port/adapter boundary.

## 3. Nested (sub-space) creation: one call vs. create-then-reparent

**Decision**: `SpaceHierarchyService.create` accepts an optional
`parent_space_id` and, when present, runs the *same* parent-admin and depth-limit
checks `set_parent` already performs (`get_by_id_for_company`, admin
`SpaceMembership` check, `get_ancestor_chain` + `_MAX_DEPTH` comparison) before
inserting the new space with `parent_space_id` already set — a single service
call, one transaction.

**Rationale**: The spec's FR-008 requires that a failed creation never leaves a
partial/orphaned space. A two-step "create as root, then call `PATCH
/spaces/{id}/parent`" from the frontend would create a real (if temporarily
mis-placed) root-level space if the second call failed for any reason — that is
itself a partial/inconsistent outcome relative to what the user asked for, even
though no exception-handling bug is involved. Doing both in one service call
avoids the intermediate state entirely and reuses validation logic that already
exists and is already tested for `set_parent`.

**Alternatives considered**: Two-step frontend orchestration (create, then
`reparentSpace` from `lib/spaces.ts`) — rejected for the reason above; also would
have required the modal to handle a "created but not nested" partial-failure UI
state that the spec's Edge Cases don't describe.

## 4. Default `sector` when the user isn't asked for one

**Decision**: `CreateSpaceRequest.sector` becomes `str = "General"`
(previously required with no default). When the "Add Space" modal doesn't send
`sector` at all, the new space gets `sector="General"`.

**Rationale**: `sector` is a required, non-empty `str` on the `Space` domain
model and is already rendered directly on `FolderTile` (`<p>{space.sector}</p>`),
so it can't be left blank or nullable without adding a new "no sector" display
state to an otherwise-unrelated component. A fixed default keeps `FolderTile`
unchanged and matches the spec's Assumption that non-essential attributes are
system-assigned rather than asked of the user; it remains editable later if a
sector-edit capability is ever added (out of scope here, same as slug/parent
edits are already separate features).

**Alternatives considered**: Making `sector` nullable/optional end-to-end —
rejected as unnecessary schema/UI churn for a field the spec explicitly says
should not be surfaced at creation time.

## 5. Auditing the creation event itself

**Decision**: Add a new audit action, `space_created` (`entity_type="space"`,
`entity_id=<new space id>`, `metadata={"company_id", "parent_space_id"}`), written
in `create_space` alongside the existing `member_invited` audit entry that's
already written when the creator's admin membership is granted.

**Rationale**: FR-010 requires the creation act itself to be part of the audit
trail. Today only the resulting membership grant is audited (`member_invited`);
there's no record that distinguishes "a space was created" from "a member was
added to an existing space" if one ever reads the audit log for space lifecycle
events.

**Alternatives considered**: Relying solely on the existing `member_invited`
entry — rejected; it conflates two distinct events and would silently stop
covering "creation" if the auto-admin-grant behavior ever changed independently.
