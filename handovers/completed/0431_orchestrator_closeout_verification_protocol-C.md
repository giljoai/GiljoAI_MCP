# Handover 0431: Orchestrator Closeout Verification Protocol

**Status**: READY FOR IMPLEMENTATION
**Created**: 2026-01-22
**Complexity**: Medium (6-10 hours)
**Priority**: High (Prevents incomplete project closeouts)
**Dependencies**: Handover 0402 (AgentTodoItem table), Handover 0387i (Message counters)

---

## Pre-Implementation Required Reading

**CRITICAL**: Read these documents before starting:

1. **Quick Launch Guide**: `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`
2. **Agent Flow Summary**: `F:\GiljoAI_MCP\handovers\Reference_docs\AGENT_FLOW_SUMMARY.md`
3. **Existing Closeout**: `src/giljo_mcp/tools/project_closeout.py` (write_360_memory)
4. **Todo Model**: `src/giljo_mcp/models/agent_identity.py` (AgentTodoItem)
5. **Orchestrator Protocol**: `docs/ORCHESTRATOR.md` (CH5 completion protocol)

---

## TDD Protocol Reminder

**Test-Driven Development is MANDATORY**:

1. Write tests FIRST (before implementation code)
2. Run tests - they should FAIL (red)
3. Implement minimum code to make tests pass (green)
4. Refactor while keeping tests green
5. Repeat for next feature

**Coverage Target**: >80% for all new code

---

## Objective

Enhance `write_360_memory()` to enforce pre-closeout verification, preventing orchestrators from closing projects that have:
- Agents still working (status != 'complete')
- Agents with unread messages (`messages_waiting_count > 0`)
- Agents with incomplete todos (AgentTodoItem.status != 'completed')
- Orchestrator's own incomplete todos

---

## Problem Statement

### Current Behavior (Gap)

Orchestrator can call `write_360_memory()` → `complete_job()` without verification:

```
Agent A: [working] → [complete_job()] → [complete]
Agent B: [working] ... sends message to A ... → [complete]
Orchestrator: [write_360_memory()] → SUCCESS  <-- PROBLEM
```

Agent A never read Agent B's late message. Project closed with unfinished work.

### Why This Matters

In multi-terminal mode:
- Agents run asynchronously in separate terminals
- One agent may finish and send a message to another
- Receiving agent may complete before reading the message
- Orchestrator has no visibility into this state

**User Experience**: Project marked "complete" but work is actually incomplete.

---

## Solution: Self-Protecting `write_360_memory()`

Enhance `write_360_memory()` to check closeout readiness BEFORE writing memory.

### Tool Behavior Change

**Before (Current)**:
```python
write_360_memory(project_id, summary, ...) → {success: true}  # Always succeeds
```

**After (Enhanced)**:
```python
write_360_memory(project_id, summary, author_job_id, ...) →
  if ready:     {success: true, entry_id: ...}
  if not ready: {success: false, error: "CLOSEOUT_BLOCKED", blockers: [...]}
```

### Verification Checks (In Order)

| Check | Data Source | Blocker Type |
|-------|-------------|--------------|
| Agent not complete | `AgentExecution.status != 'complete'` | `still_working` |
| Unread messages | `AgentExecution.messages_waiting_count > 0` | `unread_messages` |
| Incomplete todos | `AgentTodoItem.status != 'completed'` | `incomplete_todos` |
| Orchestrator's own todos | Same check for `author_job_id` | `orchestrator_incomplete_todos` |

### Response Schema

**Success Response:**
```json
{
    "success": true,
    "entry_id": "uuid-xxx",
    "sequence_number": 5,
    "message": "360 Memory written successfully",
    "verified": {
        "agents_checked": 4,
        "all_complete": true,
        "all_messages_read": true,
        "all_todos_done": true
    }
}
```

