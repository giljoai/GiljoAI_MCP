# 0765n Post-Remediation Re-Audit Report (Third Independent Audit — Subagent-Enhanced)

**Date:** 2026-03-03
**Branch:** `0760-perfect-score`
**Auditor:** Agent 0765n (fresh session, zero prior context, 5 parallel deep-researcher subagents)
**Predecessor:** 0765k scored 8.0/10, 0765l remediated all priority findings
**Note:** This report supersedes the earlier 0765n single-agent audit (9.35/10). This audit used 5 parallel deep-researcher subagents for exhaustive coverage and found substantially more dead code.

---

## Fix Verification: 13/14 VERIFIED

| # | Fix | Status |
|---|-----|--------|
| S1 | JWT secret ephemeral (generated at startup) | VERIFIED |
| S2 | Network endpoints `/detect-ip`, `/adapters` require auth | VERIFIED |
| S3 | Username enumeration unified error response | VERIFIED |
| S4 | api_keys.json in .gitignore, untracked | VERIFIED |
| S5 | Placeholder API key replaced with config lookup | VERIFIED |
| B1-B2 | Bare expression no-ops removed | VERIFIED |
| B3 | Unused noqa A005 in statistics.py | NOT REMOVED (intentional — pre-commit ruff v0.9.1 needs it) |
| B4 | RUF005 unpacking fix | VERIFIED |
| T1 | MCP session update/delete tenant-scoped | VERIFIED |
| D1-D4 | ~2,353 lines dead code removed (14 files) | VERIFIED |
| F1-F3 | 3 functions split into helpers/builders | VERIFIED |
| E1 | eslint warning budget hook (max-warnings=124) | VERIFIED |

Zero regressions from 0765l fixes.

---

## Per-Dimension Rubric Scores

