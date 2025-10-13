# Repository Guidelines

## Project Structure & Module Organization
Backend orchestration lives in `src/giljo_mcp/` (FastAPI services, mission templates, setup flows). API routers and websocket helpers sit in `api/`. The Vue dashboard is under `frontend/` with static assets in `frontend/public/`. Extensive suites live in `tests/`, split into integration, unit, and scenario files. Deploy and helper scripts stay in `docker/`, `scripts/`, and `configs/`. Store heavy artifacts locally (`logs/`, `data/`, `uploads/`) outside git.

## Build, Test, and Development Commands
- `python install.py` boots the stack, provisions PostgreSQL, and wires the dashboard.
- `python run_api.py` starts the FastAPI backend on port 7272; use `uvicorn api.app:app --reload --port 7272` for hot reload.
- `npm install && npm run dev` inside `frontend/` serves the dashboard on port 5173.
- `pytest tests` executes the backend suite; append `--cov=giljo_mcp` to gather branch coverage.
- `npm run test:coverage` in `frontend/` runs Vitest with coverage for UI modules.

## Coding Style & Naming Conventions
Python code follows Black (120-char limit) and Ruff; run `ruff check src/ api/` then `black src/ api/`. Keep type hints compatible with the strict `mypy` profile in `pyproject.toml`. Modules and functions stay snake_case, classes use PascalCase. Vue components use PascalCase filenames, composables live in `frontend/src/composables/` with `useSomething.ts`, and shared styles live in `frontend/src/styles/`.

## Testing Guidelines
Prefer colocating new fixtures in `tests/fixtures/` and naming tests `test_<feature>.py`. Exercise async paths with `pytest -k async` before merging and reuse orchestrator suites instead of one-off scripts. Maintain coverage targets and log UI regressions with snapshots or storybook notes.

## Commit & Pull Request Guidelines
Adopt the conventional `type: summary` style seen in history (`feat:`, `fix:`, `test:`). Each PR should link tracking issues, describe configuration changes, list executed tests, and attach screenshots or payload samples for UX or messaging changes. Flag rollout risks and required follow-ups before requesting review.

## Security & Configuration Tips
Never commit secrets; copy `config.yaml.example` to `config.yaml` or load values via `.env`. Certificates live in `certs/` and should be regenerated per environment. Review `config_manager.py` when adding settings to keep defaults safe, and update installer scripts that mirror configuration values.

## Claude Agent Context
Default workspace is `F:\GiljoAI_MCP`; runtime files like `.env`, `config.yaml`, `data/`, `logs/`, `temp/`, `venv/`, and `frontend/node_modules/` stay local and out of git. Maintain cross-platform compatibility by using `pathlib.Path` and relative paths. The project runs in localhost or server/LAN modes—respect configuration switches, API key requirements, and PostgreSQL-only support when adjusting services, installers, or docs.
