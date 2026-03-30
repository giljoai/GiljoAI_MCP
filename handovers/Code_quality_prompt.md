# Code Quality Audit Prompt

**Purpose:** Reusable prompt for comprehensive code quality audits. Agents reading this should launch parallel subagents and report findings with a per-dimension quality score.

**Usage:** Ask an agent: "Read `handovers/Code_quality_prompt.md` and execute the audit."

**Frequency:** After every 15-30 commits, or before any release milestone.

**Baseline:** 0769 sprint (March 2026) — 8.5/10, 1,893 frontend tests / 0 skipped, 661 backend unit tests / 0 failures, zero ruff issues, ESLint 6 warnings (budget 8). MyPy blocked by src-layout dual-module-name (pre-existing). Alembic chain valid (model drift detected — indexes/comments only, not structural).

---

## Instructions for the Executing Agent

You are performing a code health audit. Your job is to detect drift from the established clean baseline and score the codebase on 10 dimensions.

### Step 1: Scope the Audit

Determine the commit range to audit:

```bash
git log --oneline -30
git diff --stat HEAD~30..HEAD
```

Count files changed, lines added/removed. This frames the audit scope.

### Step 2: Automated Checks

Run these directly (do NOT delegate to subagents):

```bash
# Backend linting (baseline: 0 issues)
ruff check src/ api/

# Frontend linting (baseline: 6 warnings, budget: 8 max)
cd frontend && npx eslint src/ --max-warnings 8

# Frontend build (baseline: clean build, main chunk ~736KB)
cd frontend && npm run build

# CE/SaaS import boundary (baseline: 0 violations)
python scripts/check_saas_import_boundary.py src/ api/ frontend/src/

# Frontend test suite (baseline: 1,893 pass, 0 skip, 0 fail)
cd frontend && npx vitest run

# Backend unit tests (baseline: 661 pass, 0 fail — no DB required)
python -m pytest tests/unit/ -q --timeout=60 --no-cov

# Backend full suite (requires PostgreSQL giljo_mcp_test database)
# Integration/smoke/e2e tests need DB — see tests/helpers/test_db_helper.py
python -m pytest tests/ -q --timeout=60 --no-cov
```

### Step 2b: Runtime & Type Verification

These checks catch issues that linting and unit tests miss (circular imports, broken migrations, type mismatches after refactors):

```bash
# Startup verification — catches circular imports and broken service wiring
# Must succeed without a running database (import-only check)
python -c "from api.app import create_app; print('Startup import OK')"

# Type checking (baseline: blocked by src-layout dual-module-name issue)
# The editable install + mypy_path=src causes "Source file found twice" error.
# CI runs: mypy src/ --ignore-missing-imports --no-strict-optional || true
# To unblock locally: pip install -e . in a venv without src/ on PYTHONPATH.
python -m mypy src/ --ignore-missing-imports --no-strict-optional 2>&1 | tail -5

# Migration chain validity
alembic check

# Frontend coverage (baseline: 80% lines/functions/statements, 75% branches)
cd frontend && npx vitest run --coverage 2>&1 | grep -A5 "Coverage summary"
```

### Step 2c: Dependency Security

```bash
# Python dependency vulnerabilities
pip-audit 2>&1 | tail -10

# Frontend dependency vulnerabilities
cd frontend && npm audit --audit-level=moderate 2>&1 | tail -10
```

Record all results. Any regression from baseline is a finding.

### Step 3: Launch Parallel Audit Subagents

Launch **5 subagents in parallel** using the `deep-researcher` agent type:

#### Subagent 1: Backend Source Code (`src/giljo_mcp/`)

