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

