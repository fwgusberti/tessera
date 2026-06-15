# Research: Frontend Login

**Feature**: 005-frontend-login | **Date**: 2026-06-15

## R-001: Token Storage Strategy

- **Decision**: Store `access_token`, `refresh_token`, and `expires_at` (numeric timestamp) in `localStorage`
- **Rationale**: The backend issues tokens in the response body (not as `Set-Cookie` headers), so the client must hold them. `localStorage` is the only option that satisfies all requirements simultaneously: it persists across page refreshes (ruling out in-memory), is accessible from any same-origin tab (ruling out `sessionStorage` for cross-tab logout sync), and doesn't require server-side session management. `sessionStorage` would break FR-008 (session persistence across refresh) and make cross-tab logout coordination impossible (edge case in spec). HttpOnly cookies are ideal for security but require backend support (`Set-Cookie` response header and CORS credentials), which is out of scope for this feature.
- **Alternatives considered**:
  - *In-memory (React state)*: Lost on refresh — violates FR-008.
  - *sessionStorage*: Lost on tab close; cannot coordinate logout across tabs — violates the multiple-tabs edge case.
  - *HttpOnly cookies*: Most secure XSS-resistant option, but requires backend changes (CORS cookie headers, `Set-Cookie` responses) — out of scope per spec Assumptions.
- **Constitution III compliance**: Spec Assumptions explicitly note session tokens are a technical necessity, expire automatically, are not personal data, and do not require a consent dialog.

## R-002: Route Protection Strategy

- **Decision**: Client-side `AuthGuard` component (HOC-style wrapper or hook pattern)
- **Rationale**: Next.js Middleware (`middleware.ts`) executes on the server/edge and cannot access `localStorage`. Any middleware-based guard would require duplicating token storage to cookies, which changes the storage strategy. Client-side guards (a `useEffect` that redirects unauthenticated users) run on mount and are sufficient for this SPA-like app. The 1-second redirect requirement (SC-003) is achievable — the check is synchronous (`localStorage.getItem`) and the redirect fires before the protected content renders.
- **Alternatives considered**:
  - *Next.js Middleware*: Cannot read `localStorage`; would require cookie-based token storage (different strategy, backend changes).
  - *Layout-level server component guard*: Cannot read client-side storage; same constraint as middleware.
- **Implementation**: `AuthGuard` is a `"use client"` component. It reads auth state from `AuthContext`, and if unauthenticated, redirects to `/login?redirect=<current-path>`. It renders `null` (blank flash) until the auth check is complete, then renders `children`.

## R-003: Session Refresh Strategy

- **Decision**: Proactive expiry check before each API request + reactive 401 handling as fallback
- **Rationale**: The proactive check (compare `Date.now()` against `expires_at` minus a 60-second buffer) catches the common case where the access token has expired while the user was idle. The reactive path (intercept the 401 HTTP response, call `/v1/auth/refresh`, replay the original request) handles edge cases where the token expired between the expiry check and the server response. Single-use refresh token rotation (backend behaviour: old refresh token is revoked, new pair issued) means the reactive path must be serialised — a second concurrent 401 must wait for the in-flight refresh rather than issuing a second refresh call.
- **Alternatives considered**:
  - *Only reactive (intercept 401)*: Simpler code path but causes a round-trip on every expired-token request. The user sees a brief delay on every protected page load after idle time.
  - *Background interval refresh*: Refreshes on a timer regardless of activity — wastes refresh tokens and complicates logout (must clear the interval).
- **Implementation**: A `refreshLock` promise in `AuthContext` serialises concurrent refresh attempts. `api.ts` will be updated to: (1) inject `Authorization: Bearer <token>` header from context, (2) call `authContext.refreshIfNeeded()` before each request, (3) on 401, call `authContext.refresh()` once, then retry.

## R-004: Cross-Tab Logout Synchronisation

- **Decision**: `window.addEventListener('storage', ...)` in `AuthContext`
- **Rationale**: When the user logs out in one tab, `localStorage.removeItem('access_token')` fires a `storage` event in all other same-origin tabs. The `AuthContext` in each other tab listens for this event and transitions its state to unauthenticated, which causes the `AuthGuard` in each tab to redirect to `/login`.
- **Alternatives considered**:
  - *BroadcastChannel API*: More explicit but requires all browsers to support it (good support, but adds complexity for the same outcome).
  - *No cross-tab sync*: Other tabs continue working until the next API call returns 401 — acceptable degradation but the spec calls this out as an edge case to handle.

## R-005: Next.js App Router Auth Context Pattern

- **Decision**: `AuthProvider` as a client component wrapping the root `layout.tsx` children; `useAuth()` hook for access
- **Rationale**: React Context cannot be created in Server Components. Since all existing pages are already `"use client"` components and the root layout is a Server Component, the `AuthProvider` must be a separate `"use client"` wrapper placed inside `layout.tsx`. This is the standard Next.js App Router pattern for client-only state like auth.
- **Implementation**: `layout.tsx` imports `AuthProvider` from `"use client"` `lib/auth.tsx` and wraps `{children}` with it. The `nav` logout button also becomes a separate `"use client"` `NavBar` component since it needs to call `useAuth()`.

## R-006: Login Redirect Preservation

- **Decision**: `?redirect=<path>` query parameter on the login page URL
- **Rationale**: Standard pattern for SPA auth flows. When `AuthGuard` redirects unauthenticated users, it appends `?redirect=/original/path`. After successful login, the login page reads this parameter and redirects to it (with validation that it's a relative path to prevent open redirect attacks). If absent, redirect to `/`.
- **Alternatives considered**:
  - *sessionStorage*: Would not survive cross-tab flows (user opens link in a new tab); query param is more reliable.
  - *No redirect preservation*: Violates FR-005 and Acceptance Scenario 1 of User Story 1.
