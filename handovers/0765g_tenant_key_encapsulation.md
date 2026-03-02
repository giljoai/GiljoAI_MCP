# Handover 0765g: Tenant Key Removal + Encapsulation

**Date:** 2026-03-02 (updated 2026-03-03)
**Priority:** HIGH
**Estimated effort:** 4-5 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765g)
**Depends on:** 0765a (clean baseline), 0765f (tenant isolation patterns established)
**Blocks:** None (final in chain)

---

## Objective

Remove the hardcoded default tenant key (`tk_cyyOVf1H...`) from all 10 production locations and replace with config-based resolution. Also fix two encapsulation issues: prompts endpoint calling private methods and update_project bloat.

This is a **code quality cleanup only** — removing a hardcoded secret from source code. The full SaaS tenant provisioning architecture (JWT claims, org-based key generation, multi-org support) is out of scope and tracked separately in `handovers/0770_SAAS_EDITION_PROPOSAL.md`.

**Score impact:** ~9.7 -> ~9.8-10.0

---

## Pre-Conditions

1. All prior handovers (0765a-f) complete
2. CSRF middleware enabled (0765f) — new endpoints must respect CSRF
3. Tenant isolation patterns established (0765f)
4. Read chain log for all predecessor notes and deviations

---

## Scope Boundary (READ THIS)

**IN SCOPE (this handover):**
- Remove hardcoded `tk_cyyOVf1H...` from 10 source code locations
- Replace with config.yaml-based resolution
- install.py generates unique key during install, stores in config
- Upgrade path: migrate existing hardcoded key to config.yaml
- Frontend reads key from `/api/v1/config/frontend` endpoint (already exists)

**OUT OF SCOPE (future 0770 series):**
- Tenant key in JWT claims
- Generate key at first-admin/org creation
- Multi-org tenant provisioning
- Login response delivering tenant key
- install.py mode flags (community/enterprise/saas)
- Any auth flow changes beyond removing the hardcoded value

---

## Task 1: Remove Hardcoded Default Tenant Key [Proposal 4B] (~2-3 hours)

### 1.1 Current State — 10 Production Locations

The hardcoded key `tk_cyyOVf1H...` appears in:

**Backend (5 locations):**

| # | File | Context | Current Behavior |
|---|------|---------|-----------------|
| 1 | `api/dependencies.py` | Location 1 | Falls back to hardcoded key when no tenant header |
| 2 | `api/dependencies.py` | Location 2 | Same pattern, different code path |
| 3 | `api/dependencies.py` | Location 3 | Same pattern |
| 4 | `api/middleware/auth.py` | Middleware | Uses hardcoded key when tenant header missing |
| 5 | `api/endpoints/auth.py` | Login endpoint | Creates first admin with hardcoded tenant key |

**Frontend (4 locations):**

| # | File | Context |
|---|------|---------|
| 6 | `frontend/src/config/api.js` | Default config value |
| 7 | `frontend/src/services/api.js` | Axios interceptor default |
| 8 | `frontend/src/views/McpIntegration.vue` | Location 1 |
| 9 | `frontend/src/views/McpIntegration.vue` | Location 2 |

**Installer (1+ locations):**

| # | File | Context |
|---|------|---------|
| 10 | `install.py` | Initial setup generates/uses this key |

### 1.2 Implementation Plan — Config-Based Resolution

#### install.py Changes

1. **Fresh install:** Generate a unique tenant key using `secrets.token_urlsafe(32)` prefixed with `tk_`. Store in `config.yaml` under `security.tenant_key`.
2. **Upgrade path:** Detect if `config.yaml` has no `security.tenant_key`. If missing, write the EXISTING hardcoded key value to preserve backward compatibility. Log a warning that the key should be rotated.
3. Add a future-facing comment:
```python
# Future: install.py will support --mode=community|enterprise|saas
# See handovers/0770_SAAS_EDITION_PROPOSAL.md for roadmap
```

#### Backend Changes

4. **Create a config reader** (or extend existing config loading) that reads `security.tenant_key` from `config.yaml` at startup. Store as `settings.default_tenant_key`.
5. **`api/dependencies.py`**: Replace all 3 hardcoded fallbacks with `settings.default_tenant_key`.
6. **`api/middleware/auth.py`**: Replace hardcoded fallback with `settings.default_tenant_key`.
7. **`api/endpoints/auth.py`**: Read tenant key from config for first admin creation.

#### Frontend Changes

8. **`frontend/src/config/api.js`**: Remove hardcoded default. Read from the `/api/v1/config/frontend` endpoint (already serves tenant config).
9. **`frontend/src/services/api.js`**: Axios interceptor reads from config store instead of hardcoded value.
10. **`frontend/src/views/McpIntegration.vue`**: Same — read from config store.

### 1.3 Migration Safety

- **Existing installations:** Upgrade path writes the old key to config.yaml — zero breaking change.
- **No auth flow changes:** The tenant key resolution still works the same way (header or fallback). The only difference is WHERE the fallback value comes from (config file vs source code).
- **Tests:** Search for the hardcoded key string across all test files. Update test fixtures to read from config or use a test-specific key.

---

## Task 2: Fix Prompts Endpoint Encapsulation [Proposal 4D] (~1-2 hours)

### 2.1 Problem

**File:** `api/endpoints/prompts.py` lines ~601, 610

The endpoint calls private methods `_build_multi_terminal_orchestrator_prompt()` and `_build_claude_code_execution_prompt()` on `ThinClientPromptGenerator`. Underscored methods are internal APIs — endpoints should not call them directly.

### 2.2 Fix

Add a public method to `ThinClientPromptGenerator`:

