# Kickoff: Handover 0703 - Auth & Logging Cleanup

**Series:** 0700 Code Cleanup Series
**Handover:** 0703
**Risk Level:** LOW-MEDIUM
**Estimated Effort:** 1.5-2 hours
**Date:** 2026-02-05

---

## Mission Statement

Remove duplicate/orphan middleware files and clean up logging patterns. **DELETE ~454 lines** of legacy code.

**WARNING:** Do NOT modify high-risk files with many dependents.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0703_auth_logging_cleanup.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
4. **Dependency Analysis**: `handovers/0700_series/dependency_analysis.json`

---

## HIGH-RISK FILES - DO NOT MODIFY

These files have 20+ dependents. Changes could break many things:

| File | Dependents | Action |
|------|------------|--------|
| `src/giljo_mcp/auth/dependencies.py` | 47 | **DO NOT TOUCH** |
| `api/dependencies.py` | 26 | **DO NOT TOUCH** |

---

## Tasks (from spec)

### Task 1: Delete Orphan rate_limit.py (HIGH PRIORITY)

**File:** `api/middleware/rate_limit.py` (194 lines)

This is an ORPHAN - duplicate of the active `rate_limiter.py`.

**Steps:**
1. Verify orphan status: `grep -rn "from api.middleware.rate_limit import" src/ api/`
2. Check test imports: `grep -rn "rate_limit" tests/`
3. If only test imports, update tests to use `rate_limiter` instead
4. DELETE `api/middleware/rate_limit.py`

### Task 2: Delete Legacy middleware.py (HIGH PRIORITY)

**File:** `api/middleware.py` (260 lines)

This contains older implementations that are duplicated in `api/middleware/` directory.

**Steps:**
1. Verify no direct imports: `grep -rn "from api.middleware import" src/ api/ tests/`
2. Verify no `from api import middleware` patterns
3. If safe, DELETE `api/middleware.py`

### Task 3: Document Logging Patterns (LOW PRIORITY)

Three logging patterns exist in codebase:
1. Standard: `import logging; logger = logging.getLogger(__name__)`
2. Structured: `from giljo_mcp.logging import get_logger, ErrorCode`
3. Source-prefixed: `from src.giljo_mcp.logging import get_logger`

**Action:**
- Do NOT refactor all logging (too risky, too much churn)
- Document the patterns in spec file
- Recommend structured logging for new auth/critical code

---

## Verification

```bash
# Verify deletions
ls api/middleware/rate_limit.py 2>/dev/null || echo "rate_limit.py DELETED"
ls api/middleware.py 2>/dev/null || echo "middleware.py DELETED"

# Verify API still imports
python -c "from api.app import app; print('API imports OK')"

# Verify middleware directory still works
python -c "from api.middleware.rate_limiter import RateLimiter; print('RateLimiter OK')"

# Run quick test if any exist for middleware
pytest tests/middleware/ -v -x 2>/dev/null || echo "No middleware tests"
```

---

## Communication

Write completion entry to `handovers/0700_series/comms_log.json`:

```json
{
  "id": "0703-complete-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0703",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Auth & Logging cleanup complete",
  "message": "Deleted orphan middleware files. ~454 lines removed. Logging patterns documented but not refactored (too risky).",
  "files_affected": ["[list]"],
  "action_required": false,
  "context": {
    "files_deleted": [
      "api/middleware/rate_limit.py",
      "api/middleware.py"
    ],
    "lines_removed": 454,
    "high_risk_files_preserved": [
      "src/giljo_mcp/auth/dependencies.py",
      "api/dependencies.py"
    ]
  }
}
```

---

## Success Criteria

- [ ] `api/middleware/rate_limit.py` DELETED (194 lines)
- [ ] `api/middleware.py` DELETED (260 lines)
- [ ] Any test imports updated to use `rate_limiter`
- [ ] API still starts: `python -c "from api.app import app"`
- [ ] High-risk files NOT modified
- [ ] comms_log.json entry written
- [ ] Changes committed

---

## Commit Message Template

```
cleanup(0703): Delete orphan middleware files

Removed duplicate/legacy middleware implementations.
~454 lines of dead code deleted.

Changes:
- Deleted api/middleware/rate_limit.py (194 lines) - orphan duplicate
- Deleted api/middleware.py (260 lines) - legacy, replaced by api/middleware/
- Updated test imports from rate_limit to rate_limiter (if any)

Preserved (high-risk, many dependents):
- src/giljo_mcp/auth/dependencies.py (47 dependents)
- api/dependencies.py (26 dependents)

Verification:
- API imports successfully
- RateLimiter middleware works

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
