# Repository Guidelines

## Project Structure & Module Organization
- Backend: `src/giljo_mcp/` (core orchestration, FastAPI integrations), API entry in `api/`.
- Frontend: `frontend/` (Vue 3/Vite).
- Tests: `tests/` (pytest; unit, integration, websocket, API), plus a few root-level `test_*.py`.
- Config & assets: `.env.example`, `config.yaml.example`, `docs/`, `migrations/`, `uploads/`, `logs/`.

## Build, Test, and Development Commands
- Setup (dev): `python -m venv venv && source venv/bin/activate && pip install -e .[dev]` (or `pip install -r requirements.txt -r dev-requirements.txt`).
- Run everything (auto-detects setup): `python startup.py --dev`.
- API only (reload): `python api/run_api.py --reload --port 7272`.
- Frontend dev: `cd frontend && npm ci && npm run dev`; build: `npm run build`.
- Backend tests (quick): `pytest -q` or `pytest -c pytest_no_coverage.ini`.
- Backend coverage: `pytest --cov=giljo_mcp --cov-report=term-missing`.
- Frontend tests: `cd frontend && npm test` (Vitest) or `npm run test:coverage`.

## Coding Style & Naming Conventions
- Python: 4-space indent, line length 120, double quotes preferred. Use type hints for public APIs.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`.
- Imports: prefer absolute within `giljo_mcp`.
- Lint/format: Ruff first: `ruff check . --fix` and `ruff format .`; Black optional: `black .`.

## Testing Guidelines
- Framework: pytest (see `pytest_no_coverage.ini`). Place tests under `tests/`; files `test_*.py`, functions `test_*`.
- Use markers (`@pytest.mark.integration`, `@pytest.mark.unit`) where appropriate.
- Example: `tests/test_agent_job_manager.py`, `tests/integration/test_agent_jobs_api.py`.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`. Reference handovers when relevant (e.g., `feat: Handover 0076 – ...`).
- PRs: clear description, linked issue, test coverage notes, screenshots/GIFs for UI, and reproduction/verification steps. Keep changes focused.

## Security & Configuration Tips
- Never commit secrets. Use `.env.example` and `config.yaml.example` to document settings; keep local secrets in `.env`/`config.yaml`.
- Database binds to localhost; API defaults to `0.0.0.0` with OS firewall control. Validate via `python api/run_api.py --host 0.0.0.0` only if intended.

## Agent-Specific Instructions
- Keep patches minimal and scoped; don’t alter migrations or installer flows without justification.
- Update docs when changing behavior; run `pytest` and `ruff check` before opening a PR.
