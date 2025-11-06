# 1003 – Backend Data Services for Developer Panel

Objective
- Expose read‑only Developer Panel backend endpoints that serve inventories, schemas, and graphs produced in 1001 for frontend consumption.

In Scope
- New `api/endpoints/developer_panel.py` with `/api/v1/developer/*` routes.
- Serve: api_catalog, mcp_tool_catalog, agent_template_catalog, db_schema, dependency_index, flows_index, search index, tech_stack.
- Add health and gating endpoints.

Out of Scope
- UI (1004) and PPT export (1005).
- Editing config values (viewer only until 1006).

Deliverables
- JSON endpoints:
  - `GET /api/v1/developer/api-catalog`
  - `GET /api/v1/developer/mcp-tools`
  - `GET /api/v1/developer/agents-templates`
  - `GET /api/v1/developer/db-schema`
  - `GET /api/v1/developer/dependency-index`
  - `GET /api/v1/developer/flows`
  - `GET /api/v1/developer/search-index`
  - `GET /api/v1/developer/tech-stack`
  - `GET /api/v1/developer/health`
- Gating: `ENABLE_DEVPANEL=true` env required; else 404.

Acceptance Criteria
- All endpoints return within < 500ms cached, < 2s cold.
- Responses validate against documented JSON schemas.
- Disabled by default in production environments.

Primary Data Sources
- Inventories from 1001 (`temp/devpanel/*.json`).
- API: `api/app.py`, `api/endpoints/*` for router integration.
- Config: `.env.example` for new `ENABLE_DEVPANEL` variable.

Implementation Notes
- Use `lru_cache` or in‑memory cache; refresh triggers on file mtime.
- Consider background refresh task (interval 60–120s) gated by env.

Estimate / Owner
- 1–1.5 days; Backend.

