# Research: Company Menu

## 1. Listing a user's companies

**Decision**: Add `GET /v1/companies/me` to the companies router.

**Rationale**: `SqlCompanyRepository.list_memberships_for_user(user_id)` already exists and returns `list[CompanyMembership]`, and `get_by_id(company_id)` resolves each membership to a full `Company`. A single new endpoint stitches these together and returns `[{id, name, role}]` — no new DB methods required.

**Alternatives considered**: Embedding company list in the JWT or the refresh response. Rejected because it would bloat the token and require re-login on membership changes.

---

## 2. Active company state persistence

**Decision**: Persist the active company ID in `localStorage` under the key `tessera_active_company_id`, mirroring the access-token pattern already used in `lib/auth.tsx`.

**Rationale**: The spec explicitly assumes "active company selection is persisted in the user's session so that page refreshes do not reset it." `localStorage` is already the persistence layer for auth tokens; adding one more key is consistent and requires no backend changes. The Constitution (Principle III) requires explicit end-user authorization for local persistence — we satisfy this because the user explicitly selects the active company via the menu.

**Alternatives considered**: Server-side session field (e.g., `user.active_company_id` in DB). Rejected: adds migration, backend complexity, and introduces server state for a purely client-side UX concern. Cookie: would work but the project already uses localStorage for tokens.

---

## 3. Company context in the React tree

**Decision**: Implement a new `CompanyContext` (React context + provider in `lib/company.tsx`) that wraps the app, similar to `AuthContext`. It exposes `companies`, `activeCompany`, `setActiveCompany`, and `createAndSetActive`.

**Rationale**: Multiple components (NavBar, company-scoped pages) need the active company. A React context avoids prop-drilling and mirrors the existing `AuthContext` pattern. The context loads on mount via `GET /v1/companies/me` once the user is authenticated.

**Alternatives considered**: Zustand or other state lib. Rejected: overkill for a single piece of global state; project has no existing global state library beyond React context.

---

## 4. Company settings navigation target

**Decision**: "Company settings" in the menu navigates to `/settings/company` — a new page stub. For this feature the stub page only needs to exist and render a heading; full settings are out of scope.

**Rationale**: The spec (FR-007) only requires navigation to a company settings section, not full implementation of that section. Creating a stub satisfies the acceptance scenario while keeping scope bounded.

---

## 5. Create new company flow (in-menu)

**Decision**: Open a small modal (not a full onboarding page) with a single required field (name) and two optional fields (industry, team_size). On success, call `POST /v1/companies`, then refresh the company list, and set the new company as active.

**Rationale**: The spec says "lighter, non-onboarding path." The existing `POST /v1/companies` endpoint already handles creation and returns `{id, name, role}`. No backend changes needed for this path. The existing `CompanyForm` onboarding component is too large and wizard-linked; a simple modal is purpose-built and avoids coupling.

---

## 6. Role enforcement for "Company settings" visibility

**Decision**: Derive the current user's role in the active company from the `CompanyContext` (which carries `role` from the `/me` endpoint). Show "Company settings" only when `role === "admin"`.

**Rationale**: The role data is already returned alongside company membership. No additional API call required. Matches spec FR-007.

---

## 7. No-company state

**Decision**: When `companies` is empty (after load), display a "Create or join a company" prompt in the navbar area where the company menu would otherwise appear, linking to `/register/company` (existing onboarding path) or opening the create modal directly.

**Rationale**: Spec FR-008. The onboarding flow already handles first-time company creation; the in-menu create path can serve as the shortcut.
