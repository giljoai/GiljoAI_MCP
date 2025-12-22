# Handover 0372: MessageService Unification

**Date**: 2025-12-22
**Priority**: HIGH
**Status**: READY FOR EXECUTION
**Estimated Effort**: 4-6 hours
**Agent**: TDD-Implementor (service layer expert)

---

## Executive Summary

### What
Merge `message_service_0366b.py` into the production `message_service.py` to unify the split MessageService architecture and recover critical features lost during the Agent Identity Refactor (0366b).

### Why
During dead code cleanup (Handover 0371), we discovered that `message_service_0366b.py` is NOT dead code—it's an **incomplete integration** from 0366b that was never finished. This has created a split architecture:

- **Production path**: MCP tools → `tool_accessor.py` → `message_service.py` (ACTIVE but missing features)
- **Orphan path**: `agent_communication.py` → `message_service_0366b.py` (NEVER CALLED but has better features)

The orphan version contains critical features for orchestrator succession:
1. **Agent-ID routing**: Routes by `agent_id` (executor) instead of `job_id` (work order) - enables message delivery to NEW orchestrator after succession
2. **Smart filtering**: `exclude_self`, `exclude_progress`, `message_types` reduce noise
3. **Cleaner API**: Returns `list[dict]` instead of wrapped `dict` (simpler for clients)

### Impact
- **Succession support**: Messages will route to new orchestrator instances (currently broken)
- **Reduced noise**: Agents get relevant messages only (no self-echoes or progress spam)
- **Code clarity**: Single MessageService instead of parallel implementations
- **Maintenance**: One codebase to test and maintain

---

## Prerequisites

Before starting, verify:

- [ ] **Database access**: PostgreSQL 18 running, password=$DB_PASSWORD
- [ ] **Test environment**: Can run `pytest tests/services/test_message_service*.py`
- [ ] **Backup**: All existing tests pass before changes begin
- [ ] **No active work**: No other handovers modifying MessageService

**Verification commands**:
```powershell
# Database connection
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"

# Run existing tests
pytest tests/services/test_message_service*.py -v
pytest tests/integration/test_message_service_receive.py -v
```

---

## Phase 1: Analysis - Method-by-Method Comparison

### 1.1 Side-by-Side Comparison

| Method | `message_service.py` (production) | `message_service_0366b.py` (orphan) | Decision |
|--------|----------------------------------|-------------------------------------|----------|
| `send_message()` | ✅ Routes by `job_id` (work order)<br>✅ Has WebSocket events<br>✅ Persists to JSONB<br>❌ No agent succession support | ✅ Routes by `agent_id` (executor)<br>❌ No WebSocket events<br>❌ No JSONB persistence<br>✅ Succession-aware routing | **MERGE**: Keep production's WebSocket + JSONB, add 0366b's agent-ID routing |
| `broadcast()` | ✅ Uses `send_message()` internally<br>✅ WebSocket events<br>❌ Routes to job types | N/A (no equivalent) | **KEEP**: Production version works, just needs routing update |
| `broadcast_to_project()` | N/A (no equivalent) | ✅ Broadcasts to all active executions<br>✅ Agent-ID routing | **ADD**: New method for agent-level broadcasts |
| `receive_messages()` | ✅ Returns `dict[str, Any]` with wrapper<br>❌ No filtering params<br>❌ Routes by `job_id` | ✅ Returns `list[dict]` directly<br>✅ `exclude_self`, `exclude_progress`, `message_types`<br>✅ Routes by `agent_id` | **MERGE**: Keep production's WebSocket, add 0366b's filtering + agent-ID routing, **change return type** |
| `get_messages()` | ✅ Basic retrieval by agent name<br>❌ No advanced filtering | N/A (no equivalent) | **KEEP**: Production version |
| `list_messages()` | ✅ Comprehensive listing<br>✅ Multiple filter options | N/A (no equivalent) | **KEEP**: Production version |
| `complete_message()` | ✅ Marks message completed<br>✅ WebSocket events | N/A (no equivalent) | **KEEP**: Production version |
| `acknowledge_message()` | N/A (auto-ack in receive) | ✅ Explicit acknowledgment<br>✅ Agent-ID routing | **ADD**: Explicit ack method (optional for clients) |
| `_persist_message_to_agent_jsonb()` | ✅ Counter persistence | N/A | **KEEP**: Production-only feature |
| `_update_jsonb_message_status()` | ✅ Counter sync | N/A | **KEEP**: Production-only feature |

