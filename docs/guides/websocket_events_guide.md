# WebSocket Events Developer Guide

**For**: Backend Developers Contributing to GiljoAI MCP
**Goal**: Implement WebSocket events with production-grade patterns
**Prerequisites**: Python 3.11+, FastAPI knowledge, WebSocket basics

---

## Core Principles

1. **Always use dependency injection** - Never access WebSocket manager directly
2. **Always use EventFactory** - Never construct events manually
3. **Always enforce tenant isolation** - Filter by tenant_key at broadcast level
4. **Always handle errors gracefully** - WebSocket failures shouldn't crash endpoints
5. **Always log with structure** - Include context for debugging

---

## Quick Start

### Minimal Working Example

```python
from fastapi import APIRouter, Depends
from api.dependencies.websocket import get_websocket_dependency, WebSocketDependency
from api.dependencies.auth import get_current_active_user
from api.events.schemas import EventFactory
from src.giljo_mcp.models import User

router = APIRouter()

@router.post("/example")
async def example_endpoint(
    current_user: User = Depends(get_current_active_user),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)
):
    # Business logic
    result = do_something()

    # Create standardized event
    event_data = EventFactory.project_mission_updated(
        project_id=result.project_id,
        tenant_key=current_user.tenant_key,
        mission=result.mission
    )

    # Broadcast to tenant
    sent_count = await ws_dep.broadcast_to_tenant(
        tenant_key=current_user.tenant_key,
        event_type="project:mission_updated",
        data=event_data["data"]
    )

    logger.info(f"Broadcasted to {sent_count} clients")
    return result
```

---

## Step-by-Step Guide

### Step 1: Add Dependency Injection

```python
from api.dependencies.websocket import get_websocket_dependency, WebSocketDependency
from fastapi import Depends

@router.post("/your-endpoint")
async def your_endpoint(
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),  # ADD THIS
    current_user: User = Depends(get_current_active_user)
):
    pass
```

### Step 2: Choose Event Type

**Available Events** (from `api/events/schemas.py`):

- `project:mission_updated` - Mission generated/regenerated
- `agent:created` - New agent job created
- `agent:status_changed` - Agent status transitions
- `orchestrator:prompt_generated` - Thin prompt generated (0088 migration)
- `job:succession_triggered` - Orchestrator succession started (0080)
- `job:successor_created` - Successor orchestrator created (0080)

**Create New Event** (if needed):

```python
# 1. Add Pydantic model in api/events/schemas.py
class YourEventData(BaseModel):
    """Data payload for your:event."""
    field1: str
    field2: int

class YourEvent(BaseModel):
    """Complete event structure."""
    type: Literal["your:event"] = "your:event"
    timestamp: str
    schema_version: str = "1.0"
    data: YourEventData

# 2. Add factory method
@staticmethod
def your_event(field1: str, field2: int) -> dict:
    event = YourEvent(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        data=YourEventData(field1=field1, field2=field2)
    )
    return event.model_dump(mode="json")

# 3. Add to __all__ export
__all__ = [..., "YourEvent", "YourEventData"]
```

### Step 3: Create Event with EventFactory

```python
from api.events.schemas import EventFactory

# Use existing event
event_data = EventFactory.project_mission_updated(
    project_id=project.id,
    tenant_key=current_user.tenant_key,
    mission="Build feature X",
    user_config_applied=True,
    field_toggles={"product_vision": True}
)

# Or use your custom event
event_data = EventFactory.your_event(
    field1="value1",
    field2=42
)
```

### Step 4: Broadcast Event

```python
sent_count = await ws_dep.broadcast_to_tenant(
    tenant_key=current_user.tenant_key,  # CRITICAL: Tenant isolation
    event_type="your:event",
    data=event_data["data"]  # Extract data from EventFactory result
)

logger.info(
    f"Event broadcasted to {sent_count} clients",
    extra={
        "event_type": "your:event",
        "tenant_key": current_user.tenant_key,
        "sent_count": sent_count
    }
)
```

### Step 5: Handle Edge Cases

```python
# Check WebSocket availability
if not ws_dep.is_available():
    logger.warning("WebSocket unavailable, skipping broadcast")
    # Continue with business logic (graceful degradation)

# Exclude originating client (for collaborative features)
sent_count = await ws_dep.broadcast_to_tenant(
    tenant_key=current_user.tenant_key,
    event_type="collaborative:update",
    data=event_data["data"],
    exclude_client=request_client_id  # Don't echo back
)

# Project-scoped broadcast
sent_count = await ws_dep.send_to_project(
    tenant_key=current_user.tenant_key,
    project_id=project.id,
    event_type="agent:created",
    data={"agent": agent_data}
)
```

---

## Testing WebSocket Events

### Unit Test Example

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from api.dependencies.websocket import WebSocketDependency

@pytest.fixture
def mock_ws_dependency():
    """Mock WebSocket dependency for testing."""
    mock_manager = MagicMock()
    mock_manager.active_connections = {
        "client_1": AsyncMock(),
        "client_2": AsyncMock()
    }
    mock_manager.auth_contexts = {
        "client_1": {"tenant_key": "tenant_123"},
        "client_2": {"tenant_key": "tenant_123"}
    }
    return WebSocketDependency(mock_manager)

@pytest.mark.asyncio
async def test_endpoint_broadcasts_event(mock_ws_dependency):
    """Test that endpoint broadcasts WebSocket event."""
    # Call endpoint
    result = await your_endpoint(
        ws_dep=mock_ws_dependency,
        current_user=test_user
    )

    # Verify broadcast was called
    assert result["clients_notified"] == 2

    # Verify correct event sent to client_1
    mock_ws_dependency.manager.active_connections["client_1"].send_json.assert_called_once()
    call_args = mock_ws_dependency.manager.active_connections["client_1"].send_json.call_args
    event = call_args[0][0]

    assert event["type"] == "your:event"
    assert "timestamp" in event
    assert event["data"]["field1"] == "expected_value"
