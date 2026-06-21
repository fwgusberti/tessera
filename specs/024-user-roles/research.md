# Research: User Roles (024)

## Decision 1 — Platform Admin Representation

**Decision**: Keep `User.is_admin: bool` as the platform admin flag. Do NOT add a `platform_role` column.

**Rationale**: `User.is_admin` is already used throughout auth middleware (`oidc.py`), permission checks (`access.py`), and API routers. Adding a redundant `platform_role` enum that encodes the same binary state introduces inconsistency without benefit at current scale. The existing boolean maps cleanly to the spec's `PlatformRole.USER / ADMIN` semantics.

**Alternatives considered**: Adding `platform_role: Mapped[str]` column with `USER / ADMIN` values. Rejected because it duplicates `is_admin` and requires a dual-write migration with no upside.

---

## Decision 2 — Space Role Enum Naming

**Decision**: Add a new `SpaceRole` enum (`VIEWER | EDITOR | ADMIN`) in `tessera_core/domain/entities.py`. Keep the existing `UserRole` enum unchanged.

**Rationale**: The existing `UserRole` (`READER | CONTRIBUTOR | OWNER | SPACE_ADMIN`) drives the IDP group-based permission system (`RolePermission` model). Renaming or merging it would break the existing access checks in `permissions/access.py` and all tests that depend on them. The new `SpaceRole` enum represents direct user–space membership roles, which are semantically distinct from IDP-group roles. Two separate enums prevents confusion and allows both systems to coexist.

**Alternatives considered**: Replacing `UserRole` with `SpaceRole`. Rejected because it requires migrating the existing `role_permissions` table and rewriting all group-based access logic — out of scope for this feature.

---

## Decision 3 — SpaceMembership vs RolePermission Coexistence

**Decision**: The new `SpaceMembership` table coexists with the existing `role_permissions` table. For the new roles feature, all member management flows use `SpaceMembership`. Existing group-based access (`RolePermission`) continues to work for backward compatibility.

**Rationale**: `RolePermission` links IDP groups to spaces for systems where group membership is managed externally (e.g., Okta, Azure AD). `SpaceMembership` links individual registered users to spaces for in-app member management. The spec explicitly targets registered users (FR-003: "invite registered users"). Both mechanisms are additive.

**In access checks**: `SpaceMembership` role is checked first. If present, it governs. This means direct membership overrides group-based access when both exist for the same user+space.

**Alternatives considered**: Replace `RolePermission` entirely. Rejected — IDP group access is used in existing features and removing it is out of scope.

---

## Decision 4 — Frontend Route for Members Panel

**Decision**: Members management panel lives at `/spaces/[id]/members` (a new Next.js dynamic route). The current user's role is shown in the space header/nav as a badge.

**Rationale**: The spec (SC-006) requires users to identify their role in "at most 2 navigation steps from the space home." Placing the members panel under the space route satisfies this. Existing web routes follow the `/spaces/[id]/*` pattern implied by the `apps/web/app/` structure.

**Alternatives considered**: Adding members as a tab on the existing space settings page. Deferred — no dedicated space settings page currently exists; adding a dedicated route is cleaner.

---

## Decision 5 — Last-Admin Guard Location

**Decision**: The last-admin guard lives in the **domain service** (`MembershipService`), not in the router or repository. `SpaceMembershipRepository` exposes `count_admins(space_id) → int` to support the check.

**Rationale**: FR-007 is a business rule ("prevent a space from having zero Admins"). Business rules belong in the domain layer per Constitution Principle I. The service checks `count_admins` before executing a demotion or removal and raises a domain exception if it would leave the space admin-less.

---

## Decision 6 — Audit Log for Role Events

**Decision**: Reuse the existing `AuditRecord` entity and `AuditRepository`. No new audit table needed.

**Rationale**: `AuditRecord` is already generic (`entity_type / entity_id / action / metadata`). Role change events are recorded as:
- `action`: `"member_invited"`, `"role_changed"`, `"member_removed"`, `"platform_role_changed"`
- `entity_type`: `"space_membership"` or `"user"`
- `metadata`: `{space_id, user_id, previous_role, new_role}` (where applicable)

The constitution (Security Requirements) mandates audit logging for every state-changing action. This satisfies FR-008.