### 1.2 Key Differences Summary

**0366b Unique Features (MUST MERGE)**:
1. **Agent-ID routing** (`agent_id` executor vs `job_id` work order)
2. **Advanced filtering** in `receive_messages()`:
   - `exclude_self: bool = True` - No self-echoes
   - `exclude_progress: bool = True` - No progress spam
   - `message_types: Optional[list[str]]` - Type allowlist
3. **Cleaner return type** (`list[dict]` vs `dict` wrapper)
4. **Succession-aware resolution** (routes to active execution, not job)

**Production Unique Features (MUST KEEP)**:
1. **WebSocket events** for real-time UI updates
2. **JSONB persistence** for message counters
3. **Broadcast method** for project-wide messages
4. **Complete/acknowledge** workflow methods

---

## Phase 2: Merge Strategy

### 2.1 Routing Layer Update

**Goal**: Replace `job_id` routing with `agent_id` routing while preserving WebSocket/JSONB features.

**Changes to `send_message()`**:

**BEFORE** (production - lines 159-186):
```python
# Resolve agent_type strings to job_id UUIDs before storing
resolved_to_agents = []
for agent_ref in to_agents:
    if agent_ref == 'all':
        resolved_to_agents.append('all')
    elif len(agent_ref) == 36 and '-' in agent_ref:
        # Already a UUID (job_id) - use directly
        resolved_to_agents.append(agent_ref)
    else:
        # Agent type string (e.g., "orchestrator") - resolve to job_id
        agent_result = await session.execute(
            select(AgentJob).where(
                AgentJob.project_id == project_id,
                AgentJob.job_type == agent_ref
            ).limit(1)
        )
        agent_job = agent_result.scalar_one_or_none()
        if agent_job:
            resolved_to_agents.append(agent_job.job_id)
```

**AFTER** (merged - use 0366b logic):
```python
# Resolve agent_type strings to agent_id UUIDs (executor, not work order)
# This enables succession: messages route to NEW executor after handover
resolved_to_agents = []
for agent_ref in to_agents:
    if agent_ref == 'all':
        resolved_to_agents.append('all')
    elif len(agent_ref) == 36 and '-' in agent_ref:
        # Already a UUID (agent_id) - use directly
        resolved_to_agents.append(agent_ref)
    else:
        # Agent type string (e.g., "orchestrator") - resolve to active execution agent_id
        exec_result = await session.execute(
            select(AgentExecution).join(AgentJob).where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.agent_type == agent_ref,
                    AgentExecution.status.in_(["waiting", "working", "blocked"]),  # Active statuses
                    AgentExecution.tenant_key == tenant_key
                )
            ).order_by(AgentExecution.instance_number.desc()).limit(1)  # Latest instance
        )
        execution = exec_result.scalar_one_or_none()
        if execution:
            resolved_to_agents.append(execution.agent_id)
            self._logger.info(
                f"[RESOLVER] Resolved agent_type '{agent_ref}' to agent_id '{execution.agent_id}'"
            )
        else:
            # Could not resolve - keep original (will fail to deliver)
            resolved_to_agents.append(agent_ref)
            self._logger.warning(
                f"[RESOLVER] Could not resolve agent_type '{agent_ref}' to active execution in project {project_id}"
            )
```

**Files affected**: `src/giljo_mcp/services/message_service.py` lines 159-186

---

### 2.2 Add Filtering Parameters to `receive_messages()`

**Goal**: Add smart filtering from 0366b while keeping WebSocket/JSONB features.

**BEFORE** (production - lines 489-494):
```python
async def receive_messages(
    self,
    agent_id: str,
    limit: int = 10,
    tenant_key: Optional[str] = None
) -> dict[str, Any]:
```