**Blocked Response:**
```json
{
    "success": false,
    "error": "CLOSEOUT_BLOCKED",
    "message": "Cannot write 360 memory - project has unresolved blockers",
    "blockers": [
        {
            "agent_id": "uuid-1",
            "agent_name": "implementor-auth",
            "job_id": "job-uuid-1",
            "issue_type": "still_working",
            "status": "working"
        },
        {
            "agent_id": "uuid-2",
            "agent_name": "tester-unit",
            "job_id": "job-uuid-2",
            "issue_type": "unread_messages",
            "messages_waiting": 2
        },
        {
            "agent_id": "uuid-3",
            "agent_name": "reviewer-code",
            "job_id": "job-uuid-3",
            "issue_type": "incomplete_todos",
            "pending_count": 1,
            "in_progress_count": 1,
            "incomplete_items": ["Review auth module", "Check test coverage"]
        },
        {
            "agent_id": "orch-uuid",
            "agent_name": "orchestrator",
            "job_id": "orch-job-uuid",
            "issue_type": "orchestrator_incomplete_todos",
            "incomplete_items": ["Final verification"]
        }
    ],
    "summary": {
        "total_agents": 4,
        "still_working": 1,
        "agents_with_unread": 1,
        "agents_with_incomplete_todos": 2
    },
    "action_required": "Mark yourself BLOCKED via report_error(). Inform user of blockers. User must intervene in agent terminals."
}
```

---

## Implementation Plan

### Phase 1: Add Verification Function (TDD)

**Tests First** (`tests/tools/test_project_closeout.py`):

```python
@pytest.mark.asyncio
async def test_write_360_memory_blocks_when_agent_still_working(
    db_session, test_tenant, test_project, test_orchestrator_job
):
    """Should block closeout if any agent is still working"""
    # Create agent with status='working'
    working_agent = await create_test_agent(
        session=db_session,
        project_id=test_project.id,
        status="working",
        tenant_key=test_tenant
    )

    result = await write_360_memory(
        project_id=str(test_project.id),
        summary="Test summary",
        key_outcomes=["Outcome 1"],
        decisions_made=["Decision 1"],
        tenant_key=test_tenant,
        author_job_id=str(test_orchestrator_job.job_id),
        db_manager=db_manager
    )

    assert result["success"] is False
    assert result["error"] == "CLOSEOUT_BLOCKED"
    assert len(result["blockers"]) == 1
    assert result["blockers"][0]["issue_type"] == "still_working"


@pytest.mark.asyncio
async def test_write_360_memory_blocks_when_unread_messages(
    db_session, test_tenant, test_project, test_orchestrator_job
):
    """Should block closeout if any agent has unread messages"""
    # Create completed agent with unread messages
    agent_with_messages = await create_test_agent(
        session=db_session,
        project_id=test_project.id,
        status="complete",
        messages_waiting_count=3,
        tenant_key=test_tenant
    )

    result = await write_360_memory(...)

    assert result["success"] is False
    assert result["blockers"][0]["issue_type"] == "unread_messages"
    assert result["blockers"][0]["messages_waiting"] == 3


@pytest.mark.asyncio
async def test_write_360_memory_blocks_when_incomplete_todos(
    db_session, test_tenant, test_project, test_orchestrator_job
):
    """Should block closeout if any agent has incomplete todos"""
    # Create completed agent
    agent = await create_test_agent(
        session=db_session,
        project_id=test_project.id,
        status="complete",
        tenant_key=test_tenant
    )

    # Add incomplete todo
    todo = AgentTodoItem(
        job_id=agent.job_id,
        tenant_key=test_tenant,
        content="Unfinished task",
        status="pending",
        sequence=0
    )
    db_session.add(todo)
    await db_session.commit()

    result = await write_360_memory(...)

    assert result["success"] is False
    assert result["blockers"][0]["issue_type"] == "incomplete_todos"


@pytest.mark.asyncio
async def test_write_360_memory_checks_orchestrator_todos(
    db_session, test_tenant, test_project, test_orchestrator_job
):
    """Should block closeout if orchestrator has incomplete todos"""
    # Add incomplete todo for orchestrator
    orch_todo = AgentTodoItem(
        job_id=str(test_orchestrator_job.job_id),
        tenant_key=test_tenant,
        content="Final verification",
        status="in_progress",
        sequence=0
    )
    db_session.add(orch_todo)
    await db_session.commit()

    result = await write_360_memory(
        ...,
        author_job_id=str(test_orchestrator_job.job_id)
    )

    assert result["success"] is False
    assert result["blockers"][0]["issue_type"] == "orchestrator_incomplete_todos"


@pytest.mark.asyncio
async def test_write_360_memory_succeeds_when_all_ready(
    db_session, test_tenant, test_project, test_orchestrator_job
):
    """Should succeed when all agents complete, no unread, all todos done"""
    # Create completed agent with no issues
    agent = await create_test_agent(
        session=db_session,
        project_id=test_project.id,
        status="complete",
        messages_waiting_count=0,
        tenant_key=test_tenant
    )

    # Add completed todo
    todo = AgentTodoItem(
        job_id=agent.job_id,
        tenant_key=test_tenant,
        content="Finished task",
        status="completed",
        sequence=0
    )
    db_session.add(todo)
    await db_session.commit()

    result = await write_360_memory(
        project_id=str(test_project.id),
        summary="Test summary",
        key_outcomes=["Outcome 1"],
        decisions_made=["Decision 1"],
        tenant_key=test_tenant,
        author_job_id=str(test_orchestrator_job.job_id),
        db_manager=db_manager
    )

    assert result["success"] is True
    assert "entry_id" in result
    assert result["verified"]["all_complete"] is True
```

