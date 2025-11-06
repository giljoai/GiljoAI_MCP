# 1002 – Information Architecture (IA) and UX Blueprint

Objective
- Define the navigation, taxonomy, search model, and core interactions for a left-nav Developer Panel with expandable menus and a global search bar, designed like an interactive manual.

Navigation (Left Pane)
- Overview
- Architecture (multi-view)
- APIs (searchable catalog)
- MCP Tools (searchable index)
- Agents & Templates
- Database Schema
- Installation Flow
- Dependency Explorer
- Configuration
- Tech Stack & Deprecations

Search
- Global search box (keyboard focus `/`).
- Facets: Section, entity type (endpoint, model, tool, table), tag.
- Results show title, short description, source, deep link.

Screens & States
- List/detail pairs per section with persistent left nav.
- “Diagram” mode toggle renders visual view.
- Localhost banner + gating indicator.

Deliverables
- Wireframes (low-fi) for each section (upload as `/uploads/devpanel/wireframes/*.png`).
- Navigation schema (JSON) mirroring the final menu layout.
- Search schema (JSON) with entity fields and ranking.

Acceptance Criteria
- Stakeholder sign-off on menu taxonomy and page states.
- Search schema covers ≥ 90% of planned entities.

Primary Data Sources
- `docs/index.md`, `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- `handovers/start_to_finish_agent_FLOW.md`, `handovers/MCP Tools needs.md`

Estimate / Owner
- 0.5–1 day; Product + UX + Frontend.
