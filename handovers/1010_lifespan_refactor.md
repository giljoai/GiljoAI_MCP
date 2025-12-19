# Handover 1010: Lifespan Refactor

**Date**: 2025-12-18
**Parent**: 1000 (Greptile Remediation)
**Status**: Pending
**Risk**: MEDIUM
**Tier**: 2 (User Approval Required)
**Effort**: 4 hours

---

## Mission

Extract `api/app.py` lifespan blocks into composable async functions for better testability, maintainability, and clarity. The current lifespan function is ~480 lines (lines 172-650) mixing initialization logic, background task definitions, and shutdown sequences. This refactor will:

1. Separate concerns into focused, testable modules
2. Make initialization order explicit through clear dependencies
3. Enable unit testing of individual startup components
4. Improve code organization and readability
5. Maintain backward compatibility (no behavior changes)

---

## Current Structure Analysis

### Lifespan Function Overview (api/app.py lines 172-650)

```
lifespan() - 480 lines total:
├── Database initialization (lines 172-211, ~40 lines)
├── Tenant manager initialization (lines 213-220, ~8 lines)
├── WebSocket manager initialization (lines 222-229, ~8 lines)
├── Tool accessor initialization (lines 231-242, ~12 lines)
├── Auth manager initialization (lines 244-269, ~26 lines)
├── WebSocket heartbeat task (lines 271-278, ~8 lines)
├── Event bus initialization (lines 280-317, ~38 lines)
├── Download token cleanup task (lines 320-348, ~29 lines)
├── API metrics sync task (lines 350-399, ~50 lines)
├── Health monitoring initialization (lines 401-451, ~51 lines)
├── Setup state validation (lines 455-501, ~47 lines)
├── Expired item purge task (lines 503-582, ~80 lines)
├── App state exposure (lines 584-591, ~8 lines)
└── Shutdown logic (lines 595-650, ~56 lines)
```

### Dependency Map

```
Initialization Order (CRITICAL - must be preserved):

1. Database (no dependencies)
   └── DatabaseManager created
       └── Tables created/verified
       └── SystemPromptService initialized

2. Tenant Manager (depends on: nothing - static methods)

3. WebSocket Manager (depends on: nothing)

4. Tool Accessor (depends on: DatabaseManager, TenantManager, WebSocketManager)

5. Auth Manager (depends on: config)
   └── API key loaded from environment

6. WebSocket Heartbeat Task (depends on: WebSocketManager)

7. Event Bus (depends on: WebSocketManager)
   └── WebSocketEventListener registered

8. Background Tasks (depend on: DatabaseManager):
   ├── Download Token Cleanup (every 15 minutes)
   ├── API Metrics Sync (every 5 minutes)
   └── Expired Item Purge (startup only)

9. Health Monitor (depends on: DatabaseManager, WebSocketManager, config)

10. Setup State Validation (depends on: DatabaseManager, config)

11. App State Exposure (depends on: all initialized)
```

### Key Characteristics to Preserve

1. **Logging Verbosity**: Detailed step-by-step logging for each initialization phase
2. **Error Handling**: Try/except blocks with specific error messages
3. **Graceful Degradation**: Some failures are logged as warnings, others raise
4. **Shutdown Sequence**: Cancel tasks → Stop health monitor → Close WebSockets → Close DB
5. **State References**: Background tasks stored to prevent garbage collection

---

## Target Structure

### New Module Layout

```
api/startup/
├── __init__.py              # Public exports
├── database.py              # init_database()
├── core_services.py         # init_core_services() - tenant, websocket, tool, auth
├── event_bus.py             # init_event_bus()
├── background_tasks.py      # init_background_tasks()
├── health_monitor.py        # init_health_monitor()
├── validation.py            # init_validation()
└── shutdown.py              # shutdown()
```

### Refactored Lifespan Function (api/app.py)