**Implementation** (`src/giljo_mcp/tools/project_closeout.py`):

```python
async def _check_closeout_readiness(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
    orchestrator_job_id: str
) -> dict[str, Any]:
    """
    Verify project is ready for closeout.

    Checks:
    1. All agents have status == 'complete'
    2. All agents have messages_waiting_count == 0
    3. All agents have all todos completed
    4. Orchestrator's own todos are completed

    Returns:
        {
            "ready_to_close": bool,
            "blockers": [...],
            "summary": {...}
        }
    """
    blockers = []

    # Get all agent executions for this project
    stmt = (
        select(AgentExecution, AgentJob)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            AgentJob.project_id == project_id,
            AgentJob.tenant_key == tenant_key
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    still_working_count = 0
    unread_count = 0
    incomplete_todos_count = 0

    for execution, job in rows:
        agent_info = {
            "agent_id": execution.agent_id,
            "agent_name": execution.agent_name or job.agent_name,
            "job_id": job.job_id
        }

        # Check 1: Agent still working
        if execution.status not in ("complete", "completed"):
            blockers.append({
                **agent_info,
                "issue_type": "still_working",
                "status": execution.status
            })
            still_working_count += 1
            continue  # Skip other checks if not complete

        # Check 2: Unread messages
        if execution.messages_waiting_count > 0:
            blockers.append({
                **agent_info,
                "issue_type": "unread_messages",
                "messages_waiting": execution.messages_waiting_count
            })
            unread_count += 1

        # Check 3: Incomplete todos
        todo_stmt = select(AgentTodoItem).where(
            AgentTodoItem.job_id == job.job_id,
            AgentTodoItem.tenant_key == tenant_key,
            AgentTodoItem.status != "completed"
        )
        todo_result = await session.execute(todo_stmt)
        incomplete_todos = todo_result.scalars().all()

        if incomplete_todos:
            pending = [t for t in incomplete_todos if t.status == "pending"]
            in_progress = [t for t in incomplete_todos if t.status == "in_progress"]
            blockers.append({
                **agent_info,
                "issue_type": "incomplete_todos",
                "pending_count": len(pending),
                "in_progress_count": len(in_progress),
                "incomplete_items": [t.content for t in incomplete_todos[:5]]  # Limit to 5
            })
            incomplete_todos_count += 1

    # Check 4: Orchestrator's own todos (if author_job_id provided)
    if orchestrator_job_id:
        orch_todo_stmt = select(AgentTodoItem).where(
            AgentTodoItem.job_id == orchestrator_job_id,
            AgentTodoItem.tenant_key == tenant_key,
            AgentTodoItem.status != "completed"
        )
        orch_todo_result = await session.execute(orch_todo_stmt)
        orch_incomplete = orch_todo_result.scalars().all()

        if orch_incomplete:
            blockers.append({
                "agent_id": "orchestrator",
                "agent_name": "orchestrator",
                "job_id": orchestrator_job_id,
                "issue_type": "orchestrator_incomplete_todos",
                "incomplete_items": [t.content for t in orch_incomplete[:5]]
            })
            incomplete_todos_count += 1

    return {
        "ready_to_close": len(blockers) == 0,
        "blockers": blockers,
        "summary": {
            "total_agents": len(rows),
            "still_working": still_working_count,
            "agents_with_unread": unread_count,
            "agents_with_incomplete_todos": incomplete_todos_count
        }
    }
```