**File:** `src/giljo_mcp/prompt_generation/thin_prompt_generator.py`

```python
def generate_implementation_prompt(self, prompt_type: str, **kwargs) -> str:
    """Generate an implementation prompt by type.

    Args:
        prompt_type: One of 'multi_terminal_orchestrator', 'claude_code_execution'
        **kwargs: Parameters passed to the underlying builder

    Returns:
        The generated prompt string
    """
    builders = {
        'multi_terminal_orchestrator': self._build_multi_terminal_orchestrator_prompt,
        'claude_code_execution': self._build_claude_code_execution_prompt,
    }
    builder = builders.get(prompt_type)
    if not builder:
        raise ValueError(f"Unknown prompt type: {prompt_type}")
    return builder(**kwargs)
```

Then update `prompts.py` to call the public method instead of the private ones.

---

## Task 3: Refactor update_project [Proposal 4E] (~1-2 hours)

### 3.1 Problem

**File:** `src/giljo_mcp/services/project_service.py` — `update_project` method

The method is 122 lines (90 without docstring) with 8 logical concerns mixed together. While it follows a standard CRUD pattern, it could be cleaner.

### 3.2 Fix — Extract Two Helpers

1. **Extract DTO construction** — the section that builds the update dict from incoming fields
2. **Extract WebSocket broadcast** — the section that broadcasts the update event

```python
def _build_project_update_dict(self, project, update_data):
    """Build the dictionary of fields to update on the project."""
    ...

def _broadcast_project_update(self, project, updated_fields):
    """Broadcast project update event via WebSocket."""
    ...
```

Keep `update_project` as the orchestrator that calls both helpers.

### 3.3 Scope Constraint

Do NOT over-refactor. The method works correctly. Extract only the two clearest concerns. The method should still be recognizable as a CRUD update.

---

## Cascading Impact Analysis

### Tenant Key Removal (Task 1)
- **Installation flow:** Both fresh install and upgrade must work. Test both paths.
- **No auth flow changes.** Same resolution logic, different source for the fallback value.
- **Tests:** Many tests may use the hardcoded key in fixtures. Update to read from config.
- **MCP tools:** MCP connections use API keys which already carry tenant association. No change needed.

### Prompts Encapsulation (Task 2)
- **Zero behavioral change** — same methods called, just through a public interface.

### update_project Refactor (Task 3)
- **Internal change only** — extract private helpers. All callers continue using `update_project()`.

---

## Testing Requirements

### Tenant Key
- `pytest tests/api/test_auth*.py -v` — all auth tests pass
- Verify no source file contains the hardcoded key string (grep confirmation)
- Verify config.yaml loading works at startup

### Prompts
- `pytest tests/api/test_prompts*.py -v` (if exists)

### update_project
- `pytest tests/services/test_project_service*.py -v`

### Full Suite
- `pytest tests/ -x -q` — full green
- `npm run build` — clean

---

## Success Criteria

- [ ] Hardcoded tenant key removed from all 10 production locations
- [ ] `install.py` generates unique tenant key and stores in config.yaml
- [ ] Upgrade path preserves existing key (backward compatible)
- [ ] Frontend reads tenant key from config endpoint (not hardcoded)
- [ ] Zero source files contain the hardcoded key string
- [ ] `ThinClientPromptGenerator.generate_implementation_prompt()` public method added
- [ ] `prompts.py` uses public method instead of private calls
- [ ] `update_project` refactored with 2 extracted helpers
- [ ] All tests pass, frontend builds clean
- [ ] Chain log updated: 0765g = `complete`, final_status = `complete`

---

## Completion Protocol

1. Run full test suite and frontend build
2. Update chain log: set 0765g status to `complete`
3. Write completion summary to THIS handover (max 400 words)
4. Commit: `cleanup(0765g): Remove hardcoded tenant key, fix encapsulation, refactor update_project`
5. Spawn 0765h (Skipped Test Resolution) — see `prompts/0765_chain/0765g_launch.md` for spawn command

---

## Completion Summary

**Status:** COMPLETE | **Date:** 2026-03-02 | **Commits:** 4

### Task 1: Tenant Key Removal (11 files, 80 insertions, 28 deletions)
Removed 14+ hardcoded occurrences of `tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd` from all production code. Backend: added `_get_default_tenant_key()` helper in `dependencies.py` (resolves from ConfigManager -> env var -> error), updated auth middleware, changed `RegisterUserRequest.tenant_key` default to None, added `default_tenant_key` to `/api/v1/config/frontend` response. Frontend: added `getDefaultTenantKey()` export to `api.js`, updated axios interceptor and McpIntegration.vue. Installers: both Windows and Linux installers now generate `tenant` section in config.yaml instead of hardcoding in .env template. Verified via `git grep`: zero hardcoded key instances remain.

### Task 2: Prompts Encapsulation (2 files)
Added `generate_implementation_prompt(prompt_type, **kwargs)` public method to `ThinClientPromptGenerator` as a routing method. Updated `prompts.py` endpoint to call the public method instead of directly invoking `_build_multi_terminal_orchestrator_prompt` and `_build_claude_code_execution_prompt` private methods.

### Task 3: update_project Refactor (2 files + 1 new test file, 19 tests)
Extracted `_apply_project_updates(project, updates)` for field validation/setattr and `_build_project_data(project)` static method for DTO construction from `update_project`. Added 19 unit tests covering both helpers.

### Verification
- Full test suite: 1441 passed, 342 skipped (19 new from Task 3)
- Ruff lint: all changed core files pass
- Frontend build: clean
- Pre-commit hooks: all pass
