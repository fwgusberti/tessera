# Quickstart & Validation Guide: JWT Authentication

**Feature**: 004-jwt-auth  
**Date**: 2026-06-15

## Prerequisites

- Docker Compose stack running (`make dev` or `docker compose up`)
- API reachable at `http://localhost:8000`
- `curl` and `jq` available in your shell
- Database migration applied (see tasks.md — migration task must run first)

## End-to-End Validation Scenarios

### Scenario 1: Register a local user

```bash
curl -s -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"S3cur3P@ss","display_name":"Alice"}' \
  | jq .
```

**Expected**: `201` with a `user` object containing `id`, `email`, `display_name`.

---

### Scenario 2: Login and receive JWT tokens

```bash
TOKENS=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"S3cur3P@ss"}')

echo $TOKENS | jq .

ACCESS=$(echo $TOKENS | jq -r .access_token)
REFRESH=$(echo $TOKENS | jq -r .refresh_token)
```

**Expected**: `200` with `access_token`, `refresh_token`, `token_type: "bearer"`, `expires_in: 900`.

---

### Scenario 3: Access a protected endpoint with the JWT

```bash
curl -s http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $ACCESS" \
  | jq .
```

**Expected**: `200` with space list (may be empty but not a 401).

---

### Scenario 4: Reject a request without credentials

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/v1/spaces
```

**Expected**: `401`.

---

### Scenario 5: Refresh access token

```bash
NEW_TOKENS=$(curl -s -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}")

echo $NEW_TOKENS | jq .
NEW_ACCESS=$(echo $NEW_TOKENS | jq -r .access_token)
NEW_REFRESH=$(echo $NEW_TOKENS | jq -r .refresh_token)
```

**Expected**: `200` with new `access_token` and new `refresh_token`.

---

### Scenario 6: Old refresh token is invalidated after rotation

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"
```

**Expected**: `401` — old token already consumed.

---

### Scenario 7: Logout invalidates refresh token

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/auth/logout \
  -H "Authorization: Bearer $NEW_ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$NEW_REFRESH\"}"
```

**Expected**: `204`.

```bash
# Attempt refresh with invalidated token
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$NEW_REFRESH\"}"
```

**Expected**: `401`.

---

### Scenario 8: Expired access token is rejected

Simulate by setting `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=0` in environment, logging in, and immediately calling a protected endpoint.

**Expected**: `401` with `code: "token_expired"`.

---

### Scenario 9: Wrong password returns non-revealing error

```bash
curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"wrongpassword"}' \
  | jq .error.code
```

**Expected**: `"invalid_credentials"` (same message for wrong email too).

---

### Scenario 10: Audit log entries exist

```bash
curl -s http://localhost:8000/v1/admin/audit?entity_type=user \
  -H "Authorization: Bearer $NEW_ACCESS" \
  | jq '.records[] | select(.action | startswith("auth."))'
```

**Expected**: Entries for `auth.register`, `auth.login.success`, `auth.token.refresh`, `auth.logout`.

## References

- API contracts: [contracts/auth-api.md](contracts/auth-api.md)
- Data model: [data-model.md](data-model.md)
- Tasks: [tasks.md](tasks.md)