### Phase 2: Integrate into write_360_memory()

Modify `write_360_memory()` to call verification first:

```python
async def write_360_memory(
    project_id: str,
    summary: str,
    key_outcomes: List[str],
    decisions_made: List[str],
    tenant_key: str,
    author_job_id: str,  # NEW: Required for orchestrator todo check
    entry_type: str = "project_completion",
    db_manager: Optional[DatabaseManager] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Write 360 memory entry with pre-closeout verification.

    IMPORTANT: This tool now enforces verification before writing.
    If verification fails, returns CLOSEOUT_BLOCKED error with blockers.
    """
    # ... existing validation ...

    async with session_ctx as active_session:
        # NEW: Verify closeout readiness FIRST
        readiness = await _check_closeout_readiness(
            session=active_session,
            project_id=project_id,
            tenant_key=tenant_key,
            orchestrator_job_id=author_job_id
        )

        if not readiness["ready_to_close"]:
            return {
                "success": False,
                "error": "CLOSEOUT_BLOCKED",
                "message": "Cannot write 360 memory - project has unresolved blockers",
                "blockers": readiness["blockers"],
                "summary": readiness["summary"],
                "action_required": (
                    "Mark yourself BLOCKED via report_error(). "
                    "Inform user of blockers. User must intervene in agent terminals."
                )
            }

        # Existing write logic continues if verification passes...
        # ... existing implementation ...

        return {
            "success": True,
            "entry_id": str(entry.id),
            "sequence_number": sequence_number,
            "message": "360 Memory written successfully",
            "verified": {
                "agents_checked": readiness["summary"]["total_agents"],
                "all_complete": True,
                "all_messages_read": True,
                "all_todos_done": True
            }
        }
```

### Phase 3: Update MCP Tool Registration

Update `src/giljo_mcp/mcp_tools_registry.py` to document new parameter:

```python
@mcp_tool(
    name="write_360_memory",
    description=(
        "Write a 360 memory entry for project completion or handover. "
        "IMPORTANT: This tool enforces pre-closeout verification. "
        "If any agents are still working, have unread messages, or have "
        "incomplete todos, the tool returns CLOSEOUT_BLOCKED error. "
        "On blocked response, orchestrator must report_error() and inform user."
    )
)
async def write_360_memory(
    project_id: str,
    summary: str,
    key_outcomes: list[str],
    decisions_made: list[str],
    tenant_key: str,
    author_job_id: str,  # Required for orchestrator todo check
    entry_type: str = "project_completion"
) -> dict[str, Any]:
    ...
```

### Phase 4: Update Orchestrator Protocol Documentation

Update `docs/ORCHESTRATOR.md` CH5:

```markdown
── CLOSEOUT PROTOCOL ───────────────────────────────────────────────────────

When all agents appear complete, attempt to write 360 Memory:

Call: write_360_memory(
          project_id='{project_id}',
          summary='2-3 paragraph mission accomplishment overview',
          key_outcomes=['Achievement 1', 'Achievement 2', ...],
          decisions_made=['Decision 1 + rationale', ...],
          entry_type='project_completion',
          author_job_id='{orchestrator_id}'  # REQUIRED for todo verification
      )

IF RESPONSE success=true:
  → Proceed to complete_job()
  → Project closeout successful

IF RESPONSE error="CLOSEOUT_BLOCKED":
  → Tool returns blockers array with specific issues

  1. Call report_error(job_id, "BLOCKED: Cannot close project - see blockers")

  2. Inform user of EACH blocker:
     - still_working: "Agent 'implementor-auth' is still working (status: working)"
     - unread_messages: "Agent 'tester-unit' has 2 unread messages"
     - incomplete_todos: "Agent 'reviewer-code' has incomplete todos: 'Review auth module'"
     - orchestrator_incomplete_todos: "My todo list has incomplete items: 'Final verification'"

  3. STOP - Do not proceed to complete_job()

  User intervention required:
  - Multi-terminal: User goes to agent terminal and says "Read your messages" or "Finish your work"
  - Claude Code CLI: User tells orchestrator to respawn agent or override

  After user intervention:
  4. User returns to orchestrator terminal
  5. Orchestrator calls acknowledge_job() to resume from BLOCKED
  6. Orchestrator re-attempts write_360_memory()
  7. If success=true, proceed to complete_job()
```

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `src/giljo_mcp/tools/project_closeout.py` | Add `_check_closeout_readiness()`, modify `write_360_memory()` | +120 |
| `tests/tools/test_project_closeout.py` | Add verification tests | +200 |
| `docs/ORCHESTRATOR.md` | Update CH5 closeout protocol | +40 |
| `src/giljo_mcp/mcp_tools_registry.py` | Update tool description | +5 |

