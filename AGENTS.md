# Repository Guidelines

This document guides contributors working on the **GiljoAI Agent Orchestration MCP Server**.

## Project Structure & Modules

- `src/giljo_mcp/` – core orchestrator logic, MCP tools, services.
- `api/` – FastAPI app, routes, dependency wiring.
- `frontend/` – Vue 3 dashboard, components, stores.
- `tests/` – Python tests (unit/integration); mirror `src/` layout.
- `docs/` – architecture, installation, and product specs.

## Build, Test, and Dev Commands

- Backend install/dev: `python install.py`, then `python startup.py --dev`.
- Backend tests: `pytest tests/`.
- Lint/format backend: `ruff src/` and `black src/`.
- Frontend dev: `cd frontend && npm run dev`.
- Frontend build/test: `cd frontend && npm run build` / `npm test` (if defined).

## Coding Style & Naming

- Python: 4-space indentation; follow existing patterns and type hints.
- Vue/JS: follow existing component style; keep components small and focused.
- Prefer descriptive names (`TenantProjectService`, `orchestrator_job_id`) over abbreviations.
- Use `pathlib.Path` and relative paths; never hard-code absolute Windows paths.

## Testing Guidelines

- Add/extend tests under `tests/` mirroring the module under `src/`.
- Use `pytest` style fixtures and parametrization where helpful.
- Name tests by behavior: `test_<function>_<case>()`.
- Ensure new features include at least basic happy-path and failure tests.

## Commit & Pull Request Guidelines

- Use short, imperative commit messages with prefixes when helpful: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- Keep commits logically scoped (one feature/fix per commit when possible).
- PRs should include: short summary, rationale, testing notes (`pytest`, `npm run dev` smoke), and linked issues or handover IDs.

## Agent-Specific Instructions

- When exploring or editing code with AI tools, prefer Serena MCP symbolic tools (`get_symbols_overview`, `find_symbol`) before full-file reads.
- Keep prompts and comments concise; avoid embedding large specs directly into code.

## Design Policies (Nov 2025)

- Per-User Tenancy: Every user is assigned a unique `tenant_key` at registration. Treat tenant = user for isolation. Do not attempt to share data across tenants.
- Active Product: Single active product per tenant. Under per-user tenancy, this behaves as per-user active product.
- HTTP-only MCP: Use the HTTP JSON-RPC endpoint (`/mcp`). Stdio adapter paths are deprecated; do not add or rely on FastMCP registrations.
- TDD Discipline: Write tests first, assert behavior (not implementation), then implement minimal changes and refactor.

## AI Agent Initialization Reference

This section summarizes the key behavioural and architectural expectations that should be assumed by any AI agent or prompt template working against the GiljoAI MCP server.

- **Product Identity & Architecture**
  - GiljoAI MCP is a multi-tenant agent orchestration server: backend = Python/FastAPI/PostgreSQL, frontend = Vue 3/Vuetify, orchestration via MCP over HTTP.
  - All project and agent work should flow through the MCP tools and REST APIs; do not bypass them with ad-hoc DB or filesystem access.

- **Per-User Tenancy & Safety**
  - Treat `tenant_key` as user-level isolation. Every MCP tool call must include and respect the provided tenant key.
  - Never mix data across tenants; any cross-tenant access is considered a critical bug.

- **HTTP-Only MCP Contract**
  - Use the HTTP JSON-RPC endpoint at `/mcp` with `X-API-Key` for all MCP traffic.
  - Stdio-based adapters and local FastMCP registrations are deprecated and must not be assumed in new work.

- **Context Management Model (Priority + Depth)**
  - Priority (WHAT to fetch): `product_core`, `vision_documents`, `tech_stack`, `architecture`, `testing`, `agent_templates`, `project_context`, `memory_360`, `git_history`.
  - Depth (HOW MUCH to fetch): per-category knobs such as `vision_chunking`, `memory_last_n_projects`, `git_commits`, `architecture_depth`, etc.
  - Agents and orchestration code should respect `field_priority_config` and `depth_config` when deciding which MCP context tools to call and how much to pull from each.

- **Thin-Client Prompts (Critical Concept)**
  - Thin-client prompts are *lean* prompts whose primary job is to tell the agent **how to talk to the MCP server**, not to inline all context or mission text.
  - Typical pattern: “Read your instructions on the server using `mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}', '{tenant_key}')`”, or for spawned agents, `mcp__giljo-mcp__get_agent_mission(job_id, tenant_key)`.
  - The full mission and context live on the server for **auditability** and **replay**; users paste only the thin prompt into Claude Code or other CLIs.
  - Agents can call the same MCP tools again at any time to **re-read their initial instructions** and refresh context instead of relying on a one-shot, giant clipboard prompt.

- **Orchestrator Workflow Pipeline (v3.2)**
  - Staging → Discovery → Spawning → Execution, with context and missions fetched via MCP tools (`get_orchestrator_instructions`, `get_available_agents`, `get_generic_agent_template`, `get_agent_mission`).
  - Orchestrator and agents are expected to follow the six-phase protocol (init, mission fetch, work, progress reporting, communication, completion) defined in the generic templates and Claude agent templates.

- **Coding Standards & Testing Expectations**
  - Always use `pathlib.Path` and relative paths; never hard-code absolute Windows paths (e.g., `F:\...`).
  - Prefer TDD where feasible and maintain high coverage on new backend code; align with existing patterns in `src/giljo_mcp/services/` and the FastAPI endpoints.

- **360 Memory & Closeout Semantics**
  - Project closeout is responsible for writing learnings and outcomes into `product.product_memory` (360 memory) so future agents can read that history via MCP context tools like `fetch_360_memory`.
  - Agents and tools must not bypass closeout / 360 memory mechanisms when recording project-level decisions or outcomes.
