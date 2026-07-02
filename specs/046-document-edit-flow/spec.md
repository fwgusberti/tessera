# Feature Specification: Document Edit Flow

**Feature Branch**: `046-document-edit-flow`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "in document page create edition flow. When editing a document the user msuts ssee a windows in the left that has the editable .md and a realtime render in the right. Not now but in the future the user may opt in for an text editor google docs style"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Edit document content with a live preview (Priority: P1)

A space member with write access opens a document and enters an edit view. The
edit view shows two panes side by side: the left pane holds the raw, editable
Markdown source; the right pane shows a live rendered preview of that same
content. As the member types or changes the Markdown source, the preview
updates to reflect the new content without any manual refresh or extra step.
Only members with write access to the document's space can open this view —
anyone else neither sees nor can reach the edit entry point.

**Why this priority**: This is the core value of the feature — without a
working split editable/preview view, there is no editing flow at all. It must
work end-to-end (including access control) before anything else matters.

**Independent Test**: As a space member with write access, open a document,
enter edit mode, and confirm the source/preview split view is visible. Type a
Markdown change (e.g., add a heading or a list) in the left pane and confirm
the right pane reflects the formatted result within a second, with no
explicit "preview" action required. Separately, confirm a user without write
access to that space cannot see or reach the edit entry point.

**Acceptance Scenarios**:

1. **Given** a document in a space the user has write access to, **When** the
   user opens the document and chooses to edit it, **Then** an edit view
   opens showing the raw Markdown source on the left and a rendered preview
   on the right.
2. **Given** the edit view is open, **When** the user changes the Markdown
   source in the left pane, **Then** the rendered preview in the right pane
   updates automatically to match the new content.
3. **Given** a user who is not a member of the document's space (or is a
   member without write access), **When** they view the document, **Then**
   no edit entry point is available to them.

---

### User Story 2 - Edits are protected against accidental loss (Priority: P2)

While a user is editing, the system periodically autosaves their in-progress
changes in the background, without requiring an explicit "Save" action. If
the browser crashes, the tab is closed unexpectedly, or the page is
reloaded, the user's most recent autosaved content is preserved so they do
not have to redo their work from scratch.

**Why this priority**: Editing sessions can be interrupted at any time;
without autosave, a crash or accidental navigation could destroy real work.
This builds directly on User Story 1's editing view.

**Independent Test**: Open the edit view, make a Markdown change, wait for an
autosave to occur, then reload or reopen the edit view without explicitly
saving or finishing the session. Confirm the previously entered content is
still present.

**Acceptance Scenarios**:

1. **Given** the user has made changes in the edit view, **When** enough time
   passes for an autosave to occur, **Then** the in-progress content is
   persisted without the user taking any explicit save action.
2. **Given** an autosave has occurred, **When** the browser is closed and the
   edit view is reopened before the editing session is finalized, **Then**
   the user's most recently autosaved content is restored.
3. **Given** an autosave attempt fails (e.g., a network error), **When** the
   failure occurs, **Then** the user sees a clear warning and their unsaved
   edits remain visible and editable in the pane (not discarded).

---

### User Story 3 - Finishing an edit session creates a new version (Priority: P3)

When a user finishes an editing session — by navigating away from the edit
view or by leaving it idle long enough to time out — the system finalizes
their changes as a new version of the document, visible in the document's
existing version history. If the user leaves without making any changes, no
new version is created.

**Why this priority**: This turns protected in-progress edits (User Story 2)
into a durable, auditable part of the document's history, and is the
natural conclusion of an edit session. It depends on editing (P1) and
autosave (P2) already working.

**Independent Test**: Open the edit view, make a Markdown change, then
navigate away from the edit view. Confirm a new version appears in the
document's version history containing the edited content. Separately, open
the edit view and leave immediately without changing anything, and confirm
no new version is created.

**Acceptance Scenarios**:

1. **Given** the user has changed the document's content in the edit view,
   **When** they navigate away from the edit view, **Then** a new document
   version is created containing their final edited content, and it appears
   in the version history.
2. **Given** the user has changed the document's content in the edit view,
   **When** the editing session times out due to inactivity, **Then** the
   same finalization occurs as if the user had navigated away.
3. **Given** the user opened the edit view but made no content changes,
   **When** they leave the edit view, **Then** no new version is created.

---

### Edge Cases

- Two space members open edit mode on the same document at the same time:
  the system does not merge their edits live; whichever session finalizes
  (navigates away or times out) last determines the resulting version. A
  warning that another session may be active is acceptable but full
  real-time collaborative merging is out of scope (see Assumptions).
- A user's write access to the space is revoked while they have an active
  edit session: further autosaves and session finalization for that user
  must stop once access is revoked.
- A user clears all content and leaves the editor empty: saving an
  intentionally empty version is allowed, matching how a user would clear a
  document in place.
- The browser or device loses power/connectivity abruptly, bypassing any
  "are you sure" prompt: at most the edits made since the last successful
  autosave may be lost; everything up to the last autosave is preserved.
