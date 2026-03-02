# Handover 0765g: Tenant Key Removal + Encapsulation

**Date:** 2026-03-02
**Priority:** HIGH (SaaS blocker)
**Estimated effort:** 6-8 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765g)
**Depends on:** 0765a (clean baseline), 0765f (tenant isolation patterns established)
**Blocks:** None (final in chain)

---

## Objective

Remove the hardcoded default tenant key (`tk_cyyOVf1H...`) from all 10 production locations and implement a proper first-run tenant provisioning flow. Also fix two encapsulation issues: prompts endpoint calling private methods and update_project bloat.

This is the final sprint in the chain and addresses the last remaining items blocking a 10/10 score.

**Score impact:** ~9.7 -> ~9.8-10.0
**SaaS impact:** Removes a critical SaaS blocker (hardcoded shared secret)

---

## Pre-Conditions

1. All prior handovers (0765a-f) complete
2. CSRF middleware enabled (0765f) — new endpoints must respect CSRF
3. Tenant isolation patterns established (0765f)
4. Read chain log for all predecessor notes and deviations

---

## Task 1: Remove Hardcoded Default Tenant Key [Proposal 4B] (~4-5 hours)

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

### 1.2 Product Decisions Required

Before implementing, the agent must resolve these design questions. If the user is unavailable, choose Option A for each:

**Q1: What happens when no tenant key is provided?**
- **Option A (Recommended):** Return 401 Unauthorized. Every request must have a tenant key.
- **Option B:** Auto-assign to a "default" tenant created during installation.

**Q2: First-run flow — how does the first tenant key get created?**
- **Option A (Recommended):** `install.py` generates a unique tenant key during installation, stores it in `config.yaml`, and configures the frontend to use it.
- **Option B:** The `/welcome` first-run wizard prompts the user to create an organization which generates a tenant key.

**Q3: Frontend — where does it get the tenant key?**
- **Option A (Recommended):** From the login response (server sends tenant key after authentication).
- **Option B:** From a config file served by the backend (`/api/v1/config/frontend`).

### 1.3 Implementation Plan (Based on Option A defaults)

#### Backend Changes

1. **`install.py`**: Generate a unique tenant key during installation. Store in `config.yaml` under `security.tenant_key`. Use `secrets.token_urlsafe(32)` prefixed with `tk_`.

2. **`api/dependencies.py`**: Remove ALL hardcoded fallbacks. When no `X-Tenant-Key` header is present:
   - For cookie-authenticated requests: extract tenant key from the user's JWT token (add `tenant_key` claim during login)
   - For API key requests: look up the tenant key associated with the API key
   - For unauthenticated requests: return 401

3. **`api/middleware/auth.py`**: Remove hardcoded fallback. Use the same resolution logic as dependencies.

4. **`api/endpoints/auth.py`**: During first admin creation, read tenant key from `config.yaml` instead of hardcoding.

#### Frontend Changes

5. **`frontend/src/config/api.js`**: Remove hardcoded default. Set `tenantKey: null` initially.

6. **`frontend/src/services/api.js`**: The Axios interceptor should get the tenant key from:
   - The auth store (populated after login from the JWT or login response)
   - If not authenticated, don't send the header

7. **`frontend/src/views/McpIntegration.vue`**: Get tenant key from the auth store instead of hardcoding.

### 1.4 Migration Safety

- **Existing installations:** The `install.py` upgrade path must:
  1. Detect if `config.yaml` has no `security.tenant_key`
  2. If so, write the EXISTING hardcoded key to the config file (preserves backward compatibility)
  3. Log a warning that the tenant key should be rotated

- **JWT changes:** If adding `tenant_key` to JWT claims, existing tokens won't have it. The middleware must handle missing claims gracefully during the transition period.

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
- **CRITICAL: Installation flow.** Every change to tenant key handling must be tested with `install.py`. Both fresh install and upgrade paths must work.
- **Frontend auth flow:** Login -> JWT -> tenant key extraction must work end-to-end.
- **MCP tools:** MCP connections use API keys which must be associated with a tenant. Verify the API key -> tenant key lookup works.
- **Tests:** Many tests may use the hardcoded key in fixtures. Search for the key across all test files and update fixtures.

### Prompts Encapsulation (Task 2)
- **Zero behavioral change** — same methods called, just through a public interface.

### update_project Refactor (Task 3)
- **Internal change only** — extract private helpers. All callers continue using `update_project()`.

---

## Testing Requirements

### Tenant Key
- `pytest tests/api/test_auth*.py -v` — all auth tests pass
- Test fresh install: `install.py` generates unique key and stores in config
- Test upgrade: existing installation gets migrated key
- Manual: login flow works end-to-end with new tenant key resolution

### Prompts
- `pytest tests/api/test_prompts*.py -v` (if exists)
- Manual: verify prompt generation endpoints return correct content

### update_project
- `pytest tests/services/test_project_service*.py -v`
- Verify WebSocket events still fire on project updates

### Full Suite
- `pytest tests/ -x -q` — full green
- `npm run build` — clean

---

## Success Criteria

- [ ] Hardcoded tenant key removed from all 10 production locations
- [ ] `install.py` generates unique tenant key and stores in config
- [ ] Upgrade path preserves existing key
- [ ] Frontend gets tenant key from auth state (not hardcoded)
- [ ] `ThinClientPromptGenerator.generate_implementation_prompt()` public method added
- [ ] `prompts.py` uses public method instead of private calls
- [ ] `update_project` refactored with 2 extracted helpers
- [ ] All tests pass, frontend builds clean
- [ ] Chain log updated: 0765g = `complete`, final_status = `complete`

---

## Completion Protocol (FINAL IN CHAIN)

1. Run full test suite and frontend build
2. Update chain log:
   - Set 0765g status to `complete`
   - Set `final_status` to `complete`
   - Write `chain_summary` summarizing the entire 0765 series
3. Write completion summary to THIS handover (max 400 words)
4. Commit: `cleanup(0765g): Remove hardcoded tenant key, fix encapsulation, refactor update_project`
5. **Final verification:** Run the code quality audit prompt (`handovers/Code_quality_prompt.md`) to verify 10/10 score
6. If score achieved: Tag the branch for the user's review
