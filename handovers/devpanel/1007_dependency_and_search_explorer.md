# 1007 – Dependency Explorer and Global Search

Objective
- Provide a code‑aware explorer: search for a function/class/module and view cascading dependencies (imports, call sites, related endpoints/models), with a fast global search.

In Scope
- Static analysis: AST + import graph for `src/giljo_mcp/` and `api/`.
- Index entities: functions, classes, modules, endpoints, models, tools.
- UI: search results + dependency tree/graph view.

Out of Scope
- Runtime tracing/profiling.

Deliverables
- `dependency_index.json` (from 1001) expanded with call‑site heuristics.
- `GET /api/v1/developer/dependency-index` (already in 1003).
- Frontend tree/graph visualizer with deep links to file + line.

Acceptance Criteria
- Find by symbol name returns entity with at least file path and line number reference.
- “Cascading” shows at least 2 levels (direct + one hop) of imports/callers.

Primary Data Sources
- Source directories: `src/`, `api/`.
- Ripgrep + Python AST for symbol and reference extraction.

Implementation Notes
- Use `rg` to seed candidates; confirm with AST to reduce false positives.
- File references must use workspace‑relative paths with `:line` anchors.

Estimate / Owner
- 1–2 days; Full‑stack.

