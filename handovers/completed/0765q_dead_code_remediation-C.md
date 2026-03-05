# Handover: 0765q — Dead Code Remediation

## Context
The 0765n audit (8.5/10) found ~1,800 lines of verified dead code across backend, tests, and frontend. Your job is to delete it all and lower the eslint warning budget.

## Dead Code Inventory (from 0765n audit report)

### Backend — 16 dead methods (~650-700 lines)
Delete these methods (all verified zero references):

| File | Symbol | ~Lines |
|------|--------|--------|
| `src/giljo_mcp/config_manager.py:948-1232` | `populate_config_data()` + 7 helper functions | ~284 |
| `src/giljo_mcp/template_cache.py` | `invalidate_all()`, `get_cache_stats()`, `reset_stats()` | ~70 |
| `src/giljo_mcp/template_manager.py` | `extract_variables()`, `get_template_manager()` | ~30 |
| `src/giljo_mcp/tools/chunking.py` | `chunk_multiple_documents()`, `calculate_content_hash()` | ~75 |
| `src/giljo_mcp/services/product_service.py` | `validate_project_path()` | ~51 |
| `src/giljo_mcp/database.py` | `get_tenant_session()`, `validate_tenant_key()`, `generate_tenant_key()` | ~40 |
| `src/giljo_mcp/exceptions.py` | `create_error_from_exception()` | ~30 |
| `src/giljo_mcp/network_detector.py` | `format_serving_address()` | ~7 |
| `src/giljo_mcp/api_key_utils.py` | `validate_api_key_format()` | ~25 |

**CRITICAL**: Before deleting, verify each method truly has zero references using `grep` or `find_referencing_symbols`. The 0725 audit had 75% false positives — do NOT blindly delete.

### Tests — 3 dead helper files (~1,089 lines)
Delete entire files (verified zero imports):

| File | Lines |
|------|-------|
| `tests/helpers/async_helpers.py` | 168 |
| `tests/helpers/tenant_helpers.py` | 574 |
| `tests/helpers/websocket_test_utils.py` | 347 |

Also:
- `tests/unit/conftest.py:119-159` — 3 dead fixtures (`mock_db_session`, `test_user`, `mock_config`)
- `tests/conftest.py:32-33` — 2 dead base_fixtures imports (`test_agent_jobs`, `test_messages`)

### Frontend — Dead exports (~15 lines)
- `frontend/src/utils/immutableHelpers.js:12` — `immutableMapDelete`
- `frontend/src/config/agentColors.js:98` — `getAgentBadgeId`
- `frontend/src/config/constants.js:30,36` — `AGENT_HASH_PALETTE`, `AGENT_FALLBACK_COLOR`
- `frontend/src/config/websocketEventRouter.js` — 3 unnecessary exports

### Frontend — Dead Vue variables (75+ across 25 files)
The audit found 75+ dead variables. Focus on the top offenders:
- `ProductsView.vue` — 27 dead symbols
- `TemplateManager.vue` — 8 dead symbols
- `LaunchTab.vue` — 7 dead symbols
- Remaining ~33 across ~20 files

**Approach for Vue dead vars**: Run eslint and grep for `no-unused-vars` warnings. Remove the dead variables and their imports. After cleanup, update the eslint budget in `.pre-commit-config.yaml` to the new lower count.

## Commit Strategy
- Commit 1: `cleanup(0765q): Delete dead backend methods (~650 lines)`
- Commit 2: `cleanup(0765q): Delete dead test helpers and fixtures (~1,100 lines)`
- Commit 3: `cleanup(0765q): Remove dead frontend exports and Vue variables`
- Commit 4: `ci(0765q): Lower eslint warning budget to match cleaned state`

## Verification
After each commit:
- `python -m pytest tests/ -x -q --tb=short` — 1453 passed, 0 skipped
- `python -m ruff check src/ api/` — 0 issues
- `npm run build` (in frontend/) — builds clean

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0765_chain/chain_log.json`
- Verify previous sessions completed
- Check for any blockers

### Step 2: Mark Session Started
Update your session entry: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Tasks
Use subagents to preserve context budget:

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Backend dead code verification + deletion | `deep-researcher` | Verify zero refs, then delete |
| Test helper deletion + fixture cleanup | `backend-tester` | Delete files, verify tests pass |
| Frontend dead exports + Vue variable cleanup | `frontend-tester` | Remove dead vars, run eslint |

### Step 4: Update Chain Log
Update your session with results, then set status to `complete`.

### Step 5: Done
Do NOT spawn another terminal. Report completion via chain log.