```

### Integration Test with Dependency Override

```python
from fastapi.testclient import TestClient
from api.dependencies.websocket import get_websocket_dependency

def test_websocket_broadcast_integration(client: TestClient, app):
    """Integration test with real endpoint."""

    # Create mock dependency
    def override_ws_dependency():
        mock_manager = MagicMock()
        mock_manager.active_connections = {}
        return WebSocketDependency(mock_manager)

    # Override dependency
    app.dependency_overrides[get_websocket_dependency] = override_ws_dependency

    # Call endpoint
    response = client.post("/api/your-endpoint", json={...})

    # Assertions
    assert response.status_code == 200
    assert response.json()["clients_notified"] >= 0

    # Clean up
    app.dependency_overrides.clear()
```

---

## Common Patterns

### Pattern 1: Async Operation with Real-Time Updates

```python
@router.post("/long-running-task")
async def start_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
    background_tasks: BackgroundTasks
):
    # Create task
    task = create_task(task_data)

    # Broadcast task started
    await ws_dep.broadcast_to_tenant(
        tenant_key=current_user.tenant_key,
        event_type="task:started",
        data={"task_id": str(task.id), "status": "running"}
    )

    # Run task in background
    background_tasks.add_task(
        run_task_with_updates,
        task,
        current_user.tenant_key,
        ws_dep
    )

    return {"task_id": str(task.id)}

async def run_task_with_updates(task, tenant_key, ws_dep):
    """Background task with progress updates."""
    for progress in range(0, 101, 10):
        # Do work...
        await asyncio.sleep(1)

        # Broadcast progress
        await ws_dep.broadcast_to_tenant(
            tenant_key=tenant_key,
            event_type="task:progress",
            data={"task_id": str(task.id), "progress": progress}
        )

    # Broadcast completion
    await ws_dep.broadcast_to_tenant(
        tenant_key=tenant_key,
        event_type="task:completed",
        data={"task_id": str(task.id), "result": "success"}
    )
```

### Pattern 2: Bulk Operations

```python
@router.post("/bulk-update")
async def bulk_update(
    updates: List[UpdateData],
    current_user: User = Depends(get_current_active_user),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)
):
    results = []

    for update in updates:
        result = apply_update(update)
        results.append(result)

    # Single broadcast for all updates (efficient)
    await ws_dep.broadcast_to_tenant(
        tenant_key=current_user.tenant_key,
        event_type="bulk:updates_completed",
        data={
            "updates_count": len(results),
            "results": [r.id for r in results]
        }
    )

    return results
```

### Pattern 3: Error Broadcasting

```python
@router.post("/risky-operation")
async def risky_operation(
    data: OperationData,
    current_user: User = Depends(get_current_active_user),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)
):
    try:
        result = perform_operation(data)

        # Broadcast success
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="operation:success",
            data={"operation_id": str(result.id)}
        )

        return result

    except OperationError as e:
        # Broadcast error to UI
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="operation:error",
            data={
                "operation_id": str(data.id),
                "error": str(e),
                "retry_possible": True
            }
        )

        raise HTTPException(status_code=400, detail=str(e))
```

---

## Anti-Patterns (DO NOT USE)

### ❌ Anti-Pattern 1: Manual WebSocket Access

```python
# WRONG - Fragile, hard to test
websocket_manager = getattr(request.app.state, "websocket_manager", None)
if websocket_manager:
    for client_id, ws in websocket_manager.active_connections.items():
        await ws.send_json({...})
```

### ❌ Anti-Pattern 2: Manual Event Construction

```python
# WRONG - No validation, inconsistent structure
event = {
    "type": "my:event",
    "data": {"field": "value"},
    # Missing timestamp, schema_version, etc.
}
```

### ❌ Anti-Pattern 3: Missing Tenant Isolation

```python
# WRONG - Security vulnerability (sends to ALL clients)
for client_id, ws in manager.active_connections.items():
    await ws.send_json(event)  # No tenant check!
```

### ❌ Anti-Pattern 4: Silent Failures

```python
# WRONG - Errors hidden
try:
    await ws_dep.broadcast_to_tenant(...)
except:
    pass  # Silent failure
```

### ❌ Anti-Pattern 5: Blocking Operations

```python
# WRONG - Blocks event loop
sent_count = 0
for client in clients:
    time.sleep(0.1)  # BLOCKING!
    sent_count += await ws.send_json(event)
```

---

## Production Checklist

Before deploying WebSocket events to production:

- [ ] Uses `get_websocket_dependency()` dependency injection
- [ ] Uses `EventFactory` for event creation
- [ ] Enforces `tenant_key` filtering in `broadcast_to_tenant()`
- [ ] Handles graceful degradation (checks `ws_dep.is_available()`)
- [ ] Includes structured logging with `extra` context
- [ ] Has unit tests with mocked WebSocket dependency
- [ ] Has integration tests with dependency override
- [ ] Validates Pydantic event schema
- [ ] Documented in this guide (if new pattern)
- [ ] No blocking operations in broadcast loop

---

## Related Documentation

- [WebSocket Dependency Injection Technical Docs](../technical/WEBSOCKET_DEPENDENCY_INJECTION.md)
- [Event Schemas Source Code](../../api/events/schemas.py)
- [Stage Project Feature Overview](../STAGE_PROJECT_FEATURE.md)

---

**Last Updated**: 2024-11-02
**Version**: 3.0.0
**Maintained By**: Documentation Manager Agent
