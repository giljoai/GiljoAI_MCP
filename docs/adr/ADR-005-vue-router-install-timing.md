# ADR-005: Vue Router 4 Install Timing for Dynamic Routes

**Status:** Accepted
**Date:** 2026-05-13
**Edition Scope:** Both (CE and SaaS)

---

## Context

During the 2026-04-21 demo go-live, the SaaS edition's dynamically registered
routes were unreachable on first navigation. The root cause was the order of
operations in `frontend/src/main.js`: the Vue application was mounting the
router plugin via `app.use(router)` before calling `router.addRoute()` to
register the SaaS-specific routes.

Vue Router 4's `app.use(router)` call triggers the initial navigation
synchronously. Any `addRoute()` calls that occur after `app.use()` are not
visible to that initial navigation. The SaaS routes were registered too late;
the router had already resolved (and rejected) the initial URL against a
route table that did not yet contain them.

The fix applied in commit `f16765adb` moved all `router.addRoute()` calls
above the `app.use(router)` line. This ensured the full route table — CE
routes plus any edition-specific additions — was in place before the router
performed its first navigation.

---

## Decision

**All `router.addRoute()` calls in `main.js` (or any bootstrap module) MUST
appear before `app.use(router)`.**

The required ordering in `main.js`:

```js
// REQUIRED: add edition-specific routes first
const saasModules = import.meta.glob('@/saas/routes.js', { eager: false })
for (const loader of Object.values(saasModules)) {
  const { default: saasRoutes } = await loader()
  saasRoutes.forEach(route => router.addRoute(route))
}

// THEN install the router — initial navigation sees the full route table
app.use(router)
app.mount('#app')
```

The anti-pattern is `app.use(router)` appearing before any `router.addRoute()`
calls in the same module:

```js
// BANNED: router installed before routes are registered
app.use(router)
router.addRoute({ name: 'SaasFeature', ... })  // too late for initial nav
app.mount('#app')
```

An ESLint rule (`vue-router-install-after-routes`) enforces this ordering by
flagging any `app.use(router)` call that appears before a `router.addRoute()`
call in the same file scope.

The rule operates at `error` level. It applies to any file that contains both
`app.use(router)` and `router.addRoute()`, which in practice is only
`main.js` and any bootstrap entry point that mirrors its structure.

---

## Rationale

Vue Router 4's initial navigation is triggered synchronously by `app.use()`.
This is a documented Vue Router 4 behavior, but it is non-obvious to
developers migrating from Vue Router 3 (where `createRouter` and
`addRoute` have different lifecycle semantics). Without a lint rule, the
anti-pattern is easy to reintroduce during any refactor of `main.js` that
reorders initialization blocks.

The rule was implemented as an AST-level check rather than a comment
convention because the ordering constraint is mechanically checkable. A
comment can be ignored; a lint error cannot.

---

## Consequences

**Positive:**
- The `main.js` initialization sequence is enforced as a CI-blocking
  constraint; the anti-pattern cannot be re-introduced without a lint
  suppression comment that would be visible in code review.
- The rule is scoped to files containing both `app.use(router)` and
  `router.addRoute()`; it does not affect components or stores that call
  `addRoute` for feature-level dynamic routing.

**Negative:**
- The rule fires on any file that happens to contain both patterns in the
  wrong order, not just `main.js`. If a test helper or factory function
  legitimately orders them differently (e.g., to test the error scenario),
  a suppression comment is required.
- The rule checks lexical ordering, not execution ordering. A case where
  `app.use(router)` is textually first but guarded by a condition that
  ensures it runs after `addRoute()` would be flagged incorrectly. No such
  pattern exists in this codebase today.

---

## References

- ESLint rule: `frontend/eslint-rules/rules/vue-router-install-after-routes.cjs`
- ESLint rules commit (rule implementation): `2eb43e7db`
- Root-cause fix: `f16765adb` (`fix(frontend): unblock demo go-live --
  6 chained routing/loading bugs`, 2026-04-21), item 2 in commit message
- Related ADR (SaaS conditional loading): `docs/adr/ADR-004-saas-conditional-lazy-loading.md`
- IMP-0013 quality sweep audit: `198b2e6d9`