**AFTER** (merged signature):
```python
async def receive_messages(
    self,
    agent_id: str,
    limit: int = 10,
    tenant_key: Optional[str] = None,
    exclude_self: bool = True,
    exclude_progress: bool = True,
    message_types: Optional[list[str]] = None
) -> dict[str, Any]:  # Keep dict return for backward compatibility with existing callers
    """
    Receive pending messages for an agent executor with optional filtering.

    Handover 0372: Added filtering parameters from 0366b for noise reduction.

    Args:
        agent_id: Agent execution ID (executor UUID)
        limit: Maximum number of messages to retrieve (default: 10)
        tenant_key: Optional tenant key (uses current if not provided)
        exclude_self: Filter out messages from same agent_id (default: True)
        exclude_progress: Filter out progress-type messages (default: True)
        message_types: Optional allow-list of message types (default: None = all types)

    Returns:
        Dict with success status and list of messages or error
    """
```

**Add filtering logic** (after line 585, before `query = select(Message)`):
```python
# Build query conditions (Handover 0372: Agent-ID filtering from 0366b)
conditions = [
    Message.tenant_key == tenant_key,
    Message.project_id == job.project_id,
    Message.status == "pending",  # Only unread messages
    or_(
        # Direct message: JSONB array contains agent_id
        func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
        # Broadcast: JSONB array contains 'all' BUT exclude sender (Issue 0361-3)
        and_(
            func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB)),
            func.coalesce(
                Message.meta_data.op('->')('_from_agent').astext,
                func.cast('', String)
            ) != job.job_type
        )
    )
]

# HANDOVER 0372: Apply filtering conditions from 0366b

# Filter: exclude_self - Filter out messages from the same agent
if exclude_self:
    # Meta_data._from_agent should not equal current agent_id
    conditions.append(
        func.coalesce(
            Message.meta_data.op('->>')('_from_agent'),
            ''
        ) != agent_id
    )

# Filter: exclude_progress - Filter out progress-type messages
if exclude_progress:
    conditions.append(Message.message_type != "progress")

# Filter: message_types - Allow-list of message types
if message_types is not None:
    if len(message_types) == 0:
        # Empty allow-list means no messages should pass
        conditions.append(Message.id == None)  # noqa: E711
    else:
        # Only allow specified message types
        conditions.append(Message.message_type.in_(message_types))

query = select(Message).where(and_(*conditions)).order_by(Message.created_at)
```

**Files affected**: `src/giljo_mcp/services/message_service.py` lines 489-585

---

### 2.3 Add `broadcast_to_project()` Method

**Goal**: Add agent-level broadcast from 0366b.

**Add new method** (after `broadcast()` method, around line 423):
```python
async def broadcast_to_project(
    self,
    project_id: str,
    content: str,
    from_agent: str = "orchestrator",
    tenant_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Broadcast a message to all active executions in a project.

    Handover 0372: Added from 0366b for agent-level broadcasting.
    Differs from broadcast() which sends to agent types, not active executors.

    Args:
        project_id: Project ID to broadcast to
        content: Message content
        from_agent: Sender agent_id or agent_type (default: "orchestrator")
        tenant_key: Tenant key for multi-tenant isolation

    Returns:
        Dict with success status and message details or error

    Example:
        >>> result = await service.broadcast_to_project(
        ...     project_id="project-123",
        ...     content="Project status update",
        ...     tenant_key="tenant-abc"
        ... )
    """
    try:
        async with self._get_session() as session:
            # Get all active executions in project
            result = await session.execute(
                select(AgentExecution).join(AgentJob).where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentExecution.status.in_(["waiting", "working", "blocked"]),
                        AgentExecution.tenant_key == tenant_key
                    )
                )
            )
            executions = result.scalars().all()

            if not executions:
                return {
                    "success": False,
                    "error": "No active executions found in project"
                }

            agent_ids = [exec.agent_id for exec in executions]

            # Send message to all active executors
            result = await self.send_message(
                to_agents=agent_ids,
                content=content,
                project_id=project_id,
                message_type="broadcast",
                priority="normal",
                from_agent=from_agent,
                tenant_key=tenant_key,
            )

            if result.get("success"):
                result["count"] = len(agent_ids)

            return result

    except Exception as e:
        self._logger.exception(f"Failed to broadcast message to project: {e}")
        return {"success": False, "error": str(e)}
```

**Files affected**: `src/giljo_mcp/services/message_service.py` (new method after line 423)

---

### 2.4 Add Explicit `acknowledge_message()` Method

