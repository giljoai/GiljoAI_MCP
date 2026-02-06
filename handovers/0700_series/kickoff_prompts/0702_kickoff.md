# Kickoff: Handover 0702 - Utils & Config Cleanup

**Series:** 0700 Code Cleanup Series
**Handover:** 0702
**Risk Level:** LOW
**Estimated Effort:** 2-3 hours
**Date:** 2026-02-05

---

## Mission Statement

Clean up utility functions and config handling. Remove orphan modules, add DEPRECATED markers to legacy aliases, resolve naming collisions.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0702_utils_config_cleanup.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
4. **Dependency Analysis**: `handovers/0700_series/dependency_analysis.json`

---

## Tasks (from spec)

### Task 1: DELETE Legacy Config Aliases (CRITICAL)

**File:** `src/giljo_mcp/config_manager.py`

**PURGE these legacy aliases - there is no v4.0, we are shipping v1.0 clean:**

**DatabaseConfig (6 aliases):**
- `pg_host`, `pg_port`, `pg_database`, `pg_user`, `pg_password`, `pg_min_connections`

**AgentConfig (3 aliases):**
- `max_per_project`, `context_limit`, `handoff_threshold`

**MessageConfig (3 aliases):**
- `batch_size`, `retry_attempts`, `retry_delay`

**TenantConfig (3 aliases):**
- `enabled`, `default_key`, `isolation_strict`

**FeatureFlags (1 alias):**
- `websocket_updates`

**Steps:**
1. Search for callers: `grep -rn "pg_host\|pg_port\|max_per_project\|batch_size" src/ api/ tests/`
2. Update any callers to use the new property names (host, port, etc.)
3. DELETE the @property alias methods entirely
4. Verify config still loads

### Task 2: Resolve PathResolver Naming Collision (HIGH)

Two files with similar names:
- `src/giljo_mcp/discovery.py` - PathResolver class (ACTIVE, used by context.py)
- `src/giljo_mcp/utils/path_resolver.py` - path_resolver functions (ORPHAN-ish)

**Action:**
1. Check if `utils/path_resolver.py` is used anywhere besides tests
2. If orphan, mark for deletion or rename to avoid confusion
3. If used, rename one to distinguish purpose

### Task 3: Evaluate download_utils.py for Deletion (MEDIUM)

**File:** `src/giljo_mcp/tools/download_utils.py`

- Research shows zero production imports
- Only referenced in historical REFACTORING_SUMMARY.md

**Action:**
1. Verify with grep: `grep -rn "download_utils" src/ api/`
2. If truly orphan, DELETE the file
3. If used, document where

### Task 4: Evaluate task_helpers.py (MEDIUM)

**File:** `src/giljo_mcp/api_helpers/task_helpers.py`

- Low usage (only test file found)

**Action:**
1. Verify usage: `grep -rn "task_helpers" src/ api/ tests/`
2. If only test usage, consider if tests are valid or also orphaned
3. Document decision

---

## Verification

```bash
# Verify legacy aliases DELETED (should return 0)
grep -n "def pg_host\|def pg_port\|def max_per_project\|def batch_size" src/giljo_mcp/config_manager.py | wc -l
# Expected: 0 (all deleted)

# Verify no callers use old names (should return 0 or only comments)
grep -rn "\.pg_host\|\.pg_port\|\.max_per_project" src/ api/ | grep -v "#" | wc -l

# Verify orphan modules handled
ls -la src/giljo_mcp/tools/download_utils.py 2>/dev/null || echo "Deleted"

# Config still loads
python -c "from src.giljo_mcp.config_manager import get_config; print('Config OK')"
```

---

## Communication

Write completion entry to `handovers/0700_series/comms_log.json`:

```json
{
  "id": "0702-complete-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0702",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Utils & Config cleanup complete",
  "message": "[Summary of changes]",
  "files_affected": ["[list]"],
  "action_required": false,
  "context": {
    "legacy_aliases_deleted": 16,
    "callers_updated": "[COUNT]",
    "files_deleted": ["[list if any]"],
    "lines_removed": "[COUNT]"
  }
}
```

---

## Success Criteria

- [ ] 16 legacy config aliases DELETED (not marked - DELETED)
- [ ] Any callers updated to use new property names
- [ ] PathResolver naming collision resolved or documented
- [ ] download_utils.py evaluated (deleted if orphan)
- [ ] task_helpers.py evaluated
- [ ] Config still loads: `get_config()` works
- [ ] comms_log.json entry written
- [ ] Changes committed

---

## Commit Message Template

```
cleanup(0702): Delete legacy config aliases and orphan utils

Purged 16 legacy property aliases from config_manager.py.
No v4.0 migration needed - shipping clean v1.0.

Changes:
- DELETED DatabaseConfig aliases (pg_host, pg_port, etc.) - 6 removed
- DELETED AgentConfig aliases (max_per_project, etc.) - 3 removed
- DELETED MessageConfig aliases (batch_size, etc.) - 3 removed
- DELETED TenantConfig aliases (enabled, etc.) - 3 removed
- DELETED FeatureFlags aliases (websocket_updates) - 1 removed
- Updated X callers to use new property names
- [Deleted download_utils.py if applicable]
- [Resolved PathResolver naming if applicable]

Verification:
- Config loads successfully
- All callers use canonical property names

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
