# Feature Specification: Landing Page Claude-Chat Design

**Feature Branch**: `026-landing-claude-design`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "make landing page design similar to Claude chat"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Centered Chat Welcome Screen (Priority: P1)

When a user opens the landing page (or has no conversation yet), they see a clean, centered welcome view — prominent product name, optional tagline, and a large centered input area that invites them to start a conversation. The surrounding space is calm and uncluttered.

**Why this priority**: This is the first thing every visitor sees. A welcoming, focused entry point reduces friction and immediately communicates the product's purpose. It mirrors the Claude.ai pattern where the blank-slate state feels intentional rather than empty.

**Independent Test**: Open the landing page as an authenticated user with no prior chat turns. Verify the welcome heading, tagline (if shown), and centered input box are visible with no message history in the way.

**Acceptance Scenarios**:

1. **Given** I am authenticated and navigate to the landing page, **When** no prior conversation turns exist, **Then** I see a centered welcome heading, a descriptive tagline, and a large input field centered in the viewport.
2. **Given** the welcome screen is displayed, **When** I look at the page, **Then** there are no stat cards, navigation cards, or other dashboard widgets visible in the primary content area.
3. **Given** the welcome screen is displayed, **When** I look at the page, **Then** the input area is clearly the focal point with ample whitespace above and below.

---

### User Story 2 - Pinned Input Bar with Chat History (Priority: P2)

Once a conversation starts, the layout transitions: messages scroll in the main area while the input bar stays pinned at the bottom of the viewport, matching the Claude.ai conversation layout. The user never loses access to the input while reading previous turns.

**Why this priority**: This is the core interaction pattern for ongoing conversations. Without a pinned input, the experience breaks for multi-turn dialogs — users must scroll to the bottom to reply.

**Independent Test**: Send at least one message, then scroll up through the message history. Verify the input bar remains visible and accessible at the bottom without scrolling down.

**Acceptance Scenarios**:

1. **Given** I have sent at least one message, **When** the page renders, **Then** the input bar is fixed to the bottom of the viewport.
2. **Given** a conversation with several turns, **When** I scroll up through the message history, **Then** the input field remains anchored at the bottom and is always reachable.
3. **Given** the chat has multiple turns, **When** I view the messages, **Then** messages are displayed in a scrollable column that fills the space between the top of the viewport and the pinned input bar.

---

### User Story 3 - Suggested Starter Prompts (Priority: P3)

On the welcome screen (no prior turns), a small set of suggested prompts is displayed near the input area. Clicking one populates the input field with that prompt, allowing the user to get started quickly without typing from scratch — exactly as Claude.ai offers conversation starters.

**Why this priority**: Starter prompts lower the "blank page" barrier and demonstrate the system's capabilities. They are a quality-of-life feature that does not block core functionality.

**Independent Test**: Load the welcome screen and verify starter-prompt chips are displayed. Click one and confirm the input field is populated with that text. The user can then edit or send it.

**Acceptance Scenarios**:

1. **Given** the welcome screen with no conversation history, **When** I see the page, **Then** 3–4 suggested prompt chips are displayed near the input area.
2. **Given** the suggestion chips are visible, **When** I click one, **Then** its text is inserted into the input field and focus moves to the input.
3. **Given** the suggestion chips are visible, **When** I have already sent a message, **Then** the chips are hidden (they only appear on the empty-state welcome screen).

---

### Edge Cases

- What happens when the conversation history is very long? The message area should scroll independently without the pinned input bar shifting position.
- How does the layout respond on narrow viewports (mobile-width)? The centered welcome layout and pinned input must remain usable at 375 px wide.
- What happens if the user's session expires while on the page? The existing auth-guard behavior handles this; the chat layout should not introduce a new unauthenticated state.
- What happens when a message is pending (loading)? A loading indicator should be visible in the message area so the user knows to wait before typing again — identical to the current behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The landing page MUST display a centered, full-height welcome view when no conversation turns exist.
- **FR-002**: The welcome view MUST include a prominent product name heading and a short tagline describing the assistant's purpose.
- **FR-003**: The welcome view MUST display 3–4 suggested starter prompts near the input field; clicking one MUST populate the input with that text.
- **FR-004**: The main input area MUST be visually centered on the welcome screen, occupying the most prominent position in the viewport.
- **FR-005**: Once at least one message exists, the layout MUST switch to a conversation view: a scrollable message history area with the input bar pinned to the bottom.
- **FR-006**: The pinned input bar MUST remain fixed at the bottom of the viewport regardless of scroll position in the message history.
- **FR-007**: The message history area MUST be independently scrollable without moving the pinned input bar.
- **FR-008**: Existing chat functionality (send message, streaming/loading state, multi-turn history) MUST be preserved without regression.
- **FR-009**: All dashboard widgets (stat cards, navigation cards) present in the previous layout MUST be removed from the primary content area of the landing page.
- **FR-010**: The layout MUST be responsive and remain usable at mobile-equivalent widths (minimum 375 px).

### Key Entities

- **Welcome Screen**: The initial zero-message state of the landing page, featuring a heading, tagline, starter prompts, and centered input.
- **Conversation View**: The active-conversation state showing a scrollable message list and a pinned input bar.
- **Starter Prompt**: A short pre-written suggestion displayed on the welcome screen that populates the input when clicked.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time visitor can start a conversation within 10 seconds of the page loading, without needing to scroll or locate a hidden input.
- **SC-002**: On a screen with 10+ conversation turns, the input bar remains visible and usable without any scrolling action from the user.
- **SC-003**: Clicking a suggested starter prompt populates the input in under 200 ms (immediate, no perceptible delay).
- **SC-004**: The welcome screen layout matches the visual structure of Claude.ai's blank-slate chat view (centered heading, centered input, starter suggestions) as assessed by a visual side-by-side comparison.
- **SC-005**: All existing multi-turn chat behaviors (message send, loading state, history preservation) pass their existing acceptance tests without modification to core chat logic.
- **SC-006**: The page renders correctly and is fully usable at 375 px viewport width with no horizontal scroll or clipped elements.

## Assumptions

- The existing `ChatInterface` component and underlying chat logic (`askAssistant`, `MessageBubble`, turn state) are reused as-is; only the layout and visual presentation of the landing page change.
- The stat cards and navigation cards currently on the landing page are removed as part of this feature; their content remains accessible through other navigation routes (Spaces, Documents, etc.).
- "Similar to Claude chat" means adopting the structural layout pattern (centered welcome, pinned bottom input, starter prompts) rather than pixel-perfect copying of Claude's visual brand colors or typography. The Tessera design system (Slate + Indigo palette, Geist font) continues to apply.
- Starter prompts are hardcoded to a curated set of 3–4 questions relevant to Tessera's knowledge-management use case; no backend or user-personalization is required for this feature.
- The authenticated user state (handled by `AuthGuard`) is not affected; the landing page continues to require authentication before rendering the chat.
- Mobile responsiveness targets 375 px as the minimum supported width, consistent with other pages in the application.
