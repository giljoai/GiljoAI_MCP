# Handover 0495: Fix API Test Suite Hang (P0 Blocker)

**Date:** 2026-02-19
**Priority:** P0 (Blocks all API tests, blocks 0484)
**Status:** Completed
**Estimated Complexity:** 1-2 hours

## Problem

ALL tests under `tests/api/` hang indefinitely. The test suite collects tests but never executes them. This blocks:
- Handover 0484 (test fixture remediation)
- Handover 0489 (API/MCP cleanup)
- Any API-level testing or validation

## Root Cause (Fully Diagnosed)

**File:** `tests/api/conftest.py` lines 20-51

The `cleanup_api_test_data` fixture is `autouse=True, scope="function"` and runs TRUNCATE CASCADE on all 34 tables before every test. It hangs because:

1. **Stale PostgreSQL connections**: Previously killed test runs leave orphan connections on `giljo_mcp_test` that hold locks
2. **TRUNCATE requires exclusive lock**: Cannot proceed while any other connection holds a lock on the table
3. **Connection pool self-deadlock**: The `db_manager` fixture creates an async connection pool. The cleanup fixture opens a session from that pool, then TRUNCATE needs exclusive access - but the pool's other connections may hold locks
4. **Affects ALL tests/api/ tests**: Even pure Pydantic validation tests (like `test_users_category_validation.py`) that need zero DB access get this autouse fixture forced on them

**Evidence:**
- 71 stale connections found on first check, 25 more after a single killed test run
- Terminating stale connections via `pg_terminate_backend()` clears them but they re-accumulate
- Running with `--confcutdir=tests/api/endpoints` (skips parent conftest) makes ALL 11 validation tests pass in 1.5 seconds
- Manual simulation: hangs at the TRUNCATE step after successfully finding 34 table names

## Fix Options (Choose One)

### Option A: Replace TRUNCATE with DELETE (Recommended - Simplest)
```python
# DELETE doesn't need exclusive table lock (uses row-level locks instead)
for table_name in reversed(table_names):  # Reverse to respect FK order
    await session.execute(text(f"DELETE FROM {table_name}"))
```
- Pro: No lock contention, works with concurrent connections
- Con: Slightly slower than TRUNCATE on large tables (irrelevant for tests)
- Note: `session_replication_role = 'replica'` trick not needed with DELETE if done in FK order

### Option B: Terminate competing connections before TRUNCATE
```python
# Add before TRUNCATE loop:
await session.execute(text("""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = current_database()
    AND pid <> pg_backend_pid()
    AND state != 'active'
"""))
```
- Pro: Keeps TRUNCATE performance
- Con: May kill the db_manager's own pool connections, causing errors elsewhere

### Option C: Restructure to avoid autouse on non-DB tests
Make the fixture opt-in instead of autouse, or add a marker:
```python
@pytest_asyncio.fixture(scope="function")
async def clean_db(db_manager):
    # Same cleanup logic but NOT autouse
    ...

# Tests that need DB explicitly request it:
async def test_something(api_client, clean_db):
    ...
```
- Pro: Non-DB tests run instantly without touching PostgreSQL
- Con: Every DB test must add the fixture; easy to forget

### Option D: Hybrid (Recommended if time allows)
1. Use DELETE instead of TRUNCATE (Option A)
2. Add connection termination on fixture setup as safety net
3. Add proper `db_manager` cleanup in fixture teardown to prevent pool leaks

## Implementation

1. Apply chosen fix to `tests/api/conftest.py`
2. Verify: `python run_tests.py tests/api/endpoints/test_users_category_validation.py --no-cov --timeout 30` passes
3. Verify: `python run_tests.py tests/api/ --no-cov --timeout 30 --suite-timeout 120` runs without hanging
4. Clean up stale connections: `PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'giljo_mcp_test' AND pid <> pg_backend_pid();"`

## Testing

```bash
# Step 1: Clear stale connections first
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'giljo_mcp_test' AND pid <> pg_backend_pid();"

# Step 2: Run the previously-hanging test
python run_tests.py tests/api/endpoints/test_users_category_validation.py --no-cov --timeout 30

# Step 3: Run broader API tests
python run_tests.py tests/api/ --no-cov --timeout 30 --suite-timeout 120

# Step 4: Verify non-API tests still pass
python run_tests.py tests/unit/ tests/services/ --no-cov --timeout 30
```

## Files to Modify

- `tests/api/conftest.py` (primary - cleanup_api_test_data fixture)

## Database Info

- Test database: `giljo_mcp_test` on localhost:5432
- Credentials: postgres / 4010
- psql path: `"/c/Program Files/PostgreSQL/17/bin/psql.exe"`
- 34 tables in test database

## Rollback

Single file change: `git checkout master -- tests/api/conftest.py`

---

## Implementation Summary

### 2026-02-18 - Completed
**Implementation commit:** `d48beecb` - "fix: replace TRUNCATE CASCADE with DELETE to prevent API test hangs (Handover 0495)"
**Fix chosen:** Option A (DELETE) + fixture restructuring

**What was done:**
- Replaced autouse TRUNCATE CASCADE with opt-in DELETE in FK-reverse order
- Overrode parent conftest autouse fixtures (`setup_agent_coordination`, `setup_project_tools`, `setup_context_module`) as no-ops to prevent transaction deadlocks
- Fixed `admin_user` fixture: `flush()+expunge()` instead of `commit()+refresh()`
- Rewrote `test_admin_fixtures.py` as pure unit tests (no DB dependency)

**Files modified (2):**
- `tests/api/conftest.py`
- `tests/api/test_admin_fixtures.py`

**Impact:** 20/20 API tests pass in 1.77s (was infinite hang). Net 0 lines changed (120 added, 120 removed).