**Total Estimated**: ~365 lines

---

## Testing Requirements

### Unit Tests (>80% coverage)

- `_check_closeout_readiness()` all code paths
- `write_360_memory()` blocked scenarios
- `write_360_memory()` success scenarios
- Multi-tenant isolation in verification
- Edge cases (no agents, all agents complete, mixed states)

### Integration Tests

- Full project lifecycle: spawn agents → complete → closeout
- Blocked closeout → user intervention → retry → success
- Multi-agent scenarios with mixed states

### E2E Validation

Manual test scenario:
1. Create project, spawn 2 agents
2. Agent 1 completes, Agent 2 still working
3. Orchestrator attempts write_360_memory() → BLOCKED
4. User completes Agent 2's work
5. Orchestrator retries → SUCCESS

---

## Success Criteria

### Functional Requirements

- `write_360_memory()` blocks when agents still working
- `write_360_memory()` blocks when agents have unread messages
- `write_360_memory()` blocks when agents have incomplete todos
- `write_360_memory()` blocks when orchestrator has incomplete todos
- `write_360_memory()` succeeds when all checks pass
- Blocked response includes actionable blocker details

### Quality Requirements

- Test coverage >80% for all new code
- No breaking changes to successful closeout path
- Multi-tenant isolation enforced
- Response schema documented and consistent

---

## Non-Goals (Out of Scope)

- New MCP tool (using enhanced `write_360_memory()` instead)
- Integration with 0419 long-polling (separate concern)
- Automatic agent recovery (user intervention required)
- Force-close parameter (user can manually override via existing tools)

---

## Security Considerations

### Multi-Tenant Isolation

- All queries filter by `tenant_key`
- Verification only sees agents in same tenant
- Test cross-tenant isolation

### Data Exposure

- Blocker response includes agent names and todo content
- This is intentional - orchestrator needs details to report to user
- No sensitive data exposed (just status, counts, task descriptions)

---

## Relationship to Handover 0419

**0419**: Long-polling for real-time monitoring DURING implementation phase
**0431**: One-time verification gate BEFORE closeout

These are complementary but separate:
- 0419: "Agent X just changed status" (continuous events)
- 0431: "Is everything ready to close?" (point-in-time check)

No integration needed. Both can exist independently.

---

## References

### Handovers

- **0402**: AgentTodoItem table (normalized todo storage)
- **0387i**: Message counters (messages_waiting_count)
- **0419**: Long-polling orchestrator monitoring (complementary)
- **0390**: 360 Memory normalized table

### Code References

- `src/giljo_mcp/tools/project_closeout.py` - write_360_memory()
- `src/giljo_mcp/models/agent_identity.py` - AgentExecution, AgentTodoItem
- `docs/ORCHESTRATOR.md` - CH5 completion protocol

---

## Checklist for Implementation Agent

Before starting:
- [ ] Read QUICK_LAUNCH.txt and AGENT_FLOW_SUMMARY.md
- [ ] Review existing write_360_memory() implementation
- [ ] Review AgentTodoItem model structure
- [ ] Understand TDD protocol

During implementation:
- [ ] Write unit tests FIRST (Phase 1)
- [ ] Implement `_check_closeout_readiness()` function
- [ ] Modify `write_360_memory()` to call verification
- [ ] Run tests (should pass), verify coverage >80%
- [ ] Update MCP tool registration and docs (Phase 3-4)

Before marking complete:
- [ ] All tests pass
- [ ] Coverage >80%
- [ ] Documentation updated
- [ ] Manual E2E validation
- [ ] No breaking changes to existing functionality

---

**END OF HANDOVER 0431**
