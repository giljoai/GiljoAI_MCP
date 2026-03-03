# Handover 0765l: Full Remediation

**Date:** 2026-03-03
**Priority:** CRITICAL (security items)
**Estimated effort:** 2.5-3 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765l)
**Depends on:** 0765j (prior fixes landed), 0765k (audit findings)

---

## Objective

Fix all remaining findings from both independent audits (0765k Claude at 8.5/10 and 0765k external at 8.0/10). This covers security, dead code, bugs, tenant gaps, function splits, and eslint regression prevention.

**Target state:** All findings resolved, eslint warning budget locked, tests passing, frontend clean.

---

## Pre-Conditions

1. Read `handovers/0765k_reaudit.md` — Claude audit findings (scroll to Completion Summary)
2. Read `handovers/0765k_external_audit.md` — External audit findings
3. Read `prompts/0765_chain/chain_log.json` — verify 0765k = complete
4. Baseline: 1453 passed, 0 skipped, 0 failed

---

## Bucket 1: SECURITY Fixes (~30 min)

### S1: Hardcoded JWT fallback secret
**File:** `api/endpoints/mcp_installer.py:37`
**Problem:** Hardcoded fallback JWT secret for installer token generation
**Fix:** Generate a random secret at startup using `secrets.token_urlsafe(32)`. Never hardcode a JWT secret.

### S2: Unauthenticated network endpoints
**File:** `api/endpoints/network.py:47,100`
**Problem:** `/detect-ip` and `/adapters` endpoints have no authentication
**Fix:** Add `Depends(get_current_active_user)` to both endpoint signatures

### S3: Username enumeration
**File:** `api/endpoints/auth_pin_recovery.py:176`
**Problem:** `check_first_login` returns 404 for non-existent users, allowing enumeration
**Fix:** Return a generic response regardless of whether user exists (same shape, same status code)

### S4: Committed API key material
**File:** `api_keys.json`
**Problem:** API key-like credentials committed to repo
**Fix:** Verify what this file is. If test data, add to `.gitignore`. If real keys, remove from tracking with `git rm --cached`, add to `.gitignore`, and warn user to rotate.

### S5: Placeholder API key in endpoint
**File:** `api/endpoints/ai_tools.py:214`
**Problem:** Endpoint returns hardcoded placeholder API key to users
**Fix:** Remove the placeholder. Either generate a scoped key server-side or return an error indicating the user needs to configure their own key.

**After Bucket 1:** Run `pytest tests/ -x -q` — all must pass.

---

## Bucket 2: Bugs + Lint (~10 min)

### B1: Bare expression no-op
**File:** `src/giljo_mcp/services/message_service.py:375`
**Problem:** `messages[0]` as a bare expression — does nothing
**Fix:** Remove the line, or if it was meant to be a check, convert to a proper assertion/validation

### B2: Bare expression no-op
**File:** `src/giljo_mcp/tools/chunking.py:100`
**Problem:** `content[search_start:search_end]` as a bare expression — does nothing
**Fix:** Remove the line, or assign to a variable if the result was meant to be used

### B3: Unused ruff noqa
**File:** `api/endpoints/statistics.py:1`
**Problem:** `# ruff: noqa: A005` suppression no longer needed
**Fix:** Remove the comment

### B4: RUF005 style issue
**File:** `src/giljo_mcp/services/orchestration_service.py:650`
**Problem:** ruff RUF005 style suggestion
**Fix:** Apply the ruff-suggested fix

**After Bucket 2:** Run `ruff check src/ api/` — zero issues.

---

## Bucket 3: Tenant Isolation Gap (~15 min)

### T1: MCP session update/delete missing tenant filter
**File:** `api/endpoints/mcp_session.py:213,248`
**Problem:** `update_session_data()` and `delete_session()` resolve session by ID without tenant scoping
**Fix:** Thread `tenant_key` parameter into both methods, add tenant filter to queries. Follow the same pattern used in the `get_session()` fix from 0765j.

---

## Bucket 4: Dead Code Deletion (~30 min)

### D1: Dead test fixture files
**Files:**
- `tests/fixtures/e2e_closeout_fixtures.py` (~large)
- `tests/fixtures/vision_document_fixtures.py` (~large)
- `tests/helpers/test_factories.py`
- Dead re-exports in root `tests/conftest.py`
- Dead fixtures in `tests/helpers/mock_servers.py` (`mock_api_server`, `mock_websocket_server`)
**Verify:** Grep each fixture name across all test files. Check test function parameter names (pytest injection). Only delete if truly zero references.

