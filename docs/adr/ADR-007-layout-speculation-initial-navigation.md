# ADR-007: No Layout Speculation During Initial Navigation

**Status:** Accepted
**Date:** 2026-05-13
**Edition Scope:** Both (CE and SaaS)

---

## Context

During the 2026-04-21 demo go-live, `frontend/src/App.vue` contained a
computed property that resolved the current layout component from the active
route's `meta.layout` field. When the router had not yet resolved the initial
navigation (i.e., `route.name` was `undefined` or `null`), the computed
property fell back to `DashboardLayout` as a default. This is "layout
speculation": guessing a layout before the route is known.

The consequence was visible: on a fresh page load, the application briefly
mounted `DashboardLayout` (which triggers its own data fetches and side
effects) before the navigation guard resolved the actual route. On the demo
landing page, this produced a flash of authenticated-UI chrome and fired
API calls that assumed a session existed. In some combinations with the
401-interceptor bug (see ADR-006), this caused the page to redirect to
`/login` before the router had determined the intended destination.

The fix applied in commit `f16765adb` added a `!route.name` guard: when the
route is not yet resolved, `App.vue` renders a neutral fallback (e.g., a
blank `<div>` or a minimal loading state) rather than speculating a layout.

---

## Decision

**Layout resolver computed properties in `App.vue` (or any top-level layout
switcher) MUST return a neutral, side-effect-free component when
`route.name` is `undefined` or falsy. Falling back to a feature layout
(DashboardLayout, AppLayout, or any layout that triggers data fetches or
renders authenticated chrome) before the route is resolved is banned.**

Required pattern:

```js
// REQUIRED: neutral fallback while route is unresolved
const layout = computed(() => {
  if (!route.name) return 'div'  // or a dedicated BlankLayout
  return route.meta?.layout ?? DefaultLayout
})
```

Anti-pattern (banned):

```js
// BANNED: speculates DashboardLayout before route is known
const layout = computed(() => {
  return route.meta?.layout ?? DashboardLayout  // fires on route.name === undefined
})
```

An ESLint rule (`no-speculative-layout-fallback`) flags layout resolver
expressions where the fallback (the right-hand side of a `??` or `:` ternary
operator) resolves to a name containing `Layout` or `App` (case-insensitive)
without a preceding `route.name` guard. The rule operates at `error` level.

---

## Rationale

A layout that triggers data fetches or renders authenticated chrome is not
a neutral component. Mounting it speculatively — before the router has
decided which route the user is on — turns a timing artifact into visible
side effects and potential redirect loops. The requirement to guard on
`route.name` is minimal and unambiguous; it costs one conditional.

The alternative (making all layouts side-effect-free) was considered but
rejected. Layout components legitimately need to kick off data prefetches and
establish WebSocket connections for the authenticated experience; removing
that behavior would require a separate initialization layer. The guard
approach is targeted and has no performance cost: the neutral fallback renders
for one tick before the navigation guard resolves.

---

## Consequences

**Positive:**
- Layout speculation is detected at lint time; it cannot be re-introduced
  silently.
- The neutral fallback during route resolution eliminates the flash of
  authenticated chrome on routes that should render anonymously.
- Side effects (API calls, WebSocket connections) tied to layout mount only
  fire after the router has confirmed the destination route, making their
  preconditions reliable.

**Negative:**
- Layout components that are genuinely side-effect-free could use them as
  default fallbacks safely, but the lint rule applies uniformly (it matches
  on name pattern, not on actual side-effect analysis). Such components
  would require a suppression comment.
- The one-tick blank state before layout resolution may be perceptible on
  very slow devices. A skeleton loading state is recommended for perceived
  performance but is not mandated here.

---

## References

- ESLint rule: `frontend/eslint-rules/rules/no-speculative-layout-fallback.cjs`
- ESLint rules commit (rule implementation): `2eb43e7db`
- Root-cause fix: `f16765adb` (`fix(frontend): unblock demo go-live --
  6 chained routing/loading bugs`, 2026-04-21), `App.vue` changes
- Related ADR (interceptor side effects on unresolved route):
  `docs/adr/ADR-006-axios-interceptors-route-meta-aware.md`
- IMP-0013 quality sweep audit: `198b2e6d9`
