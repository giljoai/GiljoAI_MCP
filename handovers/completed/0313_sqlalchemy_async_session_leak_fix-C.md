# Handover 0313: SQLAlchemy Async Session Leak Fix

**Date:** 2025-12-02
**Status:** Completed
**Priority:** Critical
**Scope:** Database session management, FastAPI dependency injection

---

## Summary

Fixed critical SQLAlchemy async session leaks causing `IllegalStateChangeError` and garbage collector warnings about non-checked-in connections. Root cause was multi-layered: GeneratorExit handling, double-nested context managers, improper dependency injection patterns, and missing cascade soft-delete for agent jobs.

---

## Problems Identified

1. **GeneratorExit not caught** - `GeneratorExit` is `BaseException`, not `Exception`, so `except Exception:` blocks missed it during FastAPI HTTPException scenarios
2. **Double-nested context managers** - `get_db_session` in dependencies wrapped `db_manager.get_session_async()`, causing race conditions during cleanup
3. **`test_session` pattern in production** - Endpoint dependencies passed `test_session=db` to services, breaking session lifecycle
4. **`anext()` session extraction** - `/api/auth/me` used `await anext(get_db_session(request))` instead of `Depends()`, leaking on every request
5. **Missing cascade soft-delete** - Agent jobs weren't cancelled when parent project was soft-deleted
6. **Health monitor queried deleted projects** - Stale job detection didn't filter out jobs from soft-deleted projects

---

## Files Modified

### Core Session Management
- **`src/giljo_mcp/database.py`** - Single-layer pattern with explicit GeneratorExit handling, `is_active` checks before close

### Auth Dependencies
- **`src/giljo_mcp/auth/dependencies.py`** - Simplified to use `db_manager.get_session_async()` directly without double-wrapping

### Endpoint Dependencies (removed test_session pattern)
- **`api/endpoints/projects/dependencies.py`**
- **`api/endpoints/agent_jobs/dependencies.py`**
- **`api/endpoints/templates/dependencies.py`**

### Auth Endpoint (root cause of persistent leak)
- **`api/endpoints/auth.py`** - Changed `/me` endpoint from `anext()` to `Depends(get_db_session)`

### Cascade Soft Delete
- **`src/giljo_mcp/services/project_service.py`** - Added code to cancel all agent jobs when project is deleted

### Health Monitor
- **`src/giljo_mcp/monitoring/agent_health_monitor.py`** - Added LEFT JOIN with Project table in 4 detection methods to filter jobs from deleted projects

---

## Key Code Changes

### database.py - GeneratorExit Handling
```python
@asynccontextmanager
async def get_session_async(self) -> AsyncSession:
    session = self.AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except GeneratorExit:
        # GeneratorExit is BaseException - raised by FastAPI HTTPException
        if hasattr(session, 'is_active') and session.is_active:
            try:
                await session.rollback()
            except Exception:
                pass
        raise
    except Exception:
        # ... rollback and re-raise
    finally:
        # Check is_active before close to prevent IllegalStateChangeError
        if hasattr(session, 'is_active') and session.is_active:
            await session.rollback()
        await session.close()
```

### auth.py - Fixed anext() Leak
```python
# BEFORE (leaked sessions on EVERY /me request):
async def get_me(request: Request):
    db = await anext(get_db_session(request))

# AFTER (proper DI lifecycle):
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
```

### project_service.py - Cascade Soft Delete
```python
# Cancel all agent jobs when project is soft-deleted
agent_jobs_stmt = select(MCPAgentJob).where(
    and_(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_key == tenant_key,
        MCPAgentJob.status.notin_(["completed", "failed", "cancelled"])
    )
)
# Sets status='cancelled', timestamps
```

---

## Tests Created

- **`tests/integration/test_session_generatorexit_behavior.py`** - 4 behavioral tests for GeneratorExit handling (all passing)

---

## Manual Cleanup Performed

Cancelled 2 orphaned stale jobs from old test projects:
- Job from "Very First Project" (waiting since 2025-12-02)
- Job from "Hello Patrik Test Project" (waiting since 2025-11-24)

---

## Verification

After fixes:
- No `IllegalStateChangeError` on startup
- No garbage collector warnings about non-checked-in connections
- No "stale jobs" message on initial health scan
- All 12 session tests passing

---

## Architecture Pattern Established

**Single-Layer Session Pattern:**
- Services create their own sessions via `db_manager.get_session_async()`
- FastAPI `Depends(get_db_session)` for endpoint injection
- Never use `anext()` to manually extract async generators
- `test_session` parameter is ONLY for unit tests, not production endpoints

**Soft Delete Cascade:**
- Parent soft-delete must explicitly cancel/soft-delete children
- SQLAlchemy cascade only works for hard deletes
- Health monitors must LEFT JOIN to filter deleted parents
