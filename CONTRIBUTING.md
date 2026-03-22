# Contributing to GiljoAI MCP Coding Orchestrator

Thank you for your interest in GiljoAI MCP.

## Before You Contribute

Read this section first. It affects your intellectual property rights.

### Intellectual Property Assignment

By submitting a pull request, patch, or any other contribution to this
repository, You irrevocably assign all intellectual property rights in
Your contribution to GiljoAI LLC. You represent that You have the right
to make such assignment. GiljoAI LLC may use, license, and sublicense
Your contribution without restriction, including in proprietary and
commercial products.

You retain the right to use Your own contributions in Your other projects.

This assignment is necessary because GiljoAI distributes the Software under
both the GiljoAI Community License (free for single-user use) and commercial
licenses. Without full IP ownership of every line of code, we cannot offer
commercial licenses. This is standard practice for dual-licensed projects.

If you do not agree with these terms, please do not submit contributions.
You are welcome to fork the repository and use it under the terms of the
[LICENSE](LICENSE).

## Development Setup

```bash
# Clone and install
git clone https://github.com/patrik-giljoai/GiljoAI_MCP.git
cd GiljoAI_MCP
python install.py

# Backend
pip install -r requirements.txt
pip install -r dev-requirements.txt
python startup.py --dev

# Frontend
cd frontend
npm install
npm run dev
```

**Requirements**: Python 3.11+, PostgreSQL 18, Node.js 20+

## Code Style

- **Python**: Enforced by [ruff](https://docs.astral.sh/ruff/) (linting and formatting)
- **Frontend**: Enforced by ESLint (`eslint.config.js` flat config)
- **Paths**: Always use `pathlib.Path()` — never hardcode OS-specific paths
- **Logging**: Use `import logging; logger = logging.getLogger(__name__)` in most code. Use `structlog` only in auth, database, WebSocket, and MCP orchestration paths.

Run before committing:
```bash
python -m ruff check src/ api/
python -m ruff format src/ api/
cd frontend && npx eslint src/ --fix
```

## Submitting a Pull Request

1. Create a feature branch from `main`: `git checkout -b feature/short-description`
2. Make your changes following the code style above
3. Run tests: `pytest tests/ -x`
4. Verify frontend builds: `cd frontend && npm run build`
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
6. Push and open a PR against `main`

## Testing

- Run full suite: `pytest tests/ --cov=src/giljo_mcp`
- Coverage target: >80% for new code
- Tests use PostgreSQL with transaction rollback for isolation

## Architecture

- **Service layer**: Business logic in `src/giljo_mcp/services/`. Services raise domain exceptions from `src/giljo_mcp/exceptions.py`.
- **API layer**: FastAPI endpoints in `api/endpoints/`. Global exception handlers map domain exceptions to HTTP status codes.
- **Frontend**: Vue 3 + Vuetify + Pinia stores in `frontend/src/`.
- **Data isolation**: All database queries filter by `tenant_key`. Never bypass tenant isolation.

See `docs/README_FIRST.md` for navigation and `docs/SERVER_ARCHITECTURE_TECH_STACK.md` for full architecture.

## Reporting Issues

Use [GitHub Issues](https://github.com/patrik-giljoai/GiljoAI_MCP/issues) with the provided templates. Include steps to reproduce for bugs.

## Security Vulnerabilities

See [SECURITY.md](SECURITY.md) for responsible disclosure process. Do not open public issues for security vulnerabilities.
