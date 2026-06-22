# Research: Landing Page Claude-Chat Design

## Layout: sticky input bar without root-layout restructuring

**Decision**: Use the existing natural-flow layout (body scrolls) with `position: sticky; bottom: 0` on the conversation input bar.

**Rationale**: Next.js App Router's root `layout.tsx` applies to all pages. Modifying `overflow` or `height` there affects every route. The sticky approach requires no overflow changes — the body scrolls normally and `sticky bottom-0` pins the input to the viewport bottom once the user starts scrolling up through message history.

**Alternatives considered**:
- *Route group with dedicated layout*: Cleanest architecturally, but requires moving all 15+ pages into route groups — out of scope.
- *Fixed positioning*: Works, but requires `padding-bottom` on the message container equal to the input bar height, which is fragile to height changes.
- *`h-screen flex-col` on root layout*: Would change scroll context for every page; risks regressions.

## NavBar height constant

**Decision**: Use `3.25rem` (≈ 52 px at 16 px base) as the navbar height constant in `calc()`.

**Rationale**: NavBar CSS is `py-3` (0.75 rem × 2 = 1.5 rem) + `text-xl` line-height (1.75 rem) = 3.25 rem. This is computed from Tailwind source classes, not measured at runtime, to avoid a JS height measurement or a CSS variable.

**Alternatives considered**:
- *CSS custom property via layout*: More robust to future changes but adds complexity.
- *JS measurement with `useRef`*: Reactive but adds a ResizeObserver and a re-render.

**How to apply**: The landing page wrapper uses `min-h-[calc(100dvh-3.25rem)]`. If the NavBar classes change materially, update this constant.

## ChatInterface layout modes

**Decision**: The existing `ChatInterface` component manages both states internally (no new props). A ternary on `turns.length === 0` renders either the welcome view or the conversation view.

**Rationale**: The component is only used on the landing page. No prop drilling needed. The state (`turns`, `input`) is already owned by the component.

**Alternatives considered**:
- *Separate `WelcomeScreen` and `ConversationView` components*: Cleaner separation, but the feature scope is small and the shared state (`turns`, `input`, `handleSubmit`) would require lifting up or a context. Premature abstraction.

## Starter prompts

**Decision**: 4 hardcoded strings relevant to Tessera's knowledge-management use case. No backend, no personalization.

**Rationale**: The spec explicitly says "hardcoded to a curated set of 3–4 questions." Keeping them in a `const` array inside `ChatInterface.tsx` is the simplest solution.

**Chosen prompts**:
1. `"What's in our product roadmap?"`
2. `"Summarize the latest meeting notes"`
3. `"Find our onboarding documentation"`
4. `"What changed in the last release?"`

## New packages required

**Decision**: None.

**Rationale**: All required primitives (React state, Tailwind CSS, Vitest + Testing Library) are already in the project.

## Test strategy

**Decision**: Update the existing `chat.test.tsx` empty-state assertion (currently checks for `"ask a question"` text that will be removed) and add a new `describe` block covering starter-prompt behavior.

**Rationale**: The test checks rendered DOM text. The new welcome state shows a heading ("Tessera") and a tagline instead of the placeholder paragraph. Updating the assertion to `getByRole("heading", { name: /tessera/i })` maintains the intent (verify the empty state is rendered) without coupling to a specific phrase.
