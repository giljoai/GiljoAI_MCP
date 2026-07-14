# ADR-006: axios Interceptors Must Be Route-Meta-Aware

**Status:** Accepted
**Date:** 2026-05-13
**Edition Scope:** Both (CE and SaaS)

---

## Context

The frontend's axios instance (`frontend/src/services/api.js`) registers a
response interceptor that catches HTTP 401 responses and redirects to
`/login`. During the 2026-04-21 demo go-live, this interceptor fired on
requests that were intentionally unauthenticated — specifically, requests made
from the demo landing page and the registration flow, which are designed to
reach the backend before a session exists.

The interceptor had no mechanism to distinguish an expected 401 (a probe or
anonymous endpoint) from an unexpected 401 (an expired session on a protected
route). Every 401 triggered a redirect to `/login`, even from pages that
explicitly should not require authentication. This produced a redirect loop
on the demo landing page and prevented anonymous users from ever registering.

The fix applied in commit `f16765adb` was later strengthened in
`6a39513f4`: the interceptor now checks `error.config?.meta?.requiresAuth
=== false` before redirecting. Call sites that opt out of the redirect pass
`{ meta: { requiresAuth: false } }` in their axios request config.

---

## Decision

**The axios response interceptor in `frontend/src/services/api.js` MUST
check `error.config?.meta?.requiresAuth === false` before redirecting to
`/login` on a 401 response. Interceptors that redirect unconditionally on
any 401 are banned.**

The required interceptor pattern:

```js
axiosInstance.interceptors.response.use(
  response => response,
  error => {
    if (
      error.response?.status === 401 &&
      error.config?.meta?.requiresAuth !== false  // opt-out check
    ) {
      router.push('/login')
    }
    return Promise.reject(error)
  }
)
```

Call sites that make requests from unauthenticated contexts opt out by
including the meta flag in the request config:

```js
// Call site opt-out — interceptor will NOT redirect on 401
api.get('/api/v1/some-anonymous-endpoint', {
  meta: { requiresAuth: false }
})
```

The default behavior (no `meta` key) remains redirect-on-401, preserving
backward compatibility for all existing authenticated call sites.

An ESLint rule (`axios-interceptor-route-meta-aware`) flags response
interceptors that call `router.push('/login')` (or equivalent navigation)
without an `error.config?.meta?.requiresAuth` guard. The rule operates at
`error` level.

---

## Rationale

An unconditional 401 redirect is correct for the majority of API calls where
a session is expected, but it is wrong for calls from unauthenticated routes.
The opt-out pattern was chosen over an opt-in pattern (requiring callers to
explicitly mark every authenticated call) because:

1. Backward compatibility: no existing call sites needed to be modified when
   the opt-out was introduced. Only new anonymous-context callers need the
   flag.
2. Safety default: failing to add the flag on a protected route still
   triggers the redirect, which is the correct behavior. Forgetting the flag
   on an anonymous route produces a visible redirect; forgetting the opt-in
   flag on a protected route would silently allow unauthenticated access.

The ESLint rule encodes the requirement that any new interceptor must include
the guard. This prevents future developers from adding a second axios instance
with a naive interceptor that re-introduces the same bug.

---

## Consequences

**Positive:**
- Anonymous routes (demo landing, registration, public OAuth endpoints) can
  now make 401-eligible requests without triggering a redirect loop.
- The opt-out pattern is self-documenting: `{ meta: { requiresAuth: false } }`
  at the call site signals intent explicitly.
- `useTrialGuard.js` (SaaS) is annotated with a comment documenting the
  implicit registration-order contract with the interceptor (commit
  `6a39513f4`), making the dependency visible without tight coupling.

**Negative:**
- Call sites that make probing requests from anonymous contexts must remember
  to set the flag. A missing flag produces a redirect to `/login` (incorrect
  but visible), not a silent failure; the bug surface is small.
- The flag is not validated by TypeScript (the codebase uses plain JS). A
  typo in the key name (`requireAuth` vs `requiresAuth`) would silently
  defeat the opt-out. A runtime guard in the interceptor for the common
  misspelling is recommended but not mandated here.

---

## References

- ESLint rule: `frontend/eslint-rules/rules/axios-interceptor-route-meta-aware.cjs`
- ESLint rules commit (rule implementation): `2eb43e7db`
- Original interceptor fix: `f16765adb` (`fix(frontend): unblock demo go-live
  -- 6 chained routing/loading bugs`, 2026-04-21), item 4 in commit message
- Defensive guard addition: `6a39513f4` (`chore(fe): IMP-0013 Tranche-C
  resolutions`, item #9)
- `useTrialGuard.js` registration-order comment: `6a39513f4` (item #10)
- IMP-0013 quality sweep audit: `198b2e6d9`
