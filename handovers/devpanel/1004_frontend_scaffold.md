# 1004 – Frontend Scaffold (/developer)

Objective
- Implement a Vue 3 route at `/developer` with left navigation, global search, and section shells that consume 1003 endpoints.

In Scope
- New route `frontend/src/views/DeveloperPanel.vue`.
- Components: `LeftNavTree`, `SearchBar`, `SectionList`, `SectionDetail`, `DiagramCanvas`.
- Data loading from `/api/v1/developer/*` with basic caching and error states.

Out of Scope
- Diagram rendering details (1005).
- Config editing (1006).

Deliverables
- Navigable panel with placeholder content per section reading real JSON.
- Keyboard navigation for search and list focus.
- Localhost‑only banner showing dev gating status.

Acceptance Criteria
- Loads without console errors, handles 403/404 (gating) gracefully.
- Search returns results across all loaded entities.

Primary Data Sources
- 1001/1003 JSON outputs.
- `docs/index.md` and tech stack docs for placeholders.

Implementation Notes
- Use FlexSearch in browser for fast client‑side search.
- Prefer composables for data fetching and state.

Estimate / Owner
- 1–1.5 days; Frontend.

