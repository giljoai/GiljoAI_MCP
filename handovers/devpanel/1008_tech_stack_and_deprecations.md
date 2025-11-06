# 1008 – Tech Stack and Deprecations

Objective
- Generate an authoritative tech stack view with versions and known deprecations, cross‑checked against `pyproject.toml`, `requirements.txt`, and code references.

In Scope
- Collate runtime framework versions (FastAPI, SQLAlchemy, Pydantic, WebSocket libs, Vue/Vite).
- Extract deprecations and risky APIs (e.g., legacy auth paths, deprecated models/fields).
- Present in panel with export (CSV/Markdown) and flags.

Deliverables
- `GET /api/v1/developer/tech-stack` JSON.
- CSV/MD exports via downloads.
- “Known Deprecations” section with source citations.

Acceptance Criteria
- Versions match installed environment on the running server.
- Deprecation list includes doc and code references with file:line anchors.

Primary Data Sources
- `pyproject.toml`, `requirements.txt`, `docs/SERVER_ARCHITECTURE_TECH_STACK.md`.
- Code scans: `src/giljo_mcp/config_manager.py` (tech detection), repository imports.

Estimate / Owner
- 0.5–1 day; Backend.