**Goal**: Add explicit acknowledgment method from 0366b (optional for clients).

**Add new method** (after `complete_message()` method, around line 917):
```python
async def acknowledge_message(
    self,
    message_id: str,
    agent_id: str,
    tenant_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Explicitly acknowledge a message using agent_id (executor).

    Handover 0372: Added from 0366b for explicit acknowledgment workflow.
    Note: receive_messages() auto-acknowledges, so this is optional.

    Args:
        message_id: Message UUID
        agent_id: Agent execution ID (executor UUID)
        tenant_key: Tenant key for multi-tenant isolation

    Returns:
        Dict with success status or error

    Example:
        >>> result = await service.acknowledge_message(
        ...     message_id="msg-123",
        ...     agent_id="agent-uuid-123",
        ...     tenant_key="tenant-abc"
        ... )
    """
    try:
        # Use provided tenant_key or get from context
        if not tenant_key:
            tenant_key = self.tenant_manager.get_current_tenant()

        if not tenant_key:
            return {
                "success": False,
                "error": "No tenant context available"
            }

        async with self._get_session() as session:
            # Get message
            msg_result = await session.execute(
                select(Message).where(
                    and_(
                        Message.id == message_id,
                        Message.tenant_key == tenant_key
                    )
                )
            )
            message = msg_result.scalar_one_or_none()

            if not message:
                return {
                    "success": False,
                    "error": "Message not found or access denied"
                }

            # Update message
            message.status = "acknowledged"
            message.acknowledged_at = datetime.now(timezone.utc)
            if not message.acknowledged_by:
                message.acknowledged_by = []
            if agent_id not in message.acknowledged_by:
                message.acknowledged_by.append(agent_id)

            await session.commit()

            self._logger.info(
                f"Message {message_id} acknowledged by agent {agent_id}"
            )

            # Update JSONB for UI counter sync
            await self._update_jsonb_message_status(
                session=session,
                agent_job_id=agent_id,
                message_ids=[message_id],
                new_status="acknowledged"
            )

            # Emit WebSocket event if manager available
            if self._websocket_manager:
                try:
                    await self._websocket_manager.broadcast_message_acknowledged(
                        message_id=message_id,
                        agent_id=agent_id,
                        tenant_key=tenant_key,
                        project_id=message.project_id,
                        message_ids=[message_id],
                    )
                except Exception as ws_error:
                    self._logger.warning(f"Failed to emit WebSocket for ack: {ws_error}")

            return {
                "success": True,
                "acknowledged": True,
                "message_id": message_id,
            }

    except Exception as e:
        self._logger.exception(f"Failed to acknowledge message: {e}")
        return {"success": False, "error": str(e)}
```

**Files affected**: `src/giljo_mcp/services/message_service.py` (new method after line 917)

---

## Phase 3: Implementation Checklist

### 3.1 Update Production MessageService

- [ ] **Backup original**: `cp message_service.py message_service_backup.py`
- [ ] **Update routing** (Phase 2.1): Replace `job_id` resolution with `agent_id` resolution in `send_message()` (lines 159-186)
- [ ] **Add filtering** (Phase 2.2): Add parameters and filtering logic to `receive_messages()` (lines 489-585)
- [ ] **Add broadcast_to_project()** (Phase 2.3): Insert new method after `broadcast()` (line 423)
- [ ] **Add acknowledge_message()** (Phase 2.4): Insert new method after `complete_message()` (line 917)
- [ ] **Update docstring**: Add "Handover 0372: Unified with 0366b" to class docstring (line 42)
- [ ] **Test imports**: Verify `from giljo_mcp.models.agent_identity import AgentExecution` exists (should be line 34)

**Verification**:
```powershell
# Syntax check
python -m py_compile src/giljo_mcp/services/message_service.py

# Line count check (should be ~1300-1400 lines after merge)
(Get-Content src/giljo_mcp/services/message_service.py | Measure-Object -Line).Lines
```

---

### 3.2 Update Callers

Only ONE caller needs updating: `agent_communication.py`

**BEFORE** (`agent_communication.py` line 38):
```python
from giljo_mcp.services.message_service_0366b import MessageService
```

**AFTER**:
```python
from giljo_mcp.services.message_service import MessageService
```

**Update method call** (`check_orchestrator_messages()` lines 76-88):

