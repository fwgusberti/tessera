# Data Model: Responsive UI for Smartphones

**Feature**: 019-responsive-ui | **Date**: 2026-06-20

This feature introduces no new database entities, API fields, or persistent state. It is a pure frontend layout change. This document captures the **UI design entities** — the conceptual objects the implementation must reason about.

---

## Entity: Viewport Breakpoint

The single boundary used throughout this feature.

| Name | Width | Tailwind prefix | Meaning |
|------|-------|-----------------|---------|
| Mobile | 0 – 767px | (default / no prefix) | Smartphone portrait range; the new responsive target |
| Desktop | ≥ 768px | `md:` | Existing desktop layout; must remain unchanged |

> **Rule**: Use `md:` as the only breakpoint for mobile/desktop switches. Do not introduce `sm:` (640px) as a primary breakpoint unless a component has a specific in-between need (e.g., ProgressStepper connector width).

---

## Entity: Touch Target

A minimum-size constraint applied to all interactive elements on mobile viewports.

| Field | Value | Enforcement |
|-------|-------|-------------|
| `min_width` | 44px | `min-w-[44px]` Tailwind class |
| `min_height` | 44px | `min-h-[44px]` Tailwind class |
| `applies_to` | buttons, `<a>` nav links, form submit buttons, select elements | |
| `source` | WCAG 2.1 SC 2.5.5 (AAA) / Apple HIG / FR-003 | |

---

## Entity: Mobile Nav State

Client-side state held in `NavBar.tsx` by React `useState`.

| Field | Type | Initial | Description |
|-------|------|---------|-------------|
| `isMenuOpen` | `boolean` | `false` | Whether the mobile hamburger menu overlay is visible |

**Transitions**:
- `hamburger_button_click` → toggles `isMenuOpen`
- `nav_link_click` → sets `isMenuOpen = false`
- `Escape_key` → sets `isMenuOpen = false`
- `outside_click` (on overlay) → sets `isMenuOpen = false`

---

## Entity: Responsive Layout Mode (per component)

Maps each modified component to its mobile vs. desktop layout mode.

| Component | Mobile layout | Desktop layout |
|-----------|--------------|----------------|
| `NavBar` | Top bar with hamburger; links in vertical overlay | Top bar with horizontal link row |
| `SpaceSelector` | Full-width select | Inline (auto-width) select |
| `ProgressStepper` | Compressed connectors (w-6), smaller margins | Standard connectors (w-12), standard margins |
| `AddDocumentModal` | Language + Confidentiality stacked 1-col | 2-column grid |
| Documents table | Scroll-container + hidden Confidentiality column | Full 3-column table |
| Document detail header | Title + actions stacked vertically | Title left, actions right (flex-row) |
| Login / Register card | py-8 top padding, min-h-dvh | py-12 top padding, min-h-screen |
| Onboarding card | p-4 inner padding | p-8 inner padding |

---

## Non-Entities (explicitly out of scope)

- Tablet (768px–1023px) layout — desktop mode applies, no special treatment
- Landscape smartphone orientation — best-effort (not explicitly tested)
- PWA manifest, service worker, native app packaging
- New color, typography, or spacing tokens