Search for:
- **Dead methods**: Use `find_referencing_symbols` on any method that looks unused. Zero refs = dead code.
- **Dict return regression**: Services MUST raise exceptions (not `return {"success": False, ...}`). Grep for `return {"success": False` or `return {"error":` in services and tools.
- **Broad exception catches**: `except Exception` without an inline justification comment. After 0765d, all broad catches must be annotated.
- **Stale status values**: Valid agent statuses are ONLY: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned`. Flag any code referencing old statuses (`active`, `pending`, `preparing`, `running`, `queued`, `paused`, `review`, `planning`, `failed`, `cancelled`, `completed`).
- **Oversized functions**: Methods >200 lines. Classes >1000 lines.
- **Duplicate logic**: Service layer vs tool layer doing the same thing.
- **Config reading pattern**: Repeated `yaml.safe_load(open("config.yaml"))` instead of using config_manager.

#### Subagent 2: API Endpoints & Security (`api/`)

Search for:
- **Tenant isolation gaps**: Every DB query MUST filter by `tenant_key`. Look for endpoints that query without it.
- **Auth gaps**: Every endpoint MUST use `Depends(get_current_active_user)` except explicitly public ones (login, health, setup). Admin-only endpoints must check role.
- **CSRF protection**: Verify CSRF double-submit cookie is enforced on state-changing endpoints.
- **Dict returns in endpoints**: Endpoints should raise `HTTPException`, not return dicts.
- **Secrets in source**: Grep for hardcoded API keys, passwords, tokens (except test fixtures).
- **CORS configuration**: Verify origins are restricted, not wildcarded in production.
- **Oversized handler functions**: Single endpoint handlers >200 lines.

#### Subagent 3: Test Suite (`tests/`)

Search for:
- **Skipped tests**: Any `@pytest.mark.skip` or `pytest.skip()`. Baseline is zero skips.
- **Dead test fixtures**: Files in `tests/fixtures/` never imported by any test.
- **Stale `__pycache__`**: Bytecode from deleted test modules.
- **Oversized test files**: Files >500 lines that should be split.
- **Test coverage gaps**: Are there service methods with zero test coverage? Check critical paths (auth, tenant isolation, orchestration).

#### Subagent 4: Frontend (`frontend/src/`)

Search for:
- **Dead code**: Unused variables, dead store state, event handlers wired but never triggered.
- **Design token compliance**: Hardcoded hex colors instead of Vuetify theme tokens or `design-tokens.scss` variables. After 0765c, zero hardcoded colors is the baseline.
- **Accessibility**: Interactive elements missing ARIA labels.
- **`!important` overrides**: Flag any that aren't compensating for a documented Vuetify bug.
- **Stale backend references**: Frontend calling endpoints or using features that no longer exist.
- **Duplicated utilities**: Same logic reimplemented in multiple components (e.g., clipboard, date formatting).

#### Subagent 5: Convention & Documentation Compliance

Search for:
- **Forbidden terminology**: Grep all shipping files for "MIT", "open source", "open core". These violate the GiljoAI Community License v1.1.
- **Version consistency**: All public-facing version numbers should match (pyproject.toml, package.json, app.py, AppBar.vue, etc.).
- **CE/SaaS import boundary**: CE code (`src/giljo_mcp/`, `api/`, `frontend/src/` excluding `saas/` dirs) must NEVER import from `saas/` directories.
- **Documentation sync**: Do docstrings and inline comments match current behavior? Flag stale references to removed features, old status values, or deleted files.
- **Commented-out code**: Should be deleted, not commented. Git has the history.
- **No AI signatures**: No "Generated by", "Co-Authored-By", or similar in source code (commits are fine).

### Step 4: Consolidate and Score

After all subagents complete, compile results using the **10-Dimension Rubric**:

```markdown
## Code Quality Audit Report
**Date:** YYYY-MM-DD
**Commit Range:** [first]...[last] (N commits)
**Auditor:** [agent session identifier]

### Automated Check Results
- Ruff: N issues (baseline: 0)
- ESLint: N warnings (baseline: 8)
- Frontend build: clean / N warnings
- CE/SaaS boundary: N violations (baseline: 0)
- Tests: N pass / N skip / N fail (baseline: 1,390+ / 0 / 0)

### 10-Dimension Rubric Scoring

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | **Lint cleanliness** | X/10 | Ruff + ESLint results |
| 2 | **Dead code density** | X/10 | Unreferenced methods, dead vars, dead store state |
| 3 | **Pattern compliance** | X/10 | Exceptions not dicts, correct error handling |
| 4 | **Tenant isolation** | X/10 | Every DB query filters by tenant_key |
| 5 | **Security posture** | X/10 | CSRF, CORS, auth coverage, no secrets in source |
| 6 | **Test health** | X/10 | Zero skips, zero failures, no dead fixtures |
| 7 | **Frontend hygiene** | X/10 | Design tokens, no dead vars, accessibility |
| 8 | **Exception handling** | X/10 | All broad catches annotated with justification |
| 9 | **Code organization** | X/10 | No oversized functions/classes, clear separation |
| 10 | **Convention & docs** | X/10 | No forbidden terms, version consistency, doc sync |

**Overall Score: X.X/10** (baseline: 8.35, target: >= 8.0)

### Findings by Severity

#### SECURITY (fix immediately)
- [tenant isolation gaps, auth bypass, CSRF gaps, secrets]

#### HIGH (fix before next release)
- [dead methods >50 lines, dict return regressions, broad catches]

#### MEDIUM (fix in next cleanup pass)
- [stale statuses, oversized functions, dead config, doc drift]

#### LOW (housekeeping)
- [unused imports, dead fixtures, stale pycache, cosmetic]
```

### Step 5: Prioritized Action List

End the report with a numbered action list, ordered by:
1. Security fixes (do immediately)
2. Quick wins (<5 minutes each, high impact)
3. Medium effort cleanup (15-30 minutes each)
4. Technical debt (requires planning)

For each item, include: file path, line number, what to do, estimated effort.

---

## What This Audit Does NOT Cover

- **Feature correctness** — This is a code hygiene audit, not a functional test.
- **Performance** — No load testing or query optimization analysis.
- **SaaS-specific code** — Code in `saas/` directories is audited separately when that edition is active.

---

## False Positive Prevention (Lessons from 0725 + 0765)

A previous audit (0725) had a 75%+ false positive rate. Four subsequent 0765 audits had shifting criteria. To avoid both problems:

- **Always verify with `find_referencing_symbols`** before flagging dead code. LSP-based analysis catches real usage that grep misses.
- **Check git blame/log** before flagging something as "newly introduced" — it may be pre-existing.
- **Distinguish product integration code from dead code**: References to `claude-code`, `codex`, `gemini` are product features, not bloat.
- **Slash commands infrastructure is intentional**: `SlashCommandSetup.vue`, `slash_commands/__init__.py`, `/slash/execute` endpoint are all live.
- **Use the same 10 dimensions every time**. Do not invent new criteria mid-audit. If a new concern arises, note it as an addendum, don't retroactively change the scoring.
- **Score what you find, not what you feel**. Each dimension has a concrete definition. A codebase with zero dead code scores 10/10 on dead code even if other dimensions are weak.
