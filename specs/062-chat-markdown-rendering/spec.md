# Feature Specification: Chat Markdown Rendering

**Feature Branch**: `062-chat-markdown-rendering`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "o chat, hoje, mostra o resultado em .md mostre o resultado formatado igual na visualização de documentos"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a formatted chat answer (Priority: P1)

A user asks a question in the chat and receives an answer that contains
structure — headings, bold terms, bullet lists, numbered steps. Today that
answer is shown as raw text, so the user sees markup symbols (`**`, `#`, `-`)
instead of formatting. With this feature, the answer appears fully formatted,
the same way a document's content appears in the document viewer.

**Why this priority**: This is the entire feature. Answers sourced from
markdown documents routinely contain markup, and showing raw symbols makes
answers harder to read and looks broken to users.

**Independent Test**: Ask a question whose answer contains headings, bold
text, and a list; verify the answer displays with real formatting and no
visible markup symbols.

**Acceptance Scenarios**:

1. **Given** a chat answer containing markdown headings, bold text, and
   bullet lists, **When** the answer is displayed, **Then** the user sees
   rendered headings, bold text, and bullets — no raw markup symbols.
2. **Given** a chat answer that is plain prose with no markup, **When** it is
   displayed, **Then** it reads exactly as before, as normal paragraphs.
3. **Given** a chat answer containing a link, **When** the user clicks it,
   **Then** the link opens without discarding the current chat conversation.

---

### User Story 2 - Formatting parity with the document viewer (Priority: P2)

A user who reads a document in the document viewer and then asks the chat
about that document sees the same visual treatment in both places: tables,
code blocks, quotes, and other rich elements look consistent, so the answer
feels like a faithful excerpt of the source material.

**Why this priority**: Consistency is the explicit ask ("formatted the same
as the document view"). Covers the richer, less frequent elements beyond
basic text styling.

**Independent Test**: Ask a question whose answer includes a table and a code
block; compare side-by-side with the same content opened in the document
viewer and confirm equivalent rendering.

**Acceptance Scenarios**:

1. **Given** a chat answer containing a table, **When** it is displayed,
   **Then** the table renders with rows and columns as it would in the
   document viewer.
2. **Given** a chat answer containing a code block, **When** it is displayed,
   **Then** the code appears in a distinct monospaced block, not inline prose.
3. **Given** a wide element (long table or long code line) in an answer,
   **When** it is displayed inside the chat bubble, **Then** the chat layout
   is not broken — the element is contained within the bubble.

---

### User Story 3 - Existing chat behaviors are preserved (Priority: P3)

A user continues to see all existing chat states exactly as today: the
loading indicator while an answer is being produced, error messages when
something fails, the "I don't have enough information" response, and the
source citations listed under an answer.

**Why this priority**: Regression protection. The formatting change must not
disturb any surrounding chat behavior.

**Independent Test**: Exercise each chat state (pending, error, don't-know,
answer with citations) and confirm each looks and behaves as before.

**Acceptance Scenarios**:

1. **Given** an answer with source citations, **When** it is displayed,
   **Then** the citations list appears below the formatted answer, unchanged.
2. **Given** a question the assistant cannot answer, **When** the don't-know
   response is shown, **Then** it appears exactly as today.

---

### Edge Cases

- Malformed or unbalanced markup (e.g., an unclosed `**`) must still display
  legibly — degraded to plain text is acceptable; a broken or blank bubble is
  not.
- Answers containing embedded HTML or script content must never execute; such
  content is shown inert or stripped.
- A very long formatted answer must scroll normally within the conversation
  without breaking the chat layout.
- Markup symbols that are part of the actual content (e.g., an answer quoting
  literal markdown syntax inside a code block) must remain visible as text.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Chat answers MUST be displayed with markdown formatting rendered
  (headings, bold, italic, lists, links, inline code, code blocks, tables,
  block quotes) instead of raw markup text.
- **FR-002**: The set of supported formatting elements and their visual
  treatment MUST match the document viewer, adjusted only as needed to fit
  the chat bubble's dimensions.
- **FR-003**: Answers without any markup MUST render as plain paragraphs,
  visually equivalent to the current behavior.
- **FR-004**: Embedded HTML or executable content inside an answer MUST NOT
  be executed or interpreted; it MUST be neutralized (rendered inert or
  stripped).
- **FR-005**: Links inside answers MUST open without navigating the user away
  from the ongoing chat conversation.
- **FR-006**: All non-answer chat states — pending/loading, error, don't-know
  (including the suggested-space hint), and the citations list — MUST remain
  functionally and visually unchanged.
- **FR-007**: Formatted content MUST stay contained within the chat bubble;
  wide elements MUST NOT cause the conversation or page layout to overflow.

### Key Entities

- **Chat Answer**: The assistant's response text for one conversation turn.
  May contain markdown markup originating from source documents. Carries
  associated citations and status (pending, complete, error, don't-know).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For answers containing markup, users see zero raw markdown
  symbols (`#`, `**`, `-` list markers, `|` table pipes) rendered as literal
  text outside of code blocks.
- **SC-002**: 100% of the formatting element types supported in the document
  viewer render formatted in chat answers as well.
- **SC-003**: All pre-existing chat interactions (asking, loading, errors,
  don't-know, citation links) complete successfully with no change in
  behavior.
- **SC-004**: No chat answer, regardless of content width or length, breaks
  the conversation layout on a standard desktop or mobile viewport.

## Assumptions

- Answers are produced by the assistant from markdown source documents, so
  markdown is the only markup format that needs rendering; no other formats
  (HTML documents, rich text) are in scope.
- The user's question bubble is unaffected — only the assistant's answer is
  formatted. Questions are typed by users as plain text.
- The document viewer's current visual style is the accepted reference for
  how formatted elements should look; no new visual design is required.
- Citation quotes shown under an answer remain plain-text excerpts as today;
  formatting them is out of scope.
- No changes to how answers are generated or stored are needed — this is a
  display-only change.
