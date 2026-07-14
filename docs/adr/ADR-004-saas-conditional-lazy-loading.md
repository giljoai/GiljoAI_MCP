# ADR-004: SaaS Conditional Lazy Loading via import.meta.glob

**Status:** Accepted
**Date:** 2026-05-13
**Edition Scope:** Both (CE and SaaS)

---

## Context

ADR-002 (Rule 2) established that `@vite-ignore` dynamic imports are banned
and that `import.meta.glob` must be used instead for edition-conditional
module loading. During the 2026-04-21 demo go-live, SaaS routes and
components silently failed to load because Vite did not bundle the dynamically
imported files; the browser fetched them via the SPA fallback route, received
`text/html`, and refused to execute the response as a JavaScript module.

The IMP-0013 quality sweep (audit `198b2e6d9`, 2026-05-13) confirmed that no
live `@vite-ignore` occurrences remain in production code. All references are
comment strings documenting prior removal. The sweep also verified that
`import.meta.glob` resolves to `{}` in CE builds (no `saas/` directory) so
the glob pattern is CE-export safe.

The decision to encode this as an ESLint rule (rather than relying on
documentation and code review) was made as part of IMP-0013 Phase 4. An
automated gate is needed because the `@vite-ignore` pattern is a natural
reflex for developers who want to silence Vite's "dynamic import cannot be
analyzed" warning without understanding the bundling consequence.

---

## Decision

**An ESLint rule (`no-vite-ignore-saas-import`) MUST flag any `import()`
call that contains a `/* @vite-ignore */` comment.**

When a SaaS or edition-conditional module must be loaded at runtime, the
required pattern is `import.meta.glob`:

```js
// BANNED
const mod = await import(/* @vite-ignore */ '@/saas/routes.js')

// REQUIRED
const saasModules = import.meta.glob('@/saas/routes.js', { eager: false })
for (const loader of Object.values(saasModules)) {
  const mod = await loader()
  // use mod
}
```

`import.meta.glob` satisfies three requirements simultaneously:
1. Vite bundles all matched files at build time — no runtime 404s.
2. When the glob matches no files (CE repo has no `saas/` directory), it
   returns `{}` and the loop body never executes — CE-export safe.
3. The dynamic import warning is eliminated without silencing Vite's analysis.

The rule operates at `error` level. No per-file allowlist is defined; there
is no legitimate use of `/* @vite-ignore */` in this codebase.

---

## Rationale

The root cause of the 2026-04-21 SaaS loading failure was not the use of
dynamic imports per se, but the silencing of Vite's bundler warning via
`@vite-ignore`. Vite's warning is the correct signal that the import is
unbundled; suppressing the warning while leaving the underlying behavior
unchanged is a silent correctness hole. The lint rule converts that silent
hole into a CI-blocking error.

`import.meta.glob` was chosen as the required alternative because it is the
only Vite-native mechanism that provides build-time bundling of conditionally
loaded modules. Other alternatives (pre-importing into a barrel, conditional
top-level imports) are either incompatible with edition isolation or require
restructuring that exceeds the scope of the fix.

---

## Consequences

**Positive:**
- Any future `@vite-ignore` comment in an import call fails `npm run lint`
  before the code reaches CI.
- Existing `@vite-ignore` references that are comments-only (documentation of
  prior removal) are not flagged, because they appear inside comment strings
  rather than inside `import()` call nodes. The rule targets AST nodes, not
  raw text.
- The glob pattern is safe in CE builds: `import.meta.glob('@/saas/**', ...)`
  returns `{}` in the exported public repo.

**Negative:**
- Developers encountering Vite's "dynamic import cannot be analyzed" warning
  for the first time may not immediately understand why `@vite-ignore` is
  prohibited. The lint error message includes a link to this ADR.
- `import.meta.glob` patterns must be string literals; they cannot be
  constructed dynamically. This is a Vite constraint, not a rule constraint.
  Dynamic glob needs are uncommon in this codebase.

---

## References

- ADR-002: `docs/adr/ADR-002-setup-driven-mode-source-of-truth.md` (original
  ban; Rule 2 of that ADR; this ADR adds lint enforcement only)
- ESLint rule: `frontend/eslint-rules/rules/no-vite-ignore-saas-import.cjs`
- ESLint rules commit (rule implementation): `2eb43e7db`
- Root-cause fix (SaaS loading): `f16765adb` (`fix(frontend): unblock demo
  go-live -- 6 chained routing/loading bugs`, 2026-04-21)
- IMP-0013 quality sweep audit: `198b2e6d9`