- The user returns to the edit view and keeps interacting shortly before the
  inactivity timeout would trigger: the session continues normally and the
  timeout clock resets on activity.
- Markdown input that is unusual or malformed (e.g., very large tables,
  deeply nested lists): the preview pane renders best-effort and never
  crashes or blanks the whole edit view.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an "Edit" entry point on the document
  detail page, available only to users who have write access to the space
  that contains the document.
- **FR-002**: System MUST prevent users without write access to the
  document's space from opening or otherwise reaching the edit view.
- **FR-003**: The edit view MUST display two side-by-side panes: the raw
  editable Markdown source on the left, and a rendered preview of that same
  content on the right.
- **FR-004**: The rendered preview MUST update automatically to reflect the
  current content of the editable pane as the user types, with no manual
  refresh or explicit "preview" action required.
- **FR-005**: The rendered preview MUST support the same Markdown formatting
  already supported on the read-only document view (e.g., GFM tables, code
  blocks, lists, headings) so it accurately reflects what will be shown
  after the edit is finalized.
- **FR-006**: The rendered preview MUST NOT execute injected scripts or
  render arbitrary raw HTML from the Markdown source, matching the existing
  safe-rendering behavior of the read-only document view.
- **FR-007**: System MUST automatically save the user's in-progress edits at
  regular intervals during an editing session, without requiring an
  explicit "Save" action from the user.
- **FR-008**: If an autosave attempt fails, System MUST surface a clear,
  visible warning to the user and MUST NOT discard the user's unsaved edits
  from the editable pane.
- **FR-009**: System MUST finalize an editing session — creating a new,
  persisted document version containing the session's final content — when
  the user navigates away from the edit view.
- **FR-010**: System MUST also finalize an editing session after a period of
  user inactivity within the edit view (session timeout), using the same
  finalization behavior as navigating away.
- **FR-011**: System MUST NOT create a new document version when an editing
  session ends without any content changes having been made.
- **FR-012**: System MUST NOT create a new document version for every
  individual autosave — only one version is finalized per completed editing
  session.
- **FR-013**: System MUST preserve all prior document versions after a new
  edit is finalized, so existing version history remains complete and
  browsable.
- **FR-014**: Users MUST be able to leave the edit view at any time; doing so
  triggers session finalization per FR-009–FR-012.

### Key Entities

- **Document**: The existing document being edited; identity and metadata
  are unchanged by this feature.
- **Document Version**: The existing versioned record of a document's
  content. This feature adds a new way for versions to be created — one
  automatically finalized per completed edit session — alongside however
  versions are created today.
- **Edit Session**: The in-progress, autosaved working state of a document
  being edited by a specific user. Persists incrementally during editing and
  either finalizes into a new Document Version (on navigate-away or
  timeout) or is discarded if no changes were made.
- **Space Membership**: The existing membership/role relationship that
  determines whether a user has write access to a space, and therefore
  whether they can edit documents within it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The rendered preview reflects the user's latest edits within 1
  second of the user pausing typing, so editing feels live rather than
  batch-updated.
- **SC-002**: In an unexpected interruption (crash, closed tab, lost
  connection), a user never loses more than the edits made since the last
  successful autosave.
- **SC-003**: 100% of editing sessions that included a content change and
  then ended (navigate-away or timeout) result in a new, retrievable version
  in the document's version history.
- **SC-004**: 100% of attempts by users without write access to a document's
  space to open or use the edit view are blocked.
- **SC-005**: A first-time user can locate the edit entry point and
  successfully make and finalize a change without external help in at least
  90% of observed attempts.

## Assumptions

- "Write access" to a space follows the existing space
  membership/role model already used elsewhere in the product; this feature
  does not introduce a new permission tier.
- A reasonable, unspecified inactivity duration (on the order of tens of
  minutes) is used to determine when an idle editing session times out and
  finalizes; the exact duration is an implementation detail, not a
  user-facing requirement.
- Autosaved in-progress content is stored separately from finalized document
  versions until a session ends, so a page refresh or crash mid-session does
  not lose edits made since the last autosave tick, without polluting the
  version history with every autosave tick.
- Finalizing an edit session updates the document's current content
  immediately for all viewers (consistent with a shared, always-current
  document rather than requiring a separate approval/publish step for every
  edit). The existing publish action continues to govern only the
  document's initial lifecycle transition and is unaffected by this
  feature.
- Real-time collaborative editing (multiple users seeing each other's
  keystrokes live, with conflict merging) is out of scope for this feature.
  When two sessions overlap, the session that finalizes last wins, with no
  automatic merge.
- This feature delivers only the raw-Markdown-source-with-live-preview
  editing mode described above. A rich-text, WYSIWYG ("Google Docs style")
  editing mode is a possible future opt-in alternative and is explicitly
  out of scope for this feature — it is not designed, built, or exposed as
  an option now.
- Keeping any downstream search index in sync with newly finalized content
  is out of scope for this feature; existing indexing behavior is unaffected
  unless separately triggered.
