# Frontend Contracts: Password Change and Recovery Flow

All pages follow the existing UI design system: `slate-*` neutrals, `indigo-600` primary interactive, `red-*` error states, Geist Sans typography, minimal borders, generous whitespace.

---

## Page: /forgot-password

**File**: `apps/web/app/forgot-password/page.tsx`

**Access**: Public (no auth required)

### Layout

Single-column card, centred (mirrors `/login` layout).

### Elements

| Element | Behaviour |
|---------|-----------|
| Heading | "Reset your password" |
| Email input (`type="email"`) | Required field; inline error if empty |
| Submit button | "Send reset link" → disabled while submitting |
| Success state | Replace form with: "If that email is registered, you will receive a reset link shortly." |
| Back to sign in link | `/login` |

### State machine

```
idle → submitting → success
                 ↘ error (network / server 5xx)
```

Success message is always shown after submission (no error state for 200 responses, per non-enumeration requirement).

---

## Page: /reset-password

**File**: `apps/web/app/reset-password/page.tsx`

**Access**: Public (no auth required); reads `?token=` query param

### Elements

| Element | Behaviour |
|---------|-----------|
| Heading | "Set a new password" |
| New password input (`type="password"`) | Required; inline strength hint; min 8 chars |
| Confirm password input (`type="password"`) | Required; inline "Passwords do not match" error on blur |
| Submit button | "Update password" → disabled while submitting |
| Success redirect | On 204 response → navigate to `/login?reset=success` |
| Expired / invalid token error | Full-page message: "This reset link has expired or has already been used." + "Request a new link" → `/forgot-password` |
| Network / 5xx error | Inline form error: "Something went wrong. Please try again." |

### Token validation

The `?token=` param is read from the URL. If absent on page load, immediately show the expired/invalid state (no API call). The 400 response from the API (`invalid_or_expired_token`) also renders the expired/invalid full-page state.

### Password strength inline feedback

Client-side rules (mirrors server-side FR-004):
- Length < 8 → "Password must be at least 8 characters"
- Known weak password → "Please choose a less common password"
- Shown on input blur (not on keystroke to avoid noise)

---

## Page: /account

**File**: `apps/web/app/account/page.tsx`

**Access**: Authenticated (redirects to `/login?redirect=/account` if not logged in)

### Layout

Single-column page with a "Security" section card containing the password change form.

### Elements

| Element | Behaviour |
|---------|-----------|
| Current password input | Required; inline error for wrong password |
| New password input | Required; inline strength feedback (same rules as `/reset-password`) |
| Confirm password input | Required; inline "Passwords do not match" error on blur |
| Submit button | "Update password" → disabled while submitting |
| Success banner | "Password updated successfully." (auto-dismisses after 5 s) |
| Current password wrong (401) | Inline error: "Current password is incorrect." |
| Mismatch (client-side) | Inline error before submit: "Passwords do not match." |
| Network / 5xx | Inline error: "Something went wrong. Please try again." |

### Token rotation

On 200 response, the new `access_token` and `refresh_token` in the response body must be written to the auth store (same mechanism as `POST /v1/auth/refresh`) so the session continues without interruption.

---

## Login page modification: /login

**File**: `apps/web/app/login/page.tsx` (existing, minor addition)

Add "Forgot password?" link below the password field, styled like the existing "Create account" link:

```
Forgot password?   →   /forgot-password
```

---

## Login page: success message after reset

When `/login` is loaded with `?reset=success` in the query string, display a dismissible banner:

```
"Your password has been reset. Please sign in with your new password."
```

Rendered above the form, using `slate-100` background + `slate-700` text (neutral info style, not red/green).

---

## API client additions

File: `apps/web/lib/auth.ts` (or a new `apps/web/lib/password.ts`)

```typescript
export async function changePassword(params: {
  currentPassword: string;
  newPassword: string;
  confirmNewPassword: string;
  refreshToken: string;
}): Promise<{ access_token: string; refresh_token: string }> { ... }

export async function forgotPassword(email: string): Promise<void> { ... }

export async function resetPassword(params: {
  token: string;
  newPassword: string;
  confirmNewPassword: string;
}): Promise<void> { ... }
```
