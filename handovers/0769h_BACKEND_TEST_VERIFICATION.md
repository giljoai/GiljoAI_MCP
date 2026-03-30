# 0769h: Backend Test Verification & Runtime Checks

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 8 of 9 (extension)
**Branch:** `feature/0769-quality-sprint`
**Priority:** HIGH — backend has zero local test verification
**Estimated Time:** 2-3 hours

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md`
- **Test config:** `pyproject.toml` (lines 229-258)
- **CI pipeline:** `.github/workflows/ci.yml` (Python test matrix)
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

The 0769 audit and sprint (phases a-g) relied exclusively on ruff linting and vitest (frontend) for verification. The backend — where security fixes, service splits, tenant isolation, and config changes happened — has **196 Python test files and ~51K lines of test code** that were never run locally during the sprint. The CI pipeline runs them across Python 3.10-3.12, but local execution returned "no tests ran" during the audit.

This phase diagnoses and fixes local Python test execution, verifies the backend starts after the service splits, and establishes a local verification baseline.

---

## Scope

### Task 1: Diagnose and Fix Local pytest Execution

**Problem:** `python -m pytest tests/ -q --timeout=60` returns "no tests ran" locally.

**Investigation steps:**
1. Check `pyproject.toml` test configuration (testpaths, markers, collection)
2. Check if tests require a running PostgreSQL database and if the test database exists
3. Check conftest.py fixtures — do they require specific environment variables or setup?
4. Check if tests use markers that filter them out by default (e.g., `@pytest.mark.integration`)
5. Try running a specific unit test directly: `python -m pytest tests/unit/ -v --timeout=60`
6. Check the CI pipeline in `.github/workflows/ci.yml` for the exact pytest invocation and environment setup

**Fix:** Get at least the unit tests running locally. Document the required setup (database, env vars, etc.) and update the audit prompt's pytest command accordingly.

### Task 2: Backend Startup Verification

**Verify the application imports and starts after 0769c service splits:**

```bash
python -c "from api.app import create_app; print('OK')"
```

If this fails, diagnose and fix:
- Circular imports from service extraction
- Missing `__init__.py` exports
- Broken import paths in the new service files

**Also verify:**
```bash
python -c "from src.giljo_mcp.services.orchestration_service import OrchestrationService; print('OrchestrationService OK')"
python -c "from src.giljo_mcp.services.project_service import ProjectService; print('ProjectService OK')"
python -c "from src.giljo_mcp.services.job_lifecycle_service import JobLifecycleService; print('JobLifecycleService OK')"
python -c "from src.giljo_mcp.services.mission_service import MissionService; print('MissionService OK')"
python -c "from src.giljo_mcp.services.progress_service import ProgressService; print('ProgressService OK')"
```

### Task 3: MyPy Baseline

Run MyPy and establish a baseline error count:

```bash
python -m mypy src/ api/ --ignore-missing-imports
```

Do NOT fix MyPy errors — just record the count as a baseline for the audit prompt. If there are obvious type errors from the service splits (e.g., wrong return types on facade methods), fix those only.

### Task 4: Migration Chain Verification

```bash
alembic check
```

Verify the migration chain is valid after the backend changes. If `alembic` is not in PATH, try `python -m alembic check`.

### Task 5: Update Code Quality Prompt

Update `handovers/Code_quality_prompt.md` Step 2 baselines with actual results:
- Python test count and pass rate
- MyPy error count baseline
- Startup verification command (confirmed working)
- Any required setup documented

---

## Agent Protocols (MANDATORY)

### Rejection Authority
If Python tests require a running PostgreSQL database and the test database doesn't exist locally, document this requirement clearly rather than trying to set up a test database. The goal is to understand what works and what doesn't, not to force everything to pass.

### Flow Investigation
Before modifying any test infrastructure, understand the CI pipeline's test setup. The CI uses PostgreSQL 15 with health checks — replicate the same environment locally if possible, but don't break the CI configuration.

If you discover the local test failure is a fundamental environment issue (missing database, wrong Python version, etc.) rather than a code issue, document the findings and set status to `complete` with the diagnosis. Do NOT set to `blocked` for expected environment differences.

---

## What NOT To Do

- Do NOT write new tests — just get existing ones running
- Do NOT modify test files unless fixing import paths broken by 0769c
- Do NOT set up a test database from scratch — document the requirement
- Do NOT fix MyPy errors beyond obvious type mismatches from service splits
- Do NOT modify production code

---

## Acceptance Criteria

- [ ] Root cause of "no tests ran" identified and documented
- [ ] At least unit tests running locally (or clear documentation of why they can't)
- [ ] Backend startup verification passes for all service imports
- [ ] MyPy baseline count recorded
- [ ] Migration chain verified
- [ ] Code_quality_prompt.md updated with actual baselines and correct commands

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives`
- Review all previous sessions for context

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Work through Tasks 1-5 in order.

### Step 4: Update Chain Log
In `notes_for_next`, include:
- Which pytest commands work locally and which don't
- Required environment setup for Python tests
- MyPy baseline error count
- Any import/startup issues found and fixed

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