**BEFORE**:
```python
# Receive messages using agent_id (returns list directly)
messages = await message_service.receive_messages(
    agent_id=agent_id,
    tenant_key=tenant_key,
    limit=10,
)
```

**AFTER** (add filtering params):
```python
# Receive messages using agent_id with filtering (Handover 0372)
result = await message_service.receive_messages(
    agent_id=agent_id,
    tenant_key=tenant_key,
    limit=10,
    exclude_self=True,  # No self-echoes
    exclude_progress=True,  # No progress spam
)
messages = result.get("messages", [])  # Extract list from dict
```

**Files affected**: `src/giljo_mcp/tools/agent_communication.py` lines 38, 84-88

**Checklist**:
- [ ] Update import statement (line 38)
- [ ] Update `check_orchestrator_messages()` call (lines 84-88)
- [ ] Update `report_status()` if needed (verify no MessageService usage)

---

## Phase 4: Update Tests

### 4.1 Migrate 0366b Tests to Production Test Suite

**Action**: Merge `test_message_service_0366b.py` features into `test_message_service_contract.py`

**Files**:
- Source: `tests/services/test_message_service_0366b.py` (~400 lines)
- Target: `tests/services/test_message_service_contract.py` (expand with new tests)

**Tests to add**:
1. `test_receive_messages_exclude_self` - Verify self-filtering
2. `test_receive_messages_exclude_progress` - Verify progress filtering
3. `test_receive_messages_message_types_allowlist` - Verify type filtering
4. `test_broadcast_to_project_agent_level` - Verify agent-ID broadcast
5. `test_acknowledge_message_explicit` - Verify explicit ack method
6. `test_send_message_agent_id_routing` - Verify executor routing
7. `test_receive_messages_succession_routing` - Verify message delivery to new executor

**Checklist**:
- [ ] Copy test fixtures from 0366b file
- [ ] Adapt tests to production MessageService API
- [ ] Verify all 0366b test scenarios covered
- [ ] Run: `pytest tests/services/test_message_service_contract.py -v`

---

### 4.2 Update Agent Communication Tests

**Files**:
- `tests/tools/test_agent_communication_0366c.py`
- `tests/tools/test_agent_communication_0360.py`

**Changes**:
1. Import should work unchanged (uses `agent_communication.py` which now imports production service)
2. Update assertions if return type changed (check for `result["messages"]` vs direct list)

**Checklist**:
- [ ] Run: `pytest tests/tools/test_agent_communication*.py -v`
- [ ] Fix any failures related to return type changes
- [ ] Verify filtering parameters work as expected

---

### 4.3 Integration Test Update

**File**: `tests/integration/test_message_service_receive.py`

**Changes**:
1. Add tests for filtering parameters
2. Add tests for agent-ID routing vs job-ID routing
3. Add succession scenario test (send to old job, verify delivery to new execution)

**Checklist**:
- [ ] Add integration test for succession scenario
- [ ] Add integration test for filtering combinations
- [ ] Run: `pytest tests/integration/test_message_service_receive.py -v`

---

## Phase 5: Cleanup

### 5.1 Delete Orphan Files

**Files to delete**:
1. `src/giljo_mcp/services/message_service_0366b.py` (~550 lines)
2. `tests/services/test_message_service_0366b.py` (~400 lines)
3. `tests/services/test_orchestration_service_0366b.py` (if only tests 0366b MessageService)
4. `tests/services/test_agent_job_manager_0366b.py` (if MessageService-specific)

**Verification before deletion**:
```powershell
# Check for any remaining imports
git grep "message_service_0366b"

# Should show ONLY:
# - handovers/0372*.md (this handover doc)
# - handovers/completed/0366*.md (historical docs)
```

**Checklist**:
- [ ] Verify no imports remain: `git grep "from.*message_service_0366b"`
- [ ] Delete `message_service_0366b.py`
- [ ] Delete `test_message_service_0366b.py`
- [ ] Delete other 0366b-specific test files (after verifying tests merged)
- [ ] Run full test suite: `pytest tests/ -v`

---

### 5.2 Update Documentation

**Files to update**:

