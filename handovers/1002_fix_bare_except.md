# Handover 1002: Fix Bare Except Clause

**Date**: 2025-12-18
**Ticket**: 1002
**Parent**: 1000 (Greptile Remediation)
**Status**: Pending
**Risk**: VERY LOW
**Tier**: 1 (Auto-Execute)
**Effort**: 1 hour

---

## Mission

Replace bare `except:` clause with proper exception handling and logging in the statistics endpoint health check.

## Context

**Issue**: Bare `except:` clause on line 508 of `api/endpoints/statistics.py` catches all exceptions without logging, making debugging difficult.

**Impact**:
- Silently swallows database errors during health checks
- No visibility into why health check failed
- Violates Python best practices (PEP 8)

**Remedy**: Replace with `except Exception:` and add proper logging.

---

## Files to Modify

- `api/endpoints/statistics.py` (line 508)

---

## Pre-Implementation Research

1. ✅ Read the function containing the bare except
2. ✅ Verify no other bare excepts in the file
3. ✅ Check if logger is already imported

---

## Current Code (Line 508)

```python
try:
    async with state.db_manager.get_session_async() as session:
        await session.execute(select(1))
    db_query_time = (time.time() - db_start) * 1000
except:
    db_query_time = -1
```

---

## Fixed Code

```python
try:
    async with state.db_manager.get_session_async() as session:
        await session.execute(select(1))
    db_query_time = (time.time() - db_start) * 1000
except Exception:
    logger.exception("Database health check failed")
    db_query_time = -1
```

**Changes**:
1. Replace bare `except:` with `except Exception:`
2. Add `logger.exception()` call for full traceback visibility
3. Preserve existing behavior (`db_query_time = -1` on failure)

---

## Implementation Steps

1. **Locate the bare except clause**
   - File: `api/endpoints/statistics.py`
   - Line: ~508
   - Function: Health check endpoint

2. **Verify logger import**
   - Check if `logger` is imported at top of file
   - If not present, add: `from src.giljo_mcp.logging_config import get_logger; logger = get_logger(__name__)`

3. **Apply the fix**
   - Replace bare `except:` with `except Exception:`
   - Add logging statement before `db_query_time = -1`

4. **Run verification tests** (see below)

---

## Verification

### Automated Tests
```bash
pytest tests/endpoints/test_statistics.py -v
```

### Manual Verification
1. **Health endpoint works normally**:
   ```bash
   curl http://localhost:7272/api/statistics/health
   ```
   Expected: Valid JSON response with `db_query_time` field

2. **Exception logging works**:
   - Stop PostgreSQL service temporarily
   - Make health check request
   - Verify logs show full exception traceback
   - Restart PostgreSQL

3. **Code quality check**:
   ```bash
   ruff check api/endpoints/statistics.py
   ```
   Expected: No warnings about bare except

---

## Cascade Risk

**None**. This change only adds logging; behavior is unchanged:
- Still returns `-1` on database failure
- Still performs health check the same way
- No changes to API response structure

---

## Success Criteria

- ✅ No bare except clauses in `statistics.py`
- ✅ Health endpoint returns valid response
- ✅ Exceptions are logged with full traceback
- ✅ Tests pass without modification
- ✅ Ruff/linting checks pass

---

## Notes

**Why `except Exception:` instead of specific exception?**
- Database errors can manifest as various exception types (connection errors, timeout errors, etc.)
- Using `Exception` catches all database-related failures while still allowing system exits and keyboard interrupts to propagate
- The `logger.exception()` call will log the full traceback, making the specific exception type visible

**Why not catch `BaseException`?**
- `BaseException` catches system exits, keyboard interrupts, etc.
- These should propagate up to allow graceful shutdown
- `Exception` is the correct base class for error handling

---

## Related Documentation

- Python Exception Hierarchy: [docs.python.org](https://docs.python.org/3/library/exceptions.html#exception-hierarchy)
- PEP 8 Programming Recommendations: Section on exception handling
- GiljoAI Logging Standards: `docs/LOGGING.md` (if exists)

---

## Execution Timeline

**Estimated**: 15 minutes
**Actual**: _[To be filled by implementer]_

**Breakdown**:
- Research: 5 minutes (verify logger import, locate exact line)
- Implementation: 5 minutes (apply fix)
- Verification: 5 minutes (run tests, manual check)
