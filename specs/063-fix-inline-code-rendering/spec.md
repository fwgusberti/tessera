# Feature Specification: Fix Inline Code Rendering

**Feature Branch**: `063-fix-inline-code-rendering`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "the .md renderer is not rendering inline code as `main` the ` is shown"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inline code displays without backtick symbols (Priority: P1)

A user reads content that contains an inline code snippet — for example, a
chat answer or a document mentioning the `main` branch. Today the snippet is
shown with visible backtick characters around it (`` `main` ``), which reads
as broken markup. With this fix, the user sees just the snippet text, styled
as code, with no backtick characters visible.

**Why this priority**: This is the reported defect and the entire feature.
Visible markup symbols contradict the purpose of formatted rendering and make
the product look broken.

**Independent Test**: Display content containing an inline code snippet in
both the chat and the document viewer; verify the snippet appears without
surrounding backtick characters in both places.

**Acceptance Scenarios**:

1. **Given** a chat answer containing an inline code snippet, **When** the
   answer is displayed, **Then** the snippet text appears without any
   backtick characters around it.
2. **Given** a document whose content contains inline code snippets, **When**
   the document is opened in the document viewer, **Then** every snippet
   appears without backtick characters.
3. **Given** a sentence containing several inline code snippets, **When** it
   is displayed, **Then** none of them show backtick characters and the
   surrounding prose is unaffected.

---

### User Story 2 - Inline code remains visually distinct (Priority: P2)

After the backtick symbols are removed, a user can still immediately tell
which words are code: inline snippets keep a distinct visual treatment
(monospaced, subtly set off from prose) so no meaning is lost by hiding the
markup.

**Why this priority**: Removing the backticks must not flatten inline code
into ordinary prose — the distinction the author intended must survive.

**Independent Test**: Display a sentence mixing prose and an inline snippet;
verify the snippet is visually distinguishable from the surrounding text
without relying on backtick characters.

**Acceptance Scenarios**:

1. **Given** a paragraph containing an inline code snippet, **When** it is
   displayed, **Then** the snippet is visibly distinct from the surrounding
   prose (e.g., different typeface treatment).
2. **Given** inline code appearing inside other formatted elements (a list
   item, a table cell, a heading), **When** displayed, **Then** it is
   rendered as distinct code there as well, without backtick characters.

---

### User Story 3 - Intentional backticks are preserved (Priority: P3)

A user reading content that legitimately contains backtick characters — for
example, a code block that demonstrates markdown syntax, or prose with a
lone unpaired backtick — still sees those characters exactly as authored.

**Why this priority**: Regression protection. The fix must remove only the
decorative symbols around rendered inline code, never characters that are
part of the actual content.

**Independent Test**: Display a code block whose content includes backtick
characters and a paragraph containing a single unpaired backtick; verify both
show the backticks as literal text.

**Acceptance Scenarios**:

1. **Given** a code block whose content includes backtick characters,
   **When** it is displayed, **Then** those backticks remain visible inside
   the block.
2. **Given** prose containing a single unpaired backtick, **When** it is
   displayed, **Then** the backtick appears as typed.

---

### Edge Cases

- Inline code nested inside other formatting (bold, links, headings, list
  items, table cells) must also render without backtick symbols.
- Empty or whitespace-only inline code spans must not produce stray symbols
  or layout artifacts.
- Content that spells out markdown syntax inside a code block (e.g., teaching
  material showing `` `example` ``) must keep its backticks verbatim.
- Both display surfaces (chat answers and document viewer) must behave
  identically, since users compare them side by side.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Inline code snippets in displayed markdown MUST appear without
  the surrounding backtick characters.
- **FR-002**: Rendered inline code MUST remain visually distinct from
  surrounding prose (distinct typeface treatment) so it is still
  recognizable as code.
- **FR-003**: The correction MUST apply consistently to every surface that
  displays markdown content — chat answers and the document viewer.
- **FR-004**: Backtick characters that are part of the actual content
  (inside code blocks, or literal/unpaired backticks in prose) MUST remain
  visible exactly as authored.
- **FR-005**: All other formatting elements (headings, bold, lists, links,
  tables, code blocks, quotes) MUST render exactly as they do today.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero backtick characters are visible around inline code
  snippets in chat answers and in the document viewer.
- **SC-002**: 100% of inline code snippets remain visually distinguishable
  from surrounding prose after the fix.
- **SC-003**: All other markdown element types render identically to their
  pre-fix appearance (no visual regressions).
- **SC-004**: Chat and document viewer render the same inline-code content
  identically.

## Assumptions

- The backtick characters are added by the display layer as decoration; the
  stored content and the answers produced by the assistant are correct and
  need no change.
- Chat and the document viewer share the same rendering mechanism, so a
  single correction covers both surfaces; both are in scope regardless.
- The existing visual style for code blocks (multi-line code) is already
  correct and unaffected by this fix.
- No new visual design is required — inline code keeps its current styling
  minus the backtick symbols.