### D2: Dead backend methods
**Files:**
- `src/giljo_mcp/tools/context.py` — `get_context_history()` (line ~259), `get_succession_context()` (line ~309)
- `src/giljo_mcp/colored_logger.py` — `create_filtered_logger()` (line ~197)
- Dead methods in `template_manager.py`, `AgentJobRepository` (verify with find_referencing_symbols)
**Verify:** Each method must have zero references before deletion.

### D3: Dead CSS/SCSS
**File:** `frontend/src/styles/agent-colors.scss:158-394`
**Problem:** ~240 lines of CSS utility classes never used by any Vue component
**Verify:** Grep each class name across all Vue files before deleting.

**File:** `frontend/src/styles/design-tokens.scss`
**Problem:** Dead SCSS token sections (agent status colors duplicated in agentColors.js)
**Verify:** Grep each token/variable name before deleting.

### D4: Dead frontend exports
**Files:**
- `frontend/src/config/constants.js` — dead exports
- `frontend/src/stores/tasks.js` — dead exports
- `frontend/src/services/api.js` — dead `API_CONFIG.ENDPOINTS` object
- `frontend/src/components/projects/LaunchTab.vue` — dead `canLaunchAgent` function
**Verify:** Grep each export name across all frontend src/ files before deleting.

---

## Bucket 5: Function Splits (~45 min)

Split ONLY these 3 functions — they are where SaaS features will land.

### F1: `create_app` (441 lines)
**File:** `api/app.py:209`
**Problem:** App factory configures everything in one massive function
**Fix:** Extract middleware setup, router registration, and event handlers into named helper functions. Keep `create_app` as the orchestrator that calls them.

### F2: `send_message` (439 lines)
**File:** `src/giljo_mcp/services/message_service.py:124`
**Problem:** Core messaging function handles validation, persistence, broadcasting, and side effects in one block
**Fix:** Extract validation, broadcast, and side-effect handling into private helper methods. Keep `send_message` as the coordinator.

### F3: `handle_tools_list` (485 lines)
**File:** `api/endpoints/mcp_http.py:298`
**Problem:** MCP tool listing handler is the largest function in the codebase
**Fix:** Extract tool category builders into separate methods. Keep `handle_tools_list` as the assembler.

**IMPORTANT:** These are behavioral no-ops — the functions must do exactly what they do today, just organized into smaller pieces. Run the full test suite after each split to verify zero regressions.

---

## Bucket 6: ESLint Warning Budget Lock (~10 min)

### E1: Add eslint max-warnings to pre-commit
**File:** `.pre-commit-config.yaml`
**Fix:** Add an eslint hook that runs `npx eslint src/ --max-warnings=124` (or whatever the current count is). This freezes the warning count — new code can't add warnings, but we don't force-fix existing ones.

Steps:
1. Run `npx eslint src/ --format compact 2>/dev/null | grep -c "warning"` in `frontend/` to get exact current count
2. Add pre-commit hook with that count as the budget
3. Verify hook passes on current code

---

## Cascading Impact Analysis

- **S1-S5:** Security fixes — surgical changes, no behavioral impact on happy path
- **B1-B4:** Bug fixes — removing dead lines and lint, zero behavioral change
- **T1:** Tenant filter — additive WHERE clause, no schema change
- **D1-D4:** Dead code deletion — verify before delete, zero runtime impact
- **F1-F3:** Function splits — behavioral no-ops, same code reorganized
- **E1:** Pre-commit addition — does not modify any source code

---

## Testing Requirements

After ALL buckets:
- `pytest tests/ -x -q` — all pass, zero skips, zero failures
- `ruff check src/ api/` — zero issues
- `npm run build` in frontend/ — clean
- New pre-commit eslint hook passes

---

## Success Criteria

- [ ] All 5 SECURITY items fixed
- [ ] All 4 bug/lint items fixed (ruff clean)
- [ ] MCP session tenant gap closed
- [ ] Dead code deleted (test fixtures, backend methods, CSS, frontend exports — all verified before deletion)
- [ ] 3 oversized functions split (create_app, send_message, handle_tools_list)
- [ ] ESLint warning budget locked in pre-commit
- [ ] All tests pass, frontend builds clean

---

## Commit Strategy

4 commits:
1. `security(0765l): Fix 5 security findings from dual audit`
2. `fix(0765l): Fix bugs, lint, and tenant isolation gap`
3. `cleanup(0765l): Remove dead code across backend, tests, and frontend`
4. `refactor(0765l): Split 3 oversized functions + lock eslint budget`

---

## Completion Protocol

1. Run full test suite and frontend build
2. Update chain log: set 0765l to `complete`
3. Write completion summary to THIS handover (max 300 words)
4. Report to user: items fixed, test counts, ready for re-audit
5. Do NOT spawn another terminal
