# API Contract: Space Members (024)

Base path: `/spaces/{space_id}/members`  
Auth: All endpoints require a valid JWT (`Authorization: Bearer <token>`).

---

## Space Member Endpoints

### POST `/spaces/{space_id}/members`
Invite a registered user to a space with a role.

**Authorization**: Caller must be space ADMIN or Global Admin.

**Request body**:
```json
{
  "user_id": "uuid",
  "role": "viewer" | "editor" | "admin"
}
```

**Response 201**:
```json
{
  "membership": {
    "id": "uuid",
    "space_id": "uuid",
    "user_id": "uuid",
    "role": "editor",
    "invited_by_user_id": "uuid",
    "created_at": "2026-06-21T12:00:00Z",
    "updated_at": "2026-06-21T12:00:00Z"
  }
}
```

**Errors**:
- `400 Bad Request` — user is already a member of this space
- `403 Forbidden` — caller lacks space ADMIN privileges
- `404 Not Found` — `user_id` does not exist

---

### GET `/spaces/{space_id}/members`
List all members of a space with their roles.

**Authorization**: Any member of the space, or Global Admin.

**Response 200**:
```json
{
  "members": [
    {
      "id": "uuid",
      "space_id": "uuid",
      "user_id": "uuid",
      "display_name": "Alice Santos",
      "email": "alice@example.com",
      "role": "admin",
      "invited_by_user_id": "uuid",
      "created_at": "2026-06-21T12:00:00Z"
    }
  ]
}
```

**Errors**:
- `403 Forbidden` — caller is not a member and not a Global Admin

---

### GET `/spaces/{space_id}/members/me`
Get the calling user's own role in this space.

**Authorization**: Any authenticated user (non-members receive 404).

**Response 200**:
```json
{
  "membership": {
    "space_id": "uuid",
    "user_id": "uuid",
    "role": "viewer",
    "created_at": "2026-06-21T12:00:00Z"
  }
}
```

**Errors**:
- `404 Not Found` — caller is not a member of this space

---

### PUT `/spaces/{space_id}/members/{user_id}`
Change a member's role.

**Authorization**: Caller must be space ADMIN or Global Admin.

**Request body**:
```json
{
  "role": "viewer" | "editor" | "admin"
}
```

**Response 200**:
```json
{
  "membership": {
    "id": "uuid",
    "space_id": "uuid",
    "user_id": "uuid",
    "role": "editor",
    "updated_at": "2026-06-21T13:00:00Z"
  }
}
```

**Errors**:
- `403 Forbidden` — caller lacks space ADMIN privileges
- `404 Not Found` — target user is not a member of this space
- `409 Conflict` — demotion would leave the space with zero Admins (last-admin guard)

---

### DELETE `/spaces/{space_id}/members/{user_id}`
Remove a member from the space.

**Authorization**: Caller must be space ADMIN or Global Admin.

**Response 204** — No content.

**Errors**:
- `403 Forbidden` — caller lacks space ADMIN privileges
- `404 Not Found` — target user is not a member of this space
- `409 Conflict` — removal would leave the space with zero Admins

---

## Platform Admin Endpoints

### PUT `/users/{user_id}/platform-role`
Promote or demote a user's Global Admin status.

**Authorization**: Global Admin only.

**Request body**:
```json
{
  "is_admin": true | false
}
```

**Response 200**:
```json
{
  "user": {
    "id": "uuid",
    "display_name": "Bob Lima",
    "email": "bob@example.com",
    "is_admin": true
  }
}
```

**Errors**:
- `403 Forbidden` — caller is not a Global Admin
- `404 Not Found` — user does not exist

---

## Error Response Shape

All errors follow the existing FastAPI convention:
```json
{
  "detail": "Human-readable error message"
}
```