### 1. Lint Cleanliness: 0.9/1.0
- `ruff check src/ api/` reports 1 issue: RUF100 unused noqa directive in `statistics.py:1`
- Intentionally kept by 0765l (pre-commit ruff v0.9.1 requires A005 suppression, CLI ruff doesn't)
- Deduction: -0.1 for version skew artifact

### 2. Dead Code Density: 0.6/1.0

**Backend — 16 dead methods, ~650-700 lines (all verified with zero references):**

| File | Symbol | Lines |
|------|--------|-------|
| config_manager.py:948-1232 | `populate_config_data()` + 7 helper functions | ~284 |
| template_cache.py | `invalidate_all()`, `get_cache_stats()`, `reset_stats()` | ~70 |
| template_manager.py | `extract_variables()`, `get_template_manager()` | ~30 |
| chunking.py | `chunk_multiple_documents()`, `calculate_content_hash()` | ~75 |
| product_service.py | `validate_project_path()` | ~51 |
| database.py | `get_tenant_session()`, `validate_tenant_key()`, `generate_tenant_key()` | ~40 |
| exceptions.py | `create_error_from_exception()` | ~30 |
| network_detector.py | `format_serving_address()` | ~7 |
| api_key_utils.py | `validate_api_key_format()` | ~25 |

**Tests — 3 dead helper files, ~1,089 lines:**

| File | Lines | Issue |
|------|-------|-------|
| tests/helpers/async_helpers.py | 168 | Zero imports anywhere |
| tests/helpers/tenant_helpers.py | 574 | Zero imports, stale model references |
| tests/helpers/websocket_test_utils.py | 347 | Zero imports anywhere |
| tests/unit/conftest.py:119-159 | ~40 | 3 dead fixtures (mock_db_session, test_user, mock_config) |
| tests/conftest.py:32-33 | ~4 | 2 dead base_fixtures imports (test_agent_jobs, test_messages) |

**Frontend — 7 dead exports:**
- `immutableHelpers.js:12` — `immutableMapDelete`
- `agentColors.js:98` — `getAgentBadgeId`
- `constants.js:30,36` — `AGENT_HASH_PALETTE`, `AGENT_FALLBACK_COLOR`
- `websocketEventRouter.js` — 3 unnecessary exports

**Total dead code: ~1,800+ lines.** Deduction: -0.4

### 3. Pattern Compliance: 1.0/1.0
- Zero dict-return regressions in services or endpoints
- Zero bare expressions
- Config access via ConfigManager throughout
- Exception-based error handling post-0480/0730

### 4. Test Health: 0.9/1.0
- 1453 passed, 0 skipped, 0 failed
- Zero broken imports from 0765l removals
- 1 remaining skip (documentation-only class, intentional/harmless)
- Stale `generate_message_data()` in base_fixtures (dead fields: `from_agent`, `to_agent`, status `waiting`)
- Deduction: -0.1 for dead test infrastructure

### 5. Frontend Hygiene: 0.5/1.0
- **124 eslint warnings at budget limit**
- 75+ production dead variables across 25+ Vue files
- Top offenders: ProductsView.vue (27 dead symbols), TemplateManager.vue (8), LaunchTab.vue (7)
- 8 dead CSS selectors across 6 files
- 3 console.log statements (non-error/warn)
- 2 v-html XSS warnings
- Hardcoded hex colors: CLEAN (design tokens fully migrated)
- Design token compliance: CLEAN (agentColors.js, statusConfig.js centralized)
- Deduction: -0.5 for extensive dead variable accumulation

### 6. Security Posture: 0.9/1.0
- JWT ephemeral, network endpoints authenticated, username enum fixed
- API keys untracked, CSRF enabled
- Tenant isolation comprehensive across all authenticated DB queries
- MEDIUM: `/api/v1/config/frontend` exposes default_tenant_key publicly (design trade-off)
- Deduction: -0.1

### 7. Exception Handling: 1.0/1.0
- All `except Exception` catches annotated with inline comments
- 10 narrowed to specific types in 0765d
- No unannotated broad catches found
- API layer uses HTTPException with global exception handlers

### 8. Code Organization: 0.8/1.0
- 0765l split the 3 worst offenders successfully
- 3 remaining oversized functions (all data/content-heavy, not logic):
  - `template_manager.py:_load_legacy_templates()` — 417 lines
  - `template_seeder.py:_get_default_templates_v103()` — 315 lines
  - `thin_prompt_generator.py:_build_claude_code_execution_prompt()` — 272 lines
- Deduction: -0.2

### 9. Documentation Accuracy: 0.9/1.0
- No stale references to removed features
- `api/endpoints/setup.py` router never mounted (dead endpoint, ~105 lines)
- Deduction: -0.1

### 10. Build & CI Health: 1.0/1.0
- Frontend builds clean
- Pre-commit hooks pass
- eslint budget locked at 124

---

## Overall Score: 8.5/10

| Dimension | Score |
|-----------|-------|
| 1. Lint cleanliness | 0.9 |
| 2. Dead code density | 0.6 |
| 3. Pattern compliance | 1.0 |
| 4. Test health | 0.9 |
| 5. Frontend hygiene | 0.5 |
| 6. Security posture | 0.9 |
| 7. Exception handling | 1.0 |
| 8. Code organization | 0.8 |
| 9. Documentation accuracy | 0.9 |
| 10. Build & CI health | 1.0 |
| **TOTAL** | **8.5/10** |

---

## Verdict: FAIL (target >= 9.5)

The codebase has improved significantly through the 0765 sprint (7.8 -> 8.5), but falls short of 9.5. The two dominant gaps:

1. **Dead code (~1,800+ lines)** — Backend utility functions, test helper files, frontend dead variables
2. **Frontend dead variables (75+ production warnings)** — ProductsView.vue alone has 27 dead symbols

---

## Prioritized Fix List

### Quick Wins (< 30 min, estimated +1.0 score impact)

| # | Action | File(s) | Lines Removed |
|---|--------|---------|---------------|
| 1 | Delete 3 dead test helper files | tests/helpers/{async,tenant,websocket}*.py | ~1,089 |
| 2 | Delete dead fixtures cluster | tests/unit/conftest.py:119-159 | ~40 |
| 3 | Remove dead base_fixtures imports | tests/conftest.py:32-33,44-45 | ~4 |
| 4 | Delete `populate_config_data` cluster | config_manager.py:948-1232 | ~284 |
| 5 | Delete 8 dead methods across 5 files | template_cache, chunking, database, etc. | ~200 |
| 6 | Delete 4 dead frontend exports | agentColors, constants, immutableHelpers | ~15 |

### Medium Effort (1-2 hrs, estimated +0.5 score impact)

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 7 | Clean ProductsView.vue dead variables | ProductsView.vue | -27 eslint warnings |
| 8 | Clean TemplateManager.vue dead variables | TemplateManager.vue | -8 warnings |
| 9 | Clean LaunchTab.vue dead variables | LaunchTab.vue | -7 warnings |
| 10 | Clean remaining dead vars (~20 files) | Various .vue files | -33 warnings |
| 11 | Remove 8 dead CSS selectors | 6 .vue files | Hygiene |
| 12 | Lower eslint budget to match cleaned state | .pre-commit-config.yaml | Lock gains |

### Lower Priority (no immediate score impact)

| # | Action | Note |
|---|--------|------|
| 13 | Extract template data to JSON/YAML | Reduces 2 oversized data functions |
| 14 | Remove dead setup.py router | ~105 lines dead endpoint |
| 15 | Sanitize `str(e)` in HTTP responses | Defense-in-depth, 25+ locations |