1. **`docs/SERVICES.md`**: Add section on MessageService filtering
   ```markdown
   ### MessageService - Agent Filtering (Handover 0372)

   `receive_messages()` supports smart filtering to reduce noise:
   - `exclude_self=True` (default) - No self-echoes
   - `exclude_progress=True` (default) - No progress spam
   - `message_types=["direct", "broadcast"]` - Type allowlist
   ```

2. **`CLAUDE.md`**: Update MessageService reference
   ```markdown
   - **Agent Jobs**: Use AgentJobManager for lifecycle, MessageService for messaging
   - **Message Routing**: Messages route to agent_id (executor), not job_id (work order) - supports succession
   ```

3. **`handovers/completed/0366b_service_layer_updates-C.md`**: Add completion note
   ```markdown
   ## Handover 0372 Integration
   This handover was INCOMPLETE until Handover 0372 merged the orphaned code into production.
   ```

**Checklist**:
- [ ] Update `docs/SERVICES.md` with filtering documentation
- [ ] Update `CLAUDE.md` with routing clarification
- [ ] Add completion note to 0366b handover
- [ ] Commit documentation updates

---

## Phase 6: Verification Checklist

### 6.1 Functional Testing

Test all scenarios manually or via integration tests:

- [ ] **Agent-ID routing works**: Send message to "orchestrator" agent type, verify delivery to active execution
- [ ] **Succession routing works**: Create new orchestrator execution, send message to type, verify NEW executor receives it
- [ ] **Self-filtering works**: Agent sends message, verifies they don't receive their own broadcast
- [ ] **Progress filtering works**: Send progress message, verify agent doesn't receive it with `exclude_progress=True`
- [ ] **Type filtering works**: Send mixed message types, verify allowlist works
- [ ] **WebSocket events fire**: Verify UI counters update correctly
- [ ] **JSONB persistence works**: Verify counters survive page refresh
- [ ] **Broadcast works**: Verify all active executions receive broadcast

---

### 6.2 Test Coverage

Run tests and verify coverage:

```powershell
# Run all message service tests
pytest tests/services/test_message_service*.py -v --cov=src/giljo_mcp/services/message_service --cov-report=html

# Run integration tests
pytest tests/integration/test_message_service_receive.py -v

# Run agent communication tests
pytest tests/tools/test_agent_communication*.py -v

# Full test suite
pytest tests/ -v
```

**Coverage target**: >80% for `message_service.py`

**Checklist**:
- [ ] All message service tests pass
- [ ] Integration tests pass
- [ ] Agent communication tests pass
- [ ] Coverage >80%
- [ ] No regressions in other test suites

---

### 6.3 Code Quality

Run linters and formatters:

```powershell
# Format code
black src/giljo_mcp/services/message_service.py
black src/giljo_mcp/tools/agent_communication.py

# Check for issues
ruff src/giljo_mcp/services/message_service.py
ruff src/giljo_mcp/tools/agent_communication.py

# Type checking (if mypy configured)
mypy src/giljo_mcp/services/message_service.py
```

**Checklist**:
- [ ] Black formatting applied
- [ ] Ruff passes with no errors
- [ ] No type errors
- [ ] Docstrings complete

---

### 6.4 Final Verification

- [ ] **No orphan imports**: `git grep "message_service_0366b"` returns ONLY handover docs
- [ ] **All tests pass**: `pytest tests/ -v` shows 100% pass rate
- [ ] **No regressions**: Existing functionality unchanged
- [ ] **Documentation updated**: All docs reflect unified MessageService
- [ ] **Commit message clear**: "feat(0372): Unify MessageService - merge 0366b features"

---

## Rollback Plan

If anything breaks during implementation:

### Quick Rollback (< 5 minutes)

```powershell
# Restore backup
cp src/giljo_mcp/services/message_service_backup.py src/giljo_mcp/services/message_service.py

# Restore agent_communication.py import
git checkout src/giljo_mcp/tools/agent_communication.py

# Verify tests pass
pytest tests/ -v
```

### Full Rollback (< 15 minutes)

