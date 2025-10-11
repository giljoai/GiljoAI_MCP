# Codebase Cleanup Investigation & Validation Plan – 2025-10-08

## Inputs & Scope
- Harmonized sources: `2025-10-08_backend_proposals.md` and `2025-10-08_frontend_proposals.md`.
- Goal: Equip a fresh agent to validate suspected zombies/orphans, prove safety to remove, and identify production hardening tasks across backend (FastAPI + Python) and frontend (Vue + Vite).
- Non‑goals: Performing the deletions now; this is a validation and planning pass.

## Key Targets (from prior reports)
- Backend
  - Unused duplicate: `src/giljo_mcp/tools/tool_accessor_enhanced.py`
  - Broken legacy: `src/giljo_mcp/tools/claude_code_integration.py`
  - Orphaned services: `src/giljo_mcp/services/{serena_detector.py, claude_config_manager.py}`
  - Placeholders shipped: `SerenaHooks` in `src/giljo_mcp/discovery.py`; Serena guidance embedded in `template_manager.py`
  - Naming debt: `auth_legacy.py` (still active)
- Frontend
  - Backups/alternates: `src/services/setupService.js.bak`, `src/components/setup/DatabaseStep.vue.old`, `DatabaseStep_NEW.vue`
  - Unused composable: `src/composables/useFocusTrap.js`
  - Serena UI toggles vs missing backend capability

## Environment Setup
- Python: `python>=3.10`, virtualenv, local PostgreSQL (test DB allowed). Node: `node>=20`.
- Add `src` to `PYTHONPATH` when running static analyzers.
- Ensure frontend `.env` (or Vite env vars) mirrors typical dev settings (no production keys).

## Phase 1 – Static Inventory & Orphan Detection
- Backend
  - Dead-code scan: vulture against `src/giljo_mcp` (whitelist test files) to surface unused functions/classes.
  - Import graph: pydeps or grimp to visualize module reachability; flag nodes only referenced by tests/docs.
  - Pattern sweep: `rg -n "(\.bak$|\.old$|_NEW\.|TODO|NotImplementedError)"` within `src/giljo_mcp/`.
- Frontend
  - Orphans: dependency-cruiser or madge to detect unreachable modules from `index.html` and `wizard.html` entry points.
  - Unused exports: ESLint (`no-unused-vars`, `import/no-unused-modules`) and knip/depcheck for JS.
  - Artifact sweep: `find src -name '*.bak' -o -name '*.old' -o -name '*_NEW.*'`.

## Phase 2 – Dynamic Reachability & Coverage
- Backend
  - Startup/import smoke: `python -m compileall src` and targeted `python -c "import ..."` for suspect modules to confirm failures (e.g., `claude_code_integration.py`).
  - Scenario coverage: run representative API tests with `pytest --cov=giljo_mcp --cov-report=term,html`; confirm zero coverage for suspected orphans.
  - Tracing: `python -m trace --trace -m api.app` while exercising key endpoints to log executed modules.
- Frontend
  - Unit/integration via Vitest + happy-dom: `vitest run --coverage` focusing on wizard, settings, and router guards.
  - Build graph: `vite build` + rollup visualizer to ensure orphaned files are tree-shaken (not bundled).

## Phase 3 – Contract & Feature-Flag Validation
- OpenAPI contract
  - Export schema from FastAPI (`/openapi.json`). Diff frontend API paths in `frontend/src/services/api.js`/`setupService.js` against the schema (tooling: spectral, openapi-diff) to detect dead endpoints and mismatches.
- Serena gating
  - Decide feature flag: `FEATURE_SERENA` (backend) and `VITE_FEATURE_SERENA` (frontend). Verify UI toggles hide when unavailable and templates avoid promising unsupported flows.
- Auth/tenant defaults
  - Identify non‑production fallbacks (e.g., default tenant key in `api.js`). Require explicit config in production mode.

## Phase 4 – Safe Removal Protocol (Per Item)
For each flagged file/module:
1) Prove orphan status (no imports in app code; not bundled; zero runtime coverage).
2) Confirm docs/tests referring to it are archived or updated.
3) Prepare branch that removes only the file and any import lines.
4) Validate: `pytest -k 'smoke or api or orchestrator' --maxfail=1` and `vite build`.
5) If failures occur, revert and either re‑scope or replace with a minimal adapter.

Acceptance for removal: No app imports, no bundle inclusion, no coverage, and no contract references.

## Production Hardening Checklist
- Replace placeholder Serena hooks with feature‑flagged no‑ops and update templates accordingly.
- Rename/retire `auth_legacy.py` after confirming parity in LAN/WAN flows.
- Eliminate backups (`*.bak`, `*.old`, `*_NEW.*`) from `src/` trees.
- Enforce CI gates: ruff + black + mypy (backend), eslint + vitest + build (frontend), vulture + dep-cruiser or madge reports must show zero orphans.

## Gaps in Current Reports
- No build‑time bundle graph verification for the frontend; add rollup analyzer outputs to prove orphans.
- No OpenAPI vs client service diff; add automated comparison.
- Limited dynamic tracing on backend; add `trace`/`coverage` runs per core flows (setup, projects, agents, messages).
- No duplication scan; add `flake8-simplify`/`radon` (Python) and `jscpd` (JS) to catch copy‑paste duplication.

## Suggested Tooling (beyond LLM analysis)
- Python: vulture (dead code), pydeps/grimp (imports), coverage.py, mypy, ruff, bandit, radon, semgrep.
- Frontend: dependency-cruiser or madge (graphs/orphans), knip and depcheck (unused code/deps), eslint (`import/no-unused-modules`), rollup-plugin-visualizer, jscpd (duplication).
- Contract: spectral, openapi-diff, schemathesis (optional fuzz contract tests).

## Deliverables & Artifacts
- Reports: attach vulture/dependency graphs and coverage summaries to `docs/code_cleaning/reports/`.
- Change PRs: one PR per removal cluster (backend tools, services, frontend backups) with checklists and rollback notes.
- Updated docs: `AGENTS.md` and user‑facing README sections reflecting feature flags and removed modules.

## Milestones
1. Static scans & graphs published.
2. Coverage/tracing results attached; removal candidates confirmed.
3. Feature‑flag gating merged; Serena messaging harmonized.
4. Orphan removals merged; CI gates enforced.
5. Final production readiness review sign‑off.

