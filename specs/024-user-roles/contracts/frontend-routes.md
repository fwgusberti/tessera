# Frontend Contract: User Roles (024)

## New Routes

### `/spaces/[id]/members`

Members management panel for a space.

**Access**: Any authenticated user who is a member of the space. Non-members are redirected.

**Behavior by role**:
- **ADMIN / Global Admin**: Full panel — member list, invite form, role-change dropdown, remove button.
- **EDITOR / VIEWER**: Read-only view of the member list, showing names, emails, and roles. No invite/change/remove controls rendered.

**URL params**: `id` — the space UUID.

---

## Modified Components

### `NavBar.tsx`
No structural change. When viewing a space, the NavBar may display the current user's role as a small badge next to the space name (a label like "Admin", "Editor", "Viewer" using `indigo-600` text).

### `SpaceSelector.tsx`
No change required.

---

## New Components

### `SpaceMembersPanel`
Location: `apps/web/components/members/SpaceMembersPanel.tsx`

Displays the full member list and (for ADMINs) the invite/manage controls.

Props: `spaceId: string`

Data fetched from: `GET /spaces/{spaceId}/members`

---

### `InviteMemberForm`
Location: `apps/web/components/members/InviteMemberForm.tsx`

Form to invite a user by `user_id` (or email-lookup) with a role selector.

Calls: `POST /spaces/{spaceId}/members`

Only rendered when caller has ADMIN role.

---

### `RoleBadge`
Location: `apps/web/components/members/RoleBadge.tsx`

Visual badge displaying a SpaceRole.

| Role   | Style                                      |
|--------|--------------------------------------------|
| ADMIN  | `bg-indigo-100 text-indigo-700 rounded`    |
| EDITOR | `bg-slate-100 text-slate-700 rounded`      |
| VIEWER | `bg-slate-50 text-slate-500 rounded`       |

---

## Current User Role Detection

The `GET /spaces/{space_id}/members/me` endpoint is called on space page load to determine the current user's role. The result controls which controls are rendered.
