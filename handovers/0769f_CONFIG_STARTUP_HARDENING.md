# 0769f: Config Consolidation & Startup Hardening

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 6 of 7
**Branch:** `feature/0769-quality-sprint`
**Priority:** MEDIUM — fragility reduction
**Estimated Time:** 2 hours

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md` (sections F3, F4, F9)
- **Project rules:** `CLAUDE.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

The fragility analysis found a dual config subsystem (ConfigManager vs _config_io, both used in production with inconsistent behavior for env vars) and an all-or-nothing startup sequence where optional component failures crash the entire application.

---

## Scope

### Task 1: Consolidate Config Reads

**Problem:** Two ways to read config exist:
- `get_config()` returns a typed `ConfigManager` singleton with env-var overrides (8 files use this)
- `read_config()` returns a raw dict from disk (11 files use this)
- 4 files bypass both with inline `yaml.safe_load`

A config value set via environment variable is visible to `get_config()` callers but NOT to `read_config()` callers.

**Fix:**
1. Audit all `read_config()` call sites. For each, determine if `get_config()` would work instead.
2. Replace production logic `read_config()` calls with `get_config()` where the typed access is available.
3. Keep `read_config()`/`write_config()` ONLY in:
   - Config CRUD endpoints that manage the YAML file directly
   - The ConfigManager initialization itself
   - Any bootstrapping code that runs before ConfigManager is available
4. Route the 4 inline `yaml.safe_load` sites through `_config_io.read_config()` at minimum (0769c may have already done this — check chain log).
5. Add a comment to `_config_io.py` documenting: "This module is for raw file I/O only. Production code should use get_config() from config_manager.py."

**Files to audit:**
- Find all with: `grep -r "read_config\(\)" src/ api/ --include="*.py"`
- Find all with: `grep -r "yaml.safe_load" src/ api/ --include="*.py"`

### Task 2: Classify Startup Phases

**File:** `api/app.py` (lifespan function, lines 154-233) and `api/startup/*.py`

**Problem:** 8-phase linear startup, all-or-nothing. If Phase 3 (event bus) fails, the REST API crashes even though it could function without real-time events.

**Fix:**
1. Read the startup sequence to understand all 8 phases and their dependencies
2. Classify each phase:
   - **Required** (app cannot function without): database, auth, tool_accessor
   - **Optional** (app can function in degraded mode): event bus, health monitor, silence detector
3. Wrap optional phases in try/except with:
   - Clear warning log: `logger.warning("Optional startup phase [X] failed: %s — running in degraded mode", e)`
   - Set a degraded-mode flag on the state object
4. Ensure the WebSocket broker pattern (already degrades gracefully per `core_services.py:62`) is followed by other optional components

### Task 3: Add Startup-Complete Guard

**File:** `api/app.py`, lines 194-197

**Problem:** `app.state.db_manager` and `app.state.websocket_manager` are set AFTER all initialization completes. If middleware accesses `app.state` during initialization, these will be `None`.

**Fix:** Add a startup-complete flag:
```python
app.state.startup_complete = False
# ... initialization ...
app.state.startup_complete = True
```

Add a check in critical middleware that accesses app.state to gracefully handle the case where startup is not yet complete.

---

## What NOT To Do

- Do NOT change config.yaml schema or format
- Do NOT change environment variable names
- Do NOT modify ConfigManager's public API
- Do NOT change the startup phase order (only error handling)
- Do NOT add new config sources

---

## Acceptance Criteria

- [ ] All production code uses `get_config()` (no `read_config()` in service/tool/endpoint code)
- [ ] `read_config()` usage limited to config CRUD endpoints and bootstrapping
- [ ] Zero inline `yaml.safe_load` in production code
- [ ] Optional startup phases wrapped with degraded-mode fallback
- [ ] Startup-complete guard added
- [ ] `ruff check src/ api/` passes with 0 issues
- [ ] Application starts normally (manual verification)

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives`
- Review 0769e's `notes_for_next`
- Check 0769c's notes for config bypass fixes already applied

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Work through Tasks 1-3.

### Step 4: Update Chain Log
In `notes_for_next`, include:
- Which `read_config()` sites were converted vs kept
- Whether degraded-mode flag was added and its name/location

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
