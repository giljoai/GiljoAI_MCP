# 1001 – Discovery and Audit (Docs ⇄ Code Reconciliation)

Objective
- Build a verified, canonical inventory of APIs, MCP tools, agents/templates, DB entities, orchestration flows, and config surfaces by reconciling `docs/` + `handovers/` with the actual code.

In Scope
- Parse FastAPI routes and generate a machine‑readable API catalog.
- Enumerate MCP tools via ToolAccessor and existing endpoints.
- List agent templates, agents, jobs, and orchestration entities from DB models.
- Map installation and runtime flows to current code.
- Produce JSON inventories to power the Developer Panel and search.

Out of Scope
- UI implementation (Phase 1004).
- Diagramming/exports (Phase 1005).
- Config editing (viewer only in 1006).

Deliverables
- api_catalog.json (OpenAPI + enriched, grouped by tags and module)
- mcp_tool_catalog.json (from `/api/v1/mcp-tools/list` and `ToolAccessor`)
- agent_template_catalog.json (from `api/endpoints/templates.py` + `AgentTemplate`)
- db_schema.json (SQLAlchemy metadata: tables, columns, FKs, relationships)
- dependency_index.json (module import graph; function cross‑refs baseline)
- flows_index.json (installation, orchestration, WS events, from docs + code)
- Search index seeds (minimal Lunr/FlexSearch dataset)

Acceptance Criteria
- All inventories build successfully from a single script and match a spot‑check of 10% sampled endpoints/objects.
- API coverage ≥ 95% of `api/endpoints/*.py` routes.
- DB entities include table name, PK, FKs, relationships, and indexes for `src/giljo_mcp/models.py`.

Primary Data Sources
- API: `api/app.py`, `api/endpoints/*`, `/openapi.json` at runtime.
- MCP: `api/endpoints/mcp_tools.py`, `src/giljo_mcp/tools/tool_accessor.py`.
- Agents/Templates: `api/endpoints/templates.py`, `src/giljo_mcp/models.py:Agent, AgentTemplate`.
- DB: `src/giljo_mcp/models.py`, `src/giljo_mcp/database.py`.
- Flows: `handovers/start_to_finish_agent_FLOW.md`, `docs/INSTALLATION_FLOW_PROCESS.md`, `api/websocket.py`.

Implementation Notes
- Create a dev script `scripts/devpanel_index.py` that can:
  - Load FastAPI app and extract `app.routes` or fetch `/openapi.json` (dev server).
  - Query ToolAccessor and `/api/v1/mcp-tools/list` (if server running) or import handlers to enumerate.
  - Reflect SQLAlchemy `Base.metadata` to JSON with FKs and indexes.
  - Run AST + import graph pass over `src/giljo_mcp/` and `api/` for dependency_index.
  - Parse handover/docs markers for flows and reconcile with code (basic keyword anchors).
- Output files under `uploads/devpanel/index/` or `temp/devpanel/` (excluded from VCS).

Risks / Considerations
- Runtime vs. static analysis parity; keep static fallbacks if API server not running.
- Multi‑tenant constraints in queries; use read‑only sessions.
- Sensitive config redaction.

Estimate / Owner
- 1.5–2.5 days engineering; Backend.

