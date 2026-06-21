# Quickstart Validation Guide: Password Change and Recovery Flow

This guide documents runnable scenarios to confirm the feature works end-to-end. Run these after implementation is complete.

## Prerequisites

1. Local dev stack running: `make dev` (API on `:8000`, web on `:3000`, PostgreSQL, Redis)
2. A registered user exists. Create one if needed:
   ```bash
   curl -s -X POST http://localhost:8000/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"ValidPass1!","display_name":"Test User"}' | jq .
   ```
3. `mail_suppress_send = false` in `.env` (or use a local SMTP server like MailHog on `:1025`/`:8025`)

---

## Scenario 1 — Password Change (US1)

### Setup
```bash
# Login to get tokens
TOKENS=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"ValidPass1!"}')

ACCESS=$(echo $TOKENS | jq -r .access_token)
REFRESH=$(echo $TOKENS | jq -r .refresh_token)
```

### AC1 — Successful change
```bash
curl -s -X POST http://localhost:8000/v1/auth/change-password \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"ValidPass1!\",\"new_password\":\"NewPass99!\",\"confirm_new_password\":\"NewPass99!\",\"refresh_token\":\"$REFRESH\"}" | jq .
```
**Expected**: HTTP 200 with `access_token` and `refresh_token` fields.

Verify new password works:
```bash
curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"NewPass99!"}' | jq .status_code
```
**Expected**: HTTP 200.

Old password fails:
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"ValidPass1!"}'
```
**Expected**: `401`.

### AC2 — Wrong current password
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/auth/change-password \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"WrongPass!\",\"new_password\":\"NewPass99!\",\"confirm_new_password\":\"NewPass99!\",\"refresh_token\":\"$REFRESH\"}"
```
**Expected**: `401`.

### AC3 — Passwords do not match
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/auth/change-password \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"ValidPass1!\",\"new_password\":\"NewPass99!\",\"confirm_new_password\":\"DifferentPass!\",\"refresh_token\":\"$REFRESH\"}"
```
**Expected**: `400`.

### AC4 — Other sessions invalidated
Open a second session (get a second refresh token), perform a change, then try to use the second refresh token:
```bash
TOKENS2=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"ValidPass1!"}')
REFRESH2=$(echo $TOKENS2 | jq -r .refresh_token)

# Change password
curl -s -X POST http://localhost:8000/v1/auth/change-password \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"ValidPass1!\",\"new_password\":\"NewPass99!\",\"confirm_new_password\":\"NewPass99!\",\"refresh_token\":\"$REFRESH\"}" | jq .

# Second session's refresh token should be invalid now
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH2\"}"
```
**Expected**: `401` for the second session's refresh.

### AC5 — Audit log
```bash
# Requires admin token; check audit via DB or admin endpoint
psql "$DATABASE_URL" -c "SELECT action, actor_type, occurred_at FROM audit_records WHERE action = 'auth.password.change' ORDER BY occurred_at DESC LIMIT 1;"
```
**Expected**: One row with `action = 'auth.password.change'`.

---

## Scenario 2 — Password Reset Request (US2)

### AC1 — Always same response
```bash
# Registered email
curl -s -X POST http://localhost:8000/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}' | jq .

# Unregistered email
curl -s -X POST http://localhost:8000/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"nobody@nowhere.invalid"}' | jq .
```
**Expected**: Both return HTTP 200 with identical bodies.

### AC2 — Email received within 60 s
Submit request for registered email, then check MailHog at `http://localhost:8025`. Verify email arrives containing a link matching `http://localhost:3000/reset-password?token=`.

### AC3 — Only latest link valid
```bash
curl -s -X POST http://localhost:8000/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Issue second request (invalidates first token)
curl -s -X POST http://localhost:8000/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```
Check DB — first token should have `consumed_at` set:
```sql
SELECT token_hash, consumed_at FROM password_reset_tokens WHERE user_id = '<user_uuid>' ORDER BY created_at DESC;
```
**Expected**: First row (older) has `consumed_at` set; second row has `consumed_at = NULL`.

### AC4 — Rate limiting
```bash
for i in $(seq 1 7); do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" \
    -X POST http://localhost:8000/v1/auth/forgot-password \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com"}'
done
```
**Expected**: All 7 requests return `200`. Check MailHog — only the first 5 should have generated emails; requests 6 and 7 should produce no new emails.

---

## Scenario 3 — Reset Link Consumption (US3)

### Setup
```bash
# Get the raw token from MailHog or directly from DB
TOKEN=$(psql "$DATABASE_URL" -tA -c "
  SELECT t.token_hash FROM password_reset_tokens t
  JOIN users u ON u.id = t.user_id
  WHERE u.email = 'test@example.com' AND t.consumed_at IS NULL
  ORDER BY t.created_at DESC LIMIT 1;
")
```
Note: the raw token is in the email URL, not the DB (DB stores the hash). Extract it from the MailHog email or from the reset URL.

### AC1 — Valid token sets new password
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"<raw_token_from_email>\",\"new_password\":\"ResetPass1!\",\"confirm_new_password\":\"ResetPass1!\"}"
```
**Expected**: `204`.

Verify login with new password:
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"ResetPass1!"}'
```
**Expected**: `200`.

### AC2 / AC3 — Expired or already-consumed token
Use the same token again or a fabricated one:
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<same_token_again>","new_password":"AnotherPass1!","confirm_new_password":"AnotherPass1!"}'
```
**Expected**: `400` with `invalid_or_expired_token`.

Check browser: navigate to `http://localhost:3000/reset-password?token=<expired_token>`. **Expected**: Expired-link message with "Request a new link" button.

### AC4 — Audit log
```bash
psql "$DATABASE_URL" -c "SELECT action, occurred_at FROM audit_records WHERE action = 'auth.password.reset_completed' ORDER BY occurred_at DESC LIMIT 1;"
```
**Expected**: One row with `action = 'auth.password.reset_completed'`.

---

## Browser / UI validation

| Page | URL | Check |
|------|-----|-------|
| Forgot password | `http://localhost:3000/forgot-password` | Form submits; success message always shown |
| Reset password | `http://localhost:3000/reset-password?token=<valid>` | Form submits; redirects to `/login?reset=success` |
| Reset password (bad token) | `http://localhost:3000/reset-password?token=invalid` | Expired-link page shown |
| Account settings | `http://localhost:3000/account` | Requires login; password change form works |
| Login (after reset) | `http://localhost:3000/login?reset=success` | Banner: "Your password has been reset…" |
| Login page | `http://localhost:3000/login` | "Forgot password?" link visible and navigates to `/forgot-password` |
