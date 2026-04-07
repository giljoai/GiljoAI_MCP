# Handover 0963: In-App User Guide

**Date:** 2026-04-07
**Edition Scope:** CE
**From Agent:** Claude Opus 4.6 (scoping session with product owner)
**To Agent:** Next implementing session
**Priority:** Medium
**Estimated Complexity:** 2-3 days (3 phases)
**Status:** Not Started

---

## Task Summary

Build a full-page, always-accessible User Guide into the application. The guide is a reference manual (not an onboarding tour) that users can reach from the avatar dropdown at any time. Content is sourced from three existing documents, harmonized into a single authoritative in-app experience.

**Why it matters:** The product currently has no in-app reference documentation. The "How to Use" overlay (0908) is a one-time onboarding accordion — not searchable, not bookmarkable, and only accessible via a URL hack (`?openGuide=true`). The landing site has a getting-started page (`getting-started.html`) that new users read before install, but there's no continuity once they're inside the app. For SaaS, an in-app manual is table stakes.

**What changes:** New frontend route (`/guide`), new view component, avatar dropdown update in two files, content sourced from existing markdown. No backend changes.

---

## Content Sources

Three documents exist today. The in-app guide harmonizes them:

| Source | Location | Content | Role in Guide |
|--------|----------|---------|---------------|
| `docs/USER_GUIDE.md` (315 lines) | Repo | Every page/feature documented from code inspection (0910b) | **Primary source** — the reference manual body |
| `docs/PRODUCT_OVERVIEW.md` (82 lines) | Repo | What it is, who it's for, core concepts, how it works | **Introduction chapter** — "What is GiljoAI MCP" |
| `getting-started.html` | `/media/patrik/Work/Nicepage/giljoai-mcp-landing/getting-started.html` | 7-step install-to-monitor walkthrough for the landing page | **Getting Started chapter** — adapted for in-app context (skip install steps, focus on post-login flow) |

### Content Harmonization Rules

- `PRODUCT_OVERVIEW.md` becomes Chapter 1 (intro/concepts)
- `getting-started.html` Steps 3-7 become Chapter 2 (quick start — skip install/account steps since user is already logged in)
- `USER_GUIDE.md` sections become Chapters 3-10 (reference by page)
- All content rendered from markdown source files — not hardcoded in Vue templates
- The `docs/USER_GUIDE.md` and `docs/PRODUCT_OVERVIEW.md` remain the authoritative source files. The frontend reads and renders them. Single source of truth.

---

## Design

### Placement

Avatar dropdown (both `AppBar.vue` and `NavigationDrawer.vue`):
```
My Settings
User Guide          <-- NEW (mdi-book-open-variant icon)
Admin Settings      (if admin)
---
About
Logout
```

### Route

`/guide` — full-page view, standard `default` layout (nav drawer + app bar visible). Auth-required. Lazy-loaded.

Optional: `/guide#products` deep links to sections via anchor scroll.

### Layout

```
+----------------------------------------------------------+
| [Sidebar TOC]  |  [Content Area]                         |
| 200px fixed    |  scrollable, max-width 800px centered   |
|                |                                          |
| > Overview     |  # What is GiljoAI MCP                  |
|   Getting Started|  ...rendered markdown...               |
|   Home Page    |                                          |
|   Dashboard    |                                          |
| > Products     |                                          |
|   Projects     |                                          |
|   Jobs         |                                          |
|   Tasks        |                                          |
|   Settings     |                                          |
|   UI Elements  |                                          |
+----------------------------------------------------------+
```

- Sidebar: sticky TOC with chapter headings. Active chapter highlighted on scroll (IntersectionObserver).
- Content: rendered via `marked` + `DOMPurify` (both already installed and used in `MessageItem.vue` and `BroadcastPanel.vue`).
- Responsive: sidebar collapses to a top dropdown on mobile/narrow screens.
- Style: follows design system — `--bg-surface` background, `--text-primary` body, `--yellow` for active TOC highlight. Uses `.smooth-border` on the sidebar panel.

### No New Dependencies

- `marked` (v17) — already installed
- `DOMPurify` (v3.3) — already installed
- No additional packages needed

---

## Phase 0963a: Route + View + Avatar Dropdown (~1 day)

### Files to Create

**`frontend/src/views/UserGuideView.vue`**
- Full-page view component
- Two-column layout: sticky sidebar TOC + scrollable content area
- Loads markdown content from embedded imports or fetched files (see Content Loading below)
- Renders via `DOMPurify.sanitize(marked(content))`
- Sidebar TOC generated from `## ` headings parsed from the markdown
- Active section tracking via IntersectionObserver on heading elements
- Anchor scroll support (`/guide#products` scrolls to Products section)