```powershell
# Revert all changes
git checkout src/giljo_mcp/services/message_service.py
git checkout src/giljo_mcp/tools/agent_communication.py
git checkout tests/services/test_message_service_contract.py
git checkout tests/tools/test_agent_communication_0366c.py

# Verify tests pass
pytest tests/ -v

# Document rollback reason
echo "Handover 0372 rolled back - reason: [describe issue]" >> handovers/0372_rollback_notes.md
```

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| **Breaking change in return type** | HIGH | MEDIUM | Keep `dict` wrapper in production version, extract list internally in callers |
| **WebSocket events break** | MEDIUM | LOW | Extensive testing of UI counters before/after |
| **JSONB persistence breaks** | MEDIUM | LOW | Test counter persistence with page refresh |
| **Succession routing fails** | HIGH | LOW | Integration test with orchestrator succession scenario |
| **Existing tests fail** | MEDIUM | MEDIUM | Run full test suite before/after, fix failures incrementally |
| **Performance regression** | LOW | LOW | Agent-ID queries no slower than job-ID queries (both indexed) |

**Overall Risk**: MEDIUM-LOW (changes are additive, core logic preserved)

---

## Success Criteria

This handover is successful when:

1. ✅ Single `message_service.py` file contains all features (production + 0366b)
2. ✅ `message_service_0366b.py` deleted, no imports remain
3. ✅ All filtering parameters work (`exclude_self`, `exclude_progress`, `message_types`)
4. ✅ Agent-ID routing works (messages delivered to active executor, not job)
5. ✅ Succession scenario works (new orchestrator receives messages after handover)
6. ✅ All tests pass (>80% coverage on MessageService)
7. ✅ WebSocket events fire correctly
8. ✅ JSONB persistence works (counters survive refresh)
9. ✅ Documentation updated
10. ✅ No regressions in existing functionality

---

## Notes for Executing Agent

### Context You Need
- You have NO prior context about this codebase - this handover is your complete guide
- The split architecture happened during Handover 0366b (Agent Identity Refactor) when agent-ID routing was added but never fully integrated
- Production MessageService has 1,104 lines, 0366b version has 550 lines - merged result ~1,300-1,400 lines

### Critical Details
- **Return type**: Keep `dict[str, Any]` in production version to avoid breaking ALL existing callers. Only `agent_communication.py` expected `list[dict]`.
- **Agent-ID vs Job-ID**: `agent_id` = executor instance (UUID from `agent_executions` table), `job_id` = work order (UUID from `agent_jobs` table). Messages MUST route to executor for succession to work.
- **Default filtering**: `exclude_self=True` and `exclude_progress=True` are DEFAULTS (most agents want this). Callers can opt-out by passing `False`.

### Testing Strategy
1. **Unit tests first**: Verify each method in isolation
2. **Integration tests**: Verify succession scenario (most important)
3. **Manual UI testing**: Verify WebSocket counters update correctly
4. **Load testing**: Optional - send 100 messages, verify no performance regression

### Where to Ask for Help
- If uncertain about WebSocket events: Check `src/giljo_mcp/websocket_manager.py` for event schemas
- If uncertain about JSONB structure: Check `agent_jobs.messages` column in database
- If uncertain about filtering logic: Reference 0366b version (before deletion) for correct SQL

### Estimated Timeline
- **Phase 1 (Analysis)**: 30 minutes - verify comparison table accuracy
- **Phase 2 (Merge Strategy)**: 1 hour - review code changes, plan carefully
- **Phase 3 (Implementation)**: 2 hours - make changes, test incrementally
- **Phase 4 (Tests)**: 1.5 hours - migrate tests, add new scenarios
- **Phase 5 (Cleanup)**: 30 minutes - delete files, update docs
- **Phase 6 (Verification)**: 30 minutes - final testing, commit

**Total**: 4-6 hours (varies by familiarity with codebase)

---

## References

- **Handover 0366b**: `handovers/completed/0366b_service_layer_updates-C.md` - Original agent-ID refactor (incomplete)
- **Handover 0371**: `handovers/0371_dead_code_cleanup_project.md` - Dead code analysis that discovered this issue
- **MessageService API**: `docs/SERVICES.md` - Service layer documentation
- **Agent Identity**: `handovers/Reference_docs/UUID_INDEX_0366.md` - Agent-ID vs Job-ID reference

---

**END OF HANDOVER**

*This handover was created by the Documentation Manager Agent during dead code cleanup investigation (Handover 0371). It represents a critical missing piece of the Agent Identity Refactor (0366b) that was never completed.*