```python
from api.startup import (
    init_database,
    init_core_services,
    init_event_bus,
    init_background_tasks,
    init_health_monitor,
    init_validation,
    shutdown,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - orchestrates startup and shutdown"""
    state = AppState()

    logger.info("=" * 70)
    logger.info("STARTING GILJOAI MCP API INITIALIZATION")
    logger.info("=" * 70)

    # Phase 1: Database initialization (ALWAYS required)
    await init_database(state)

    # Phase 2: Core services (tenant, websocket, tool accessor, auth)
    await init_core_services(state)

    # Phase 3: Event bus and WebSocket listener
    await init_event_bus(state)

    # Phase 4: Background tasks (cleanup, metrics, purge)
    await init_background_tasks(state)

    # Phase 5: Health monitoring (optional - config-driven)
    await init_health_monitor(state)

    # Phase 6: Validation (setup state checking)
    await init_validation(state)

    # Expose state to app (for middleware/endpoint access)
    app.state.db_manager = state.db_manager
    app.state.websocket_manager = state.websocket_manager

    logger.info("=" * 70)
    logger.info("API STARTUP COMPLETE - ALL SYSTEMS INITIALIZED")
    logger.info("=" * 70)

    yield

    # Shutdown sequence
    await shutdown(state)
```

**Line count**: ~50 lines (down from ~480 lines)

---

## Implementation Plan

### Phase 1: Create Module Structure

**File**: `api/startup/__init__.py`
```python
"""
Startup and shutdown functions for GiljoAI MCP API.

This module provides composable initialization functions that replace
the monolithic lifespan function in api/app.py. Each function is:
- Independently testable
- Clearly documented with dependencies
- Error-handling consistent with original implementation
"""

from .database import init_database
from .core_services import init_core_services
from .event_bus import init_event_bus
from .background_tasks import init_background_tasks
from .health_monitor import init_health_monitor
from .validation import init_validation
from .shutdown import shutdown

__all__ = [
    "init_database",
    "init_core_services",
    "init_event_bus",
    "init_background_tasks",
    "init_health_monitor",
    "init_validation",
    "shutdown",
]
```

### Phase 2: Extract Database Initialization

**File**: `api/startup/database.py`

**Responsibility**: Initialize DatabaseManager and SystemPromptService

**Dependencies**: None (first in initialization chain)

**Extracted from**: Lines 172-211

**Key Logic**:
- Check for `DATABASE_URL` environment variable first
- Fall back to `config.database.get_connection_string()`
- Create `DatabaseManager(db_url, is_async=True)`
- Create tables with `create_tables_async()`
- Initialize `SystemPromptService(db_manager)`
- Comprehensive error handling and logging

**Function Signature**:
```python
async def init_database(state: AppState) -> None:
    """
    Initialize database connection and create tables.

    Args:
        state: Application state object to populate

    Raises:
        ValueError: If no database configuration found
        Exception: If database initialization fails

    Side Effects:
        - Sets state.db_manager (DatabaseManager instance)
        - Sets state.system_prompt_service (SystemPromptService instance)
        - Creates database tables if not exist
    """
```

### Phase 3: Extract Core Services

**File**: `api/startup/core_services.py`

**Responsibility**: Initialize TenantManager, WebSocketManager, ToolAccessor, AuthManager

**Dependencies**: DatabaseManager (must be initialized first)

**Extracted from**: Lines 213-269

**Key Logic**:
- TenantManager (static methods, no dependencies)
- WebSocketManager (standalone initialization)
- ToolAccessor (requires db_manager, tenant_manager, websocket_manager)
- AuthManager (requires config)
- Load API key from environment if available
- WebSocket heartbeat task creation

**Function Signature**:
```python
async def init_core_services(state: AppState) -> None:
    """
    Initialize core services: tenant manager, websocket manager, tool accessor, auth.

    Args:
        state: Application state object to populate

    Dependencies:
        - state.db_manager must be initialized

    Raises:
        Exception: If any core service fails to initialize

    Side Effects:
        - Sets state.tenant_manager (TenantManager instance)
        - Sets state.websocket_manager (WebSocketManager instance)
        - Sets state.tool_accessor (ToolAccessor instance)
        - Sets state.auth (AuthManager instance)
        - Sets state.heartbeat_task (asyncio.Task for WebSocket heartbeat)
        - Loads API key from environment if present
    """
```

### Phase 4: Extract Event Bus Initialization

**File**: `api/startup/event_bus.py`

**Responsibility**: Initialize EventBus and register WebSocketEventListener

**Dependencies**: WebSocketManager (must be initialized first)

**Extracted from**: Lines 280-317