### Files to Modify

**`frontend/src/router/index.js`**
- Add route: `{ path: '/guide', name: 'UserGuide', component: () => import('@/views/UserGuideView.vue'), meta: { requiresAuth: true } }`

**`frontend/src/components/navigation/AppBar.vue`** (~line 104, before "About")
- Add menu item: `User Guide` with `mdi-book-open-variant` icon, `@click="$router.push('/guide')"`

**`frontend/src/components/navigation/NavigationDrawer.vue`** (~line 187, before "About")
- Same menu item addition

### Content Loading Strategy

Two options (implement the simpler one):

**Option A — Static import (simpler):** Import the markdown files as raw strings using Vite's `?raw` suffix:
```js
import overviewMd from '@/../docs/PRODUCT_OVERVIEW.md?raw'
import userGuideMd from '@/../docs/USER_GUIDE.md?raw'
```
Concatenate with a getting-started section written inline (adapted from the HTML landing page). This bundles the content into the JS bundle but keeps a single source of truth in the markdown files.

**Option B — Fetch at runtime:** `fetch('/docs/USER_GUIDE.md')` from the static file server. Requires the `docs/` directory to be served statically. More complex, but content updates without rebuilding.

**Recommendation:** Option A. The guide is ~400 lines of markdown — negligible bundle impact. Content changes with code deploys anyway.

### Getting Started Adaptation

The landing page `getting-started.html` Steps 3-7 need to be adapted to markdown for the in-app guide. Create a new file:

**`docs/GETTING_STARTED.md`** (~60 lines)
- Adapted from `getting-started.html` Steps 3-7 (Quick Setup through Monitor)
- Skip Steps 1-2 (Install, Create Account) — user is already logged in
- Rewrite to reference in-app navigation instead of external instructions
- Include the troubleshooting section from the landing page

---

## Phase 0963b: Styling + Responsive + Polish (~0.5 day)

### Styling

- Sidebar: `background: var(--bg-surface)`, `.smooth-border` right edge, TOC items as text links with `color: var(--text-muted)` default, `color: var(--yellow)` active
- Content: standard prose styling — `h2` as section headers, `h3` as subsection headers, tables styled per design system
- Code blocks: `background: var(--bg-elevated)`, `font-family: var(--font-mono)`, `border-radius: 8px`
- Images: if USER_GUIDE references screenshots from `docs/Screen_shots/`, serve them statically or embed them

### Responsive

- Below 768px: sidebar becomes a fixed-position dropdown/select at the top of the content area
- Content area fills full width on mobile

---

## Phase 0963c: Content Harmonization + Final Review (~0.5 day)

### Content Work

1. Review `docs/USER_GUIDE.md` — is it still accurate after 0960, 0961, 0962 changes? Key sections to verify:
   - Products > Tuning (0961 changed the tuning flow to interactive)
   - Jobs > Auto Check-In (0960 changed from button group to slider)
   - Any references to "proposals" or "dashboard review" should reflect the new auto-apply model

2. Write `docs/GETTING_STARTED.md` — adapted from landing page Steps 3-7

3. Verify `docs/PRODUCT_OVERVIEW.md` is current

4. Test the full guide flow: avatar dropdown -> /guide -> scroll through all chapters -> verify anchor links work -> verify mobile layout

---

## Dependencies

- No backend changes required
- No database changes required
- No dependency on other handovers
- The "How to Use" onboarding overlay (0908) remains unchanged — it serves a different purpose (first-time tour vs. reference manual)

---

## Success Criteria

- Avatar dropdown in both AppBar and NavigationDrawer shows "User Guide" item
- `/guide` route renders all content with working TOC sidebar
- TOC highlights active section on scroll
- Anchor links work (`/guide#products` scrolls to Products)
- Content renders correctly via marked + DOMPurify
- Mobile responsive (sidebar collapses)
- Content matches current app behavior (post-0960/0961/0962)
- No new npm dependencies added

---

## Rollback Plan

Frontend-only change. Revert the commit. No data, no backend, no migrations.

---

## Future Considerations (Not in Scope)

- Search within the guide (Ctrl+K or inline search box)
- Contextual help links from individual pages to their guide section
- SaaS: per-plan feature visibility in the guide (hide admin sections for non-admins)
- Video/GIF walkthroughs embedded in guide sections
