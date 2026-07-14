# ADR-011: The in-app /guide is the canonical end-user documentation surface

**Status:** Accepted (Patrik, 2026-07-11)
**Context:** TSK-8055 (bring the in-app /guide to full end-user coverage), PR #420.

## Decision

1. **No separate `docs/USER_GUIDE/` tree.** The in-app `/guide` route is the single
   canonical home for end-user documentation. README links point at the in-app guide;
   a parallel docs-tree mirror would drift and is deliberately not created.
2. **Guide content lives in two source locations, both shipped to public CE:**
   - Legacy chapters: `docs/PRODUCT_OVERVIEW.md`, `docs/GETTING_STARTED.md`,
     `docs/USER_GUIDE.md` (historical home, protected zone).
   - Net-new chapters: `frontend/src/content/guide/*.md` (added by TSK-8055:
     decision-guide, chains, glossary), mirroring the SaaS-chapter precedent at
     `frontend/src/saas/docs/`.
   `UserGuideView.vue` assembles all of them into the rendered guide, with
   `> [!CE]` / `> [!SAAS]` edition callouts.
3. **New end-user chapters default to `frontend/src/content/guide/`.** Moving the
   legacy `docs/` chapters into the frontend home (or the reverse) is allowed later as
   a mechanical `git mv` + import rewire, but is not required.

## Consequences

- Customer-facing usage docs are versioned and shipped with the app itself; there is
  no second docs pipeline to keep honest.
- Contributor/installer docs remain in `docs/`; the split is by AUDIENCE (end-user
  in-app vs contributor/operator in `docs/`), not by format.
- The guide ships to public CE, so its content must pass the same leak/prose rules as
  any public-bound file.
