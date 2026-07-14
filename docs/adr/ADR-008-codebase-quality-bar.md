# ADR-008: Codebase Quality Bar — Thresholds, TODO Age Limits, and ESLint Rule Philosophy

**Status:** Accepted
**Date:** 2026-05-13
**Edition Scope:** Both (CE and SaaS)

---

## Context

The IMP-0013 quality sweep (audit commit `198b2e6d9`, 2026-05-13) performed a
systematic review of orphaned exports, zombie (dead) code, bridge patterns,
stale TODOs, and scattered edition-mode checks across the frontend codebase.
The sweep surfaced 28 pre-existing warnings across these categories, all
treated as technical debt to be queued rather than immediately fixed.

Prior to this project, no automated thresholds or age limits existed for these
categories. Developers had no signal when an export became orphaned, when a
TODO had aged past a reasonable deferral window, or when edition checks were
scattering across the codebase rather than centralizing in the router guards.
The result was gradual, invisible decay that was only visible via a full sweep.

IMP-0013 Phase 4 introduced three hygiene ESLint rules to make this decay
visible continuously. This ADR records the thresholds, age limits, and
philosophy behind those rules so they can be maintained consistently.

---

## Decision

### 1. Orphaned and zombie code threshold

An export is considered **orphaned** when it is exported from a module but
has no import in any other module in the project. A function, class, or
variable is considered **zombie** when it is defined but never referenced.

**Threshold:** Orphaned exports are flagged at `warn` level by the
`no-orphaned-exports` rule. The warn level (not error) is intentional: the
rule uses a heuristic (static import graph) and has a non-trivial false-positive
rate for re-exports, barrel files, and plugin entry points. Warnings accumulate
in the CI log and appear in `npm run lint` output; they do not block CI.

**Resolution obligation:** When the orphaned-export warning count exceeds
**40** (across the whole project), a cleanup task MUST be filed via
`mcp__giljo_mcp__create_project`. The threshold count is intentionally set
above the current baseline (28 at the time of IMP-0013) to give room for
normal development churn without requiring immediate intervention.

**Bridge patterns:** A "bridge" is a module whose sole purpose is to re-export
or adapt another module's interface without adding behavior. Bridges are not
flagged by the orphan rule but are tracked manually during sweeps. A bridge
count above **5 active bridges** triggers a consolidation review.

### 2. TODO age limit

A TODO, FIXME, or HACK comment is considered **stale** when it is older than
**30 days** AND does not reference a project ID.

A project ID is defined as either:
- A GiljoAI project reference in the format `XX-NNNN` (e.g., `FE-5044`,
  `IMP-0013`), OR
- An 8-character lowercase hex string matching a git commit hash prefix.

**Rule:** The `no-stale-todos` ESLint rule flags TODOs/FIXMEs/HACKs that
exceed the 30-day age limit without a project ID. The rule operates at `warn`
level.

**Compliance pattern:**

```js
// BANNED: unanchored TODO older than 30 days
// TODO: refactor this later

// REQUIRED: anchored to a project or commit
// TODO(FE-5044): move this to useApiUrl composable
// FIXME(a1b2c3d4): race condition on first paint, tracked in sprint review
```

New TODOs that are filed without a project ID MUST be resolved or anchored
within 30 days. TODOs that reference a project ID remain valid until the
project closes, at which point they MUST be resolved or re-anchored to the
follow-up project.

### 3. Scattered edition-mode checks

An **edition-mode check** is any inline comparison of the form
`mode === 'ce'`, `giljoMode !== 'saas'`, `GILJO_MODE === 'demo'`, or
equivalent. These checks are legitimate inside the centralized edition modules
and in router-guard / first-paint code; they become a maintenance hazard when
scattered across components, services, and stores.

**Rule:** The `no-scattered-mode-checks` ESLint rule flags inline mode checks
outside the allowlisted modules. The rule operates at `warn` level. The
allowlist of files permitted to perform inline mode checks is:
- `frontend/src/composables/useGiljoMode.js` — the CE-safe centralized edition
  accessor. It also exports the stateless `isCeModeValue` / `isSaasModeValue` /
  `isNonCeModeValue` predicates that other files delegate to when they hold
  their own reactive mode ref.
- `frontend/src/saas/composables/useSaasMode.js` — the SaaS edition accessor.
- `frontend/src/services/configService.js` — the mode source of truth.

