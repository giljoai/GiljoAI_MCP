# ADR-002: Setup-Driven Mode Source of Truth

**Status:** Accepted
**Date:** 2026-04-28
**Edition Scope:** Both (CE and SaaS)

---

## Context

The frontend derives the current edition mode (`ce`, `demo`, `saas`) from two
sources:

1. **`setupService.checkEnhancedStatus().mode`** — populated from
   `/api/setup/status` by `setupService` (a service singleton, not a Pinia
   store). Available after the async call resolves; cached with a 2 s TTL.
2. **`configService.getGiljoMode()`** — returns `config.giljo_mode` from the
   cached frontend config. Defaults to `'ce'` before `fetchConfig` resolves.

On 2026-04-21 (demo go-live), the router navigation guard read
`configService.getGiljoMode()` on first paint. Because `fetchConfig` had not
yet resolved, the call returned `'ce'` regardless of actual mode. The guard
routed demo users into the CE code path (`/welcome`), preventing
`/demo-landing` from ever rendering. This was a time-of-use race: by the
time the page was interactive, the config had loaded correctly, but the
initial navigation had already committed to the wrong branch.

A parallel issue was discovered in the same commit: several files used
`@vite-ignore` comments to perform dynamic `import()` calls at runtime.
Vite does not bundle these imports — the referenced `.vue`/`.js` files were
absent from `dist/`. The browser fetched them via the SPA fallback route,
received `text/html`, and refused to execute the response as a JS module.
SaaS routes and components silently failed to load.

---

## Decision

### Rule 1: Router guards and first-paint code MUST read mode from `setupService`

In navigation guards, layout guards, and any code that runs before the first
user interaction, mode MUST be read from `setupService.checkEnhancedStatus()`.
`setupService` hits `/api/setup/status` and caches the result with a short TTL,
making it safe to call once at guard entry:

```js
// REQUIRED in router guards and first-paint code
// (setupService is injected into the guard factory — see authGuard.js)
let setupState = null
try {
  setupState = await setupService.checkEnhancedStatus()
} catch {
  // Network error -- fall through to configService fallback below
}

const mode = (() => {
  if (setupState?.mode) return setupState.mode
  try { return configService.getGiljoMode() } catch { return 'ce' }
})()
```

`configService.getGiljoMode()` is legitimate as a fallback when
`setupService` fails (network error at startup), and for components rendered
well after initial navigation (settings panels, admin views). It MUST NOT be
used as the **primary** mode source in `router.beforeEach` guards or any code
on the critical navigation path.

### Rule 2: `@vite-ignore` dynamic imports are BANNED

`@vite-ignore` bypasses Vite's build-time bundling. Use `import.meta.glob`
instead, which bundles all matched files at build time and resolves to an
empty object (silent skip) when no files match — safe for CE builds that
have no `saas/` directory.

```js
// BANNED
const module = await import(/* @vite-ignore */ `@/saas/routes.js`)

// REQUIRED
const saasModules = import.meta.glob('@/saas/routes.js', { eager: false })
for (const path of Object.values(saasModules)) {
  const mod = await path()
  // use mod
}
```

`import.meta.glob` is CE-export safe: when the glob matches no files (CE
repo has no `saas/`), it returns `{}` and the loop body never executes.

### Rule 3 (defense-in-depth): CE fresh-install guard requires two conditions

The CE `/welcome` guard MUST check both `is_fresh_install` AND
`total_users_count > 0` before deciding the install is non-fresh. A single
flag check produced contradictory log output ("users exist (total: 0)") and
routed incorrectly when the flag and count disagreed.

---

## Consequences

**Positive:**
- First-paint routing is deterministic: `setupState.mode` is set from the
  same `/api/setup/status` call that the setup wizard depends on.
- `import.meta.glob` files are in `dist/` and load synchronously from the
  bundle; no runtime 404s or content-type mismatches.
- CE export correctness: glob on `@/saas/**` resolves to empty in the
  exported repo.

**Negative:**
- `setupState` must be populated before any guard that reads `.mode` runs.
  The `setupService.checkEnhancedStatus()` call is already part of the app
  bootstrap; this is not a new requirement, just an explicit ordering constraint.

---

## Existing Regression Tests

`frontend/tests/saas/demoLandingRouteGuard.spec.js` — 4 tests covering
Rule 1 (the `setupState.mode` race scenario and the defense-in-depth gate).
Rule 2 (`@vite-ignore` ban) is enforced by code review; no automated lint
rule exists yet.

---

## References

- Root-cause commit: `92ddabe6b` (`fix(frontend): unblock demo go-live -- 6 chained routing/loading bugs`, 2026-04-21)
- Mode resolver (canonical call site): `frontend/src/router/authGuard.js` lines 28-38
- Setup service: `frontend/src/services/setupService.js`
- Regression tests: `frontend/tests/saas/demoLandingRouteGuard.spec.js`
