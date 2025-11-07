# WebSocket Event Bus Architecture

**Handover 0111 Issue #1: WebSocket Event Bus for MCP Context**
**Created**: 2025-11-06
**Status**: Implemented

## Problem Statement

WebSocket broadcasts from MCP tool context were failing silently because:

1. MCP tools run in `tool_accessor.py` context where `state.websocket_manager` is NOT available
2. WebSocket broadcast code existed in MCP tools but `ws_manager` was always None
3. No errors were raised - just silent failure with missing UI updates
4. Mission updates and agent creation events never reached the frontend

**Root Cause**: Tight coupling between MCP tools and FastAPI application state.

## Solution: Event Bus Pattern

Implemented a simple in-memory event bus to decouple MCP tools from WebSocket infrastructure.

### Design Pattern: Publish-Subscribe

```
MCP Tool Context          Event Bus           WebSocket Context
─────────────────         ─────────         ──────────────────
[MCP Tool]  ─────publish──→ [EventBus] ─────subscribe──→ [WS Listener]
                                                          ↓
                                                    [WebSocket Manager]
                                                          ↓
                                                    [Frontend UI]
```

### Key Components

1. **EventBus** (`api/event_bus.py`)
   - Central pub/sub coordinator
   - Async event handlers
   - Error isolation (handler failures don't affect other handlers)
   - Production-grade logging and metrics

2. **WebSocketEventListener** (`api/websocket_event_listener.py`)
   - Subscribes to EventBus events
   - Broadcasts via WebSocket manager
   - Maintains multi-tenant isolation
   - Handles connection failures gracefully

3. **Application Integration** (`api/app.py`)
   - EventBus initialized at startup
   - WebSocketEventListener registered after WebSocket manager
   - Stored in `app.state.event_bus` for global access

4. **MCP Tools** (`src/giljo_mcp/tools/`)
   - Publish events instead of direct WebSocket calls
   - Context-agnostic (works anywhere)
   - Simplified error handling

## Benefits

- **Decoupling**: MCP tools don't depend on WebSocket manager availability
- **Reliability**: Handler failures don't affect event publishing
- **Scalability**: Easy to add new event types and listeners
- **Testability**: Clear separation of concerns enables isolated testing

## Testing

**Test Coverage**: 9 tests, all passing

Run tests:
```bash
pytest tests/test_event_bus.py -v
```

## Migration Impact

### Changed Files

1. **api/event_bus.py** (NEW) - EventBus implementation
2. **api/websocket_event_listener.py** (NEW) - WebSocket bridge
3. **api/app.py** - Added EventBus initialization
4. **src/giljo_mcp/tools/project.py** - Uses EventBus instead of direct WebSocket
5. **src/giljo_mcp/tools/orchestration.py** - Uses EventBus instead of direct WebSocket
6. **tests/test_event_bus.py** (NEW) - Comprehensive test suite

### Backward Compatibility

✅ **Fully Backward Compatible** - No breaking changes, frontend unchanged.

## References

- **Issue**: Handover 0111 Issue #1
- **Pattern**: Publish-Subscribe (Observer Pattern)