Router guards and other non-component contexts that legitimately cannot call a
Vue composable (e.g. `frontend/src/router/authGuard.js`,
`frontend/src/services/setupService.js`) read mode from
`setupService.checkEnhancedStatus()` per ADR-002 and carry a targeted
`// eslint-disable-next-line giljo-internal/no-scattered-mode-checks` with a
justification, rather than being blanket-allowlisted.

All other files that need edition-conditional behavior MUST delegate to
`useGiljoMode()` (or its stateless predicates), rather than performing the
check inline.

The rule inspects both script expressions and Vue `<template>` expressions, and
unwraps `.value` ref access and optional chaining, so the reported warning count
is a trustworthy gauge (FE-9147).

**Relationship to `docs/EDITION_ISOLATION_GUIDE.md`:** The backend edition
isolation rules documented there (CE/SaaS/Demo placement decision tree, import
boundaries, table existence checks) apply to the frontend equivalently. The
`no-scattered-mode-checks` rule is the frontend's enforcement layer for the
principle that edition logic centralizes rather than scatters.

### 4. ESLint rule severity philosophy

The IMP-0013 Phase 4 rules are categorized by severity as follows:

| Severity | Category | Rules |
|----------|----------|-------|
| `error`  | Anti-patterns (correctness) | `no-manual-api-url-composition`, `no-vite-ignore-saas-import`, `vue-router-install-after-routes`, `axios-interceptor-route-meta-aware`, `no-speculative-layout-fallback` |
| `warn`   | Hygiene (debt accumulation) | `no-orphaned-exports`, `no-stale-todos`, `no-scattered-mode-checks` |

`error` rules block `npm run lint` and therefore block CI. They are reserved
for patterns that have caused production failures (traced to the 2026-04-21
demo go-live) or that are categorically unsafe regardless of context.

`warn` rules accumulate in the lint output and are tracked as a debt gauge.
They do not block CI. When the aggregate warning count climbs above the
threshold defined in this ADR, a cleanup project is filed.

No new rule is introduced at `warn` level without documenting the threshold
at which it triggers a mandatory cleanup project. No new rule is introduced
at `error` level without a prior production failure or a concrete security
impact as justification.

---

## Rationale

Treating all quality signals as CI-blocking errors leads to alert fatigue and
rule suppression. Treating all signals as optional warnings leads to invisible
decay. The two-tier approach (error for correctness, warn for hygiene)
preserves CI as a reliable gate for correctness while making hygiene debt
continuously visible without blocking delivery.

The 30-day TODO age limit and the 40-warning orphan threshold were calibrated
against the IMP-0013 baseline (28 warnings, all pre-existing). They leave room
for development churn while still triggering cleanup before debt compounds to
the point where it meaningfully slows navigation of the codebase.

Project IDs on TODOs are required (not just recommended) because an unanchored
TODO has no owner, no delivery vehicle, and no expiry. An anchored TODO
participates in normal project tracking and closes when its project closes.

---

## Consequences

**Positive:**
- The orphan-export warning count provides a continuous debt gauge visible in
  every `npm run lint` run and in CI logs.
- The 30-day / project-ID rule on TODOs converts informal notes into tracked
  work items, preventing "I'll do it later" comments from persisting
  indefinitely.
- Scattered mode checks are flagged before they accumulate to the point where
  edition logic is duplicated across a dozen components.
- The severity philosophy provides a clear decision framework for future rule
  additions, preventing rules from being added at the wrong level out of habit.

**Negative:**
- The `no-orphaned-exports` heuristic has false positives on barrel files and
  plugin entry points. These require suppression comments, which add noise.
  A barrel-file allowlist in the rule is the recommended improvement if
  false-positive rate increases.
- The 40-warning threshold is a manual governance check, not an automated
  CI gate. If the project scales significantly, the threshold should be
  converted to a percentage-of-total-exports metric rather than an absolute
  count.

---

## References

- ESLint rule (orphan exports): `frontend/eslint-rules/rules/no-orphaned-exports.cjs`
- ESLint rule (stale TODOs): `frontend/eslint-rules/rules/no-stale-todos.cjs`
- ESLint rule (scattered mode checks): `frontend/eslint-rules/rules/no-scattered-mode-checks.cjs`
- ESLint rules commit (all 8 rules): `2eb43e7db`
- IMP-0013 quality sweep audit: `198b2e6d9` (`docs(IMP-0013): phase 1 codebase
  quality sweep audit`)
- Edition isolation guide (backend + frontend placement rules):
  `docs/EDITION_ISOLATION_GUIDE.md`
- ADRs for anti-pattern error rules: ADR-003 through ADR-007 in `docs/adr/`