**Key Logic**:
- Import EventBus and WebSocketEventListener
- Create EventBus instance
- Create and start WebSocketEventListener
- Extremely verbose logging (Handover 0111 Issue #1 debugging)

**Function Signature**:
```python
async def init_event_bus(state: AppState) -> None:
    """
    Initialize event bus and register WebSocket event listener.

    Args:
        state: Application state object to populate

    Dependencies:
        - state.websocket_manager must be initialized

    Raises:
        Exception: If event bus or listener fails to initialize

    Side Effects:
        - Sets state.event_bus (EventBus instance)
        - Registers WebSocketEventListener handlers

    Notes:
        - Uses verbose logging for debugging (Handover 0111)
    """
```

### Phase 5: Extract Background Tasks

**File**: `api/startup/background_tasks.py`

**Responsibility**: Create and start background tasks (cleanup, metrics, purge)

**Dependencies**: DatabaseManager, WebSocketManager

**Extracted from**: Lines 320-582

**Key Logic**:
- Download token cleanup task (every 15 minutes)
- API metrics sync task (every 5 minutes)
- Expired item purge (startup only - projects and products)
- Store task references to prevent garbage collection

**Function Signature**:
```python
async def init_background_tasks(state: AppState) -> None:
    """
    Initialize background tasks: cleanup, metrics sync, expired item purge.

    Args:
        state: Application state object to populate

    Dependencies:
        - state.db_manager must be initialized
        - state.tenant_manager must be initialized

    Raises:
        Exception: Errors are logged but don't prevent startup

    Side Effects:
        - Sets state.cleanup_task (download token cleanup)
        - Sets state.metrics_sync_task (API metrics sync)
        - Runs startup purge of expired deleted items

    Notes:
        - Cleanup task runs every 15 minutes
        - Metrics sync runs every 5 minutes
        - Purge runs once at startup (items deleted >10 days ago)
    """
```

### Phase 6: Extract Health Monitor

**File**: `api/startup/health_monitor.py`

**Responsibility**: Initialize and start AgentHealthMonitor service

**Dependencies**: DatabaseManager, WebSocketManager, config

**Extracted from**: Lines 401-451

**Key Logic**:
- Load `health_monitoring` config from YAML
- Only start if `enabled: true` in config
- Build HealthCheckConfig from config values
- Initialize and start AgentHealthMonitor

**Function Signature**:
```python
async def init_health_monitor(state: AppState) -> None:
    """
    Initialize agent health monitoring service.

    Args:
        state: Application state object to populate

    Dependencies:
        - state.db_manager must be initialized
        - state.websocket_manager must be initialized
        - state.config must be initialized

    Raises:
        Exception: Errors are logged but don't prevent startup

    Side Effects:
        - Sets state.health_monitor (AgentHealthMonitor instance)
        - Starts background monitoring task if enabled

    Notes:
        - Only starts if health_monitoring.enabled=true in config.yaml
        - Handover 0107 - agent health monitoring feature
    """
```

### Phase 7: Extract Validation

**File**: `api/startup/validation.py`

**Responsibility**: Validate setup state and version compatibility

**Dependencies**: DatabaseManager, config

**Extracted from**: Lines 455-501

**Key Logic**:
- Load current version from config.yaml
- Initialize SetupStateManager
- Check if migration required (version mismatch)
- Validate current state

**Function Signature**:
```python
async def init_validation(state: AppState) -> None:
    """
    Validate setup state and version compatibility.

    Args:
        state: Application state object to populate

    Dependencies:
        - state.db_manager must be initialized
        - state.config must be initialized

    Raises:
        Exception: Errors are logged but don't prevent startup

    Side Effects:
        - Logs warnings if migration needed or validation fails

    Notes:
        - Non-critical validation - failures don't crash startup
        - Checks version compatibility and setup state
    """
```

### Phase 8: Extract Shutdown Logic

**File**: `api/startup/shutdown.py`

**Responsibility**: Graceful shutdown of all services and tasks

**Dependencies**: All initialized state

**Extracted from**: Lines 595-650

**Key Logic**:
- Cancel background tasks (heartbeat, cleanup, metrics)
- Stop health monitoring gracefully
- Close all WebSocket connections
- Close database connection

**Function Signature**:
```python
async def shutdown(state: AppState) -> None:
    """
    Gracefully shutdown all services and background tasks.

    Args:
        state: Application state object with initialized services

    Raises:
        Exception: Errors are logged but don't prevent shutdown

    Side Effects:
        - Cancels all background tasks
        - Stops health monitor
        - Closes all WebSocket connections
        - Closes database connection

    Notes:
        - Errors during shutdown are logged but don't raise
        - Tasks are canceled and awaited to ensure cleanup
    """
```

### Phase 9: Update api/app.py

**Changes**:
1. Add import: `from api.startup import ...`
2. Replace entire lifespan function body with refactored version
3. Maintain exact same behavior (no functional changes)
4. Keep all logging levels identical

**Before** (lines 172-650, ~480 lines):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()

    # [~460 lines of initialization logic]

    yield

    # [~56 lines of shutdown logic]
```

**After** (~50 lines):
```python
from api.startup import (
    init_database,
    init_core_services,
    init_event_bus,
    init_background_tasks,
    init_health_monitor,
    init_validation,
    shutdown,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - orchestrates startup and shutdown"""
    state = AppState()

    logger.info("=" * 70)
    logger.info("STARTING GILJOAI MCP API INITIALIZATION")
    logger.info("=" * 70)

    # Phase 1: Database initialization (ALWAYS required)
    await init_database(state)

    # Phase 2: Core services (tenant, websocket, tool accessor, auth)
    await init_core_services(state)

    # Phase 3: Event bus and WebSocket listener
    await init_event_bus(state)

    # Phase 4: Background tasks (cleanup, metrics, purge)
    await init_background_tasks(state)

    # Phase 5: Health monitoring (optional - config-driven)
    await init_health_monitor(state)

    # Phase 6: Validation (setup state checking)
    await init_validation(state)

    # Expose state to app (for middleware/endpoint access)
    app.state.db_manager = state.db_manager
    app.state.websocket_manager = state.websocket_manager

    logger.info("=" * 70)
    logger.info("API STARTUP COMPLETE - ALL SYSTEMS INITIALIZED")
    logger.info("=" * 70)

    yield

    # Shutdown sequence
    await shutdown(state)
```

---

## Testing Strategy

### Unit Tests (New)

**File**: `tests/startup/test_database_init.py`
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.startup.database import init_database
from api.app import AppState


@pytest.mark.asyncio
async def test_init_database_success():
    """Test successful database initialization"""
    state = AppState()

    with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://localhost/test'}):
        with patch('api.startup.database.DatabaseManager') as MockDB:
            mock_db = AsyncMock()
            MockDB.return_value = mock_db

            await init_database(state)

            assert state.db_manager is not None
            mock_db.create_tables_async.assert_called_once()


@pytest.mark.asyncio
async def test_init_database_no_url_raises():
    """Test that missing database URL raises ValueError"""
    state = AppState()
    state.config.database = None

    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="Database URL not configured"):
            await init_database(state)
```

**File**: `tests/startup/test_core_services_init.py`
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.startup.core_services import init_core_services
from api.app import AppState


@pytest.mark.asyncio
async def test_init_core_services_success():
    """Test successful core services initialization"""
    state = AppState()
    state.db_manager = MagicMock()
    state.config = MagicMock()

    await init_core_services(state)

    assert state.tenant_manager is not None
    assert state.websocket_manager is not None
    assert state.tool_accessor is not None
    assert state.auth is not None
    assert state.heartbeat_task is not None
```

**File**: `tests/startup/test_shutdown.py`
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from api.startup.shutdown import shutdown
from api.app import AppState


@pytest.mark.asyncio
async def test_shutdown_cancels_tasks():
    """Test that shutdown cancels all background tasks"""
    state = AppState()

    # Create mock tasks
    state.heartbeat_task = asyncio.create_task(asyncio.sleep(100))
    state.cleanup_task = asyncio.create_task(asyncio.sleep(100))
    state.metrics_sync_task = asyncio.create_task(asyncio.sleep(100))

    # Mock database and health monitor
    state.db_manager = AsyncMock()
    state.health_monitor = AsyncMock()
    state.connections = {}

    await shutdown(state)

    # Verify tasks were canceled
    assert state.heartbeat_task.cancelled()
    assert state.cleanup_task.cancelled()
    assert state.metrics_sync_task.cancelled()

    # Verify cleanup methods called
    state.health_monitor.stop.assert_called_once()
    state.db_manager.close_async.assert_called_once()
```

### Integration Tests (Existing)

**Verify**:
- `tests/integration/test_api_startup.py` still passes
- Server starts successfully with refactored code
- All background tasks initialize correctly
- Shutdown is graceful (no hanging tasks)

**Run**:
```bash
pytest tests/integration/test_api_startup.py -v
```

### Manual Testing

1. **Start server**: `python startup.py --dev`
2. **Check logs**: Verify initialization order and completion messages
3. **Health check**: `curl http://localhost:7272/api/health`
4. **Graceful shutdown**: Ctrl+C, verify shutdown sequence in logs

---

## Risk Assessment

### Risk Level: MEDIUM

**Why Medium**:
- Changes core startup logic (critical path)
- Wrong initialization order can cause startup failures
- Background tasks must preserve exact behavior
- Shutdown sequence is sensitive to timing issues

**Mitigations**:
1. **Preserve Exact Behavior**: No functional changes, only code organization
2. **Extensive Testing**: Unit tests for each module + integration tests
3. **Clear Dependencies**: Explicit documentation of initialization order
4. **Incremental Testing**: Test each phase independently before integration
5. **Rollback Plan**: Keep original code in git history, easy to revert

### Cascade Risks

**If database init fails**:
- Server won't start (expected behavior - no change)
- Clear error message logged (preserved)

**If background task init fails**:
- Server continues (graceful degradation - preserved)
- Warning logged (preserved)

**If shutdown fails**:
- Tasks may not cancel cleanly (log error, don't crash)
- Database may not close gracefully (log error)

---

## Success Criteria

### Functional Requirements

✅ **Server starts successfully**
- All initialization phases complete
- No new errors or warnings in logs
- Startup time remains similar (~2-3 seconds)

✅ **Background tasks run correctly**
- Download token cleanup (every 15 minutes)
- API metrics sync (every 5 minutes)
- Expired item purge (startup only)

✅ **Shutdown is graceful**
- All tasks canceled cleanly
- No hanging tasks or zombie processes
- Database connection closed properly

✅ **Existing tests pass**
- Integration tests: `tests/integration/test_api_startup.py`
- E2E tests: No regressions

### Code Quality Requirements

✅ **Improved testability**
- Each init function has unit tests
- Mocking dependencies is straightforward
- Tests run independently (no shared state)

✅ **Better organization**
- Lifespan function reduced to ~50 lines
- Clear separation of concerns
- Explicit dependency documentation

✅ **Maintained behavior**
- Exact same logging output
- Same error handling (raise vs warn)
- Same initialization order

### Performance Requirements

✅ **No regression**
- Startup time ≤ current time
- Memory usage unchanged
- Background task overhead unchanged

---

## Rollback Plan

### Git Strategy

```bash
# Current commit (before refactor)
git tag pre-1010-lifespan-refactor

# After refactor, if issues arise:
git revert HEAD  # Revert the refactor commit
```

### Incremental Approach

**Phase 1**: Extract modules but DON'T update api/app.py yet
- Create all `api/startup/*.py` files
- Write unit tests
- Verify imports work

**Phase 2**: Update api/app.py in development environment only
- Test locally
- Verify startup/shutdown
- Run integration tests

**Phase 3**: Deploy to staging (if applicable)
- Monitor logs for errors
- Run smoke tests

**Phase 4**: Merge to main
- Only after successful testing in phases 1-3

### Fallback Markers

**Keep original code as comments** (temporary - remove after 1 week):
```python
# ORIGINAL LIFESPAN FUNCTION (Handover 1010 - remove after 2025-12-25)
# Lines 172-650 preserved below for emergency rollback
# [original code here]
```

---

## Dependencies

### Required Before Starting

✅ **Database running**: PostgreSQL 18 on localhost:5432
✅ **Config valid**: `config.yaml` exists and has correct structure
✅ **Python environment**: Virtual environment activated, dependencies installed

### Tools Needed

- `pytest` for running unit tests
- `pytest-asyncio` for async test support
- `pytest-mock` for mocking
- `ruff` and `black` for linting/formatting

### Related Handovers

- **Handover 0111**: Event bus initialization debugging (verbose logging)
- **Handover 0107**: Agent health monitoring feature
- **Handover 0100**: Download token cleanup task
- **Handover 0070**: Expired item purge (projects and products)

---

## Execution Checklist

### Pre-Implementation

- [ ] Read `api/app.py` lines 172-650 (lifespan function)
- [ ] Map all state dependencies (what sets what)
- [ ] Document initialization order (critical for correctness)
- [ ] Identify error handling patterns (raise vs warn)
- [ ] Review related handovers (0111, 0107, 0100, 0070)

### Implementation

- [ ] Create `api/startup/` directory
- [ ] Create `api/startup/__init__.py`
- [ ] Create `api/startup/database.py` + unit tests
- [ ] Create `api/startup/core_services.py` + unit tests
- [ ] Create `api/startup/event_bus.py` + unit tests
- [ ] Create `api/startup/background_tasks.py` + unit tests
- [ ] Create `api/startup/health_monitor.py` + unit tests
- [ ] Create `api/startup/validation.py` + unit tests
- [ ] Create `api/startup/shutdown.py` + unit tests
- [ ] Update `api/app.py` lifespan function
- [ ] Run linting: `ruff api/startup/; black api/startup/`

### Testing

- [ ] Run unit tests: `pytest tests/startup/ -v`
- [ ] Run integration tests: `pytest tests/integration/test_api_startup.py -v`
- [ ] Manual test: Start server and verify logs
- [ ] Manual test: Health check endpoint
- [ ] Manual test: Graceful shutdown (Ctrl+C)
- [ ] Manual test: Background tasks running (check logs after 5/15 minutes)

### Documentation

- [ ] Update `docs/SERVER_ARCHITECTURE_TECH_STACK.md` (mention startup modules)
- [ ] Add docstrings to all new functions
- [ ] Add comments explaining critical dependencies
- [ ] Create devlog: `docs/devlogs/2025-12-18_handover_1010_lifespan_refactor.md`

### Deployment

- [ ] Create git tag: `git tag pre-1010-lifespan-refactor`
- [ ] Commit changes with clear message
- [ ] Test in development environment
- [ ] Monitor logs for 24 hours
- [ ] Remove fallback comments after 1 week

---

## Notes

### Why This Refactor Matters

1. **Testability**: Current lifespan function is nearly impossible to unit test (too many dependencies)
2. **Maintainability**: 480 lines in a single function is hard to navigate and modify
3. **Clarity**: Initialization order and dependencies are implicit, not explicit
4. **Debugging**: When startup fails, it's hard to isolate which phase failed
5. **Reusability**: Background task logic can't be reused or tested independently

### Design Decisions

**Why separate modules instead of helper functions?**
- Modules enable true unit testing (can mock imports)
- Clearer file organization (each module has one responsibility)
- Easier to find and modify specific initialization logic

**Why keep all logic in init functions instead of classes?**
- Simpler for this use case (no state to manage)
- Functions are easier to test than class methods
- Follows FastAPI lifespan pattern (function-based)

**Why not use dependency injection framework?**
- Overkill for startup sequence (only runs once)
- Explicit function calls are clearer than magic DI
- Easier to debug when order matters

### Future Enhancements (Out of Scope)

- **Configuration validation**: Validate config.yaml before initialization (Handover 1011?)
- **Health checks**: Add per-phase health checks (Handover 1012?)
- **Metrics**: Track initialization time per phase (Handover 1013?)
- **Parallel initialization**: Some phases could run concurrently (Handover 1014?)

---

## Estimated Effort

**Total**: 4 hours

**Breakdown**:
- Pre-implementation research: 30 minutes
- Module extraction: 2 hours
- Unit test writing: 1 hour
- Integration testing: 30 minutes
- Documentation: 30 minutes (devlog + docstrings)

---

## Approval Required

**Tier 2** - User must approve before implementation.

**Reason**: Changes critical startup path. While risk is mitigated through testing and incremental approach, this is core infrastructure that affects every server startup.

**Approval Question**: "Do you approve Handover 1010 (Lifespan Refactor)? This will extract api/app.py lifespan logic into 7 testable modules, reducing the function from 480 to ~50 lines while preserving exact behavior."

---

**End of Handover 1010**
