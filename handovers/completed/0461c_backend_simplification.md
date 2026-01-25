# Handover 0461c: Backend Simplification

**Series**: Handover Simplification Series (0461)
**Color**: Purple (#9C27B0)
**Estimated Effort**: 8-12 hours
**Subagents**: `tdd-implementor`, `backend-tester`
**Dependencies**: 0461b (need session_handover entry type)

---

## Mission Statement

Replace the complex Agent ID Swap succession mechanism with a simple 360 Memory-based handover. Instead of creating multiple `AgentExecution` rows with swapped IDs, we:

1. Write session context to 360 Memory
2. Reset context_used counter
3. New session reads 360 Memory to continue

**Key Change**: No more Agent ID Swap, no more instance numbering, no more succession chains. Just session context in 360 Memory.

---

## Background

### Current Complex Flow (Agent ID Swap)

```
1. User clicks "Hand Over"
2. API calls trigger_succession()
3. OrchestratorSuccessionManager.create_successor():
   - Generate decomm-xxx ID for old orchestrator
   - Create new AgentExecution row with instance_number + 1
   - Old orchestrator gets decomm ID
   - New orchestrator takes original ID
4. Generate handover summary in JSONB column
5. Return launch prompt for new terminal
6. User copies prompt to new terminal
7. New orchestrator finds its row by agent_id
```

### New Simple Flow (360 Memory)

```
1. User clicks "Hand Over" (renamed: "Refresh Session")
2. API calls simple_handover():
   - Write session_handover entry to 360 Memory
   - Reset execution.context_used = 0
   - Emit orchestrator:context_reset WebSocket event
3. Return continuation prompt
4. User copies prompt to SAME or NEW terminal
5. New session calls fetch_context(categories=["memory_360"])
6. Reads session_handover entry, continues work
```

---

## Tasks

### Task 1: Create Simple Handover Endpoint

**File**: `api/endpoints/agent_jobs/simple_handover.py` (NEW FILE)

Create a new endpoint that replaces the complex succession logic:

```python
"""
Simple Handover Endpoint - Handover 0461c

Replaces complex Agent ID Swap with 360 Memory-based session continuity.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/{job_id}/simple-handover",
    summary="Simple session handover via 360 Memory",
    description="Write session context to 360 Memory and return continuation prompt",
    tags=["agent-jobs", "handover"]
)
async def simple_handover(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Simple handover: Write session to 360 Memory and reset context.

    Does NOT create new AgentExecution rows. Instead:
    1. Gathers current session context
    2. Writes session_handover entry to 360 Memory
    3. Resets context_used to 0
    4. Returns continuation prompt that reads 360 Memory

    Args:
        job_id: Orchestrator job_id or agent_id
        current_user: Authenticated user
        db: Database session

    Returns:
        {
            "success": True,
            "continuation_prompt": "...",
            "memory_entry_id": "...",
            "context_reset": True
        }
    """
    try:
        # Find execution (job_id could be agent_id)
        stmt = select(AgentExecution).where(
            AgentExecution.agent_id == job_id,
            AgentExecution.tenant_key == current_user.tenant_key
        ).order_by(AgentExecution.instance_number.desc()).limit(1)
        result = await db.execute(stmt)
        execution = result.scalars().first()

        # Fallback to job_id
        if not execution:
            stmt = select(AgentExecution).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == current_user.tenant_key
            ).order_by(AgentExecution.instance_number.desc()).limit(1)
            result = await db.execute(stmt)
            execution = result.scalars().first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        if execution.agent_display_name != "orchestrator":
            raise HTTPException(status_code=400, detail="Only orchestrators can use handover")

        # Get job for project_id
        stmt = select(AgentJob).where(AgentJob.job_id == execution.job_id)
        result = await db.execute(stmt)
        job = result.scalars().first()

        if not job:
            raise HTTPException(status_code=500, detail="Job not found")

        # Build session context for 360 Memory
        session_context = {
            "context_used": execution.context_used,
            "context_budget": execution.context_budget,
            "progress": execution.progress,
            "current_task": execution.current_task,
            "agent_id": execution.agent_id,
            "job_id": execution.job_id,
        }

        # Write to 360 Memory
        from src.giljo_mcp.tools.write_360_memory import write_360_memory

        memory_result = await write_360_memory(
            project_id=str(job.project_id),
            summary=f"Session handover at {execution.context_used}/{execution.context_budget} tokens ({(execution.context_used/execution.context_budget*100):.0f}% context used).",
            key_outcomes=[f"Progress: {execution.progress}%", f"Current task: {execution.current_task or 'N/A'}"],
            decisions_made=["Session handover triggered by user"],
            entry_type="session_handover",
            author_job_id=execution.job_id,
            tenant_key=current_user.tenant_key,
            metrics={"session_context": session_context}
        )

        # Reset context_used
        old_context = execution.context_used
        execution.context_used = 0
        await db.commit()

        # Generate continuation prompt
        prompt_generator = ThinClientPromptGenerator(
            db=db,
            tenant_key=current_user.tenant_key
        )

        prompt_result = await prompt_generator.generate(
            project_id=str(job.project_id),
            user_id=str(current_user.id),
            continuation_mode=True  # NEW: Tell generator to read 360 Memory
        )

        # Emit WebSocket event
        try:
            from api.app import state
            if state.websocket_manager:
                await state.websocket_manager.broadcast_to_tenant(
                    tenant_key=current_user.tenant_key,
                    event_type="orchestrator:context_reset",
                    data={
                        "agent_id": execution.agent_id,
                        "job_id": execution.job_id,
                        "project_id": str(job.project_id),
                        "old_context_used": old_context,
                        "new_context_used": 0,
                        "memory_entry_created": True,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
        except Exception as ws_error:
            logger.warning(f"WebSocket broadcast failed: {ws_error}")

        return {
            "success": True,
            "continuation_prompt": prompt_result.get("thin_prompt", ""),
            "memory_entry_id": memory_result.get("entry_id"),
            "context_reset": True,
            "old_context_used": old_context,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Simple handover failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Task 2: Register New Endpoint

**File**: `api/endpoints/agent_jobs/__init__.py`

Add the new router:

```python
from .simple_handover import router as simple_handover_router

# In the list of routers to include:
# simple_handover_router
```

**File**: `api/app.py` (or wherever routers are registered)

Include the new router:

```python
from api.endpoints.agent_jobs.simple_handover import router as simple_handover_router

app.include_router(simple_handover_router, prefix="/api/agent-jobs", tags=["agent-jobs"])
```

### Task 3: Update ThinClientPromptGenerator

**File**: `src/giljo_mcp/thin_prompt_generator.py`

Update `_generate_continuation_prompt()` to read 360 Memory:

**Current method** (lines 1088-1155): Generates prompt with hardcoded instructions.

**New method**: Read 360 Memory for session context.

```python
def _generate_continuation_prompt(
    self,
    project_name: str,
    agent_id: str,
    orchestrator_id: str,
    project_id: str,
    product_id: str,  # NEW: Need product_id for fetch_context
    instance_number: int,
    mcp_url: str,
) -> str:
    """
    Generate continuation prompt that reads 360 Memory.

    Handover 0461c: Instead of hardcoded instructions, tell successor
    to read 360 Memory for session context.
    """
    prompt = f"""I am Orchestrator for Project "{project_name}" (CONTINUATION SESSION).

A previous session ran out of context. I am continuing the work.

YOUR IDENTITY (use these in all MCP calls):
  YOUR Agent ID: {agent_id}
  YOUR Job ID: {orchestrator_id}
  THE Project ID: {project_id}
  THE Product ID: {product_id}

MCP Server: {mcp_url}
Note: tenant_key is auto-injected by server from your API key session

FIRST ACTIONS (DO NOT RE-STAGE):

1. Verify MCP: mcp__giljo-mcp__health_check()
   → Expected: {{"status": "healthy"}}

2. Read 360 Memory for session context:
   mcp__giljo-mcp__fetch_context(
       product_id="{product_id}",
       categories=["memory_360"]
   )
   → Look for "session_handover" entry with session context
   → Contains: previous context_used, progress, current_task

3. Check messages from agents:
   mcp__giljo-mcp__receive_messages(agent_id="{agent_id}")

4. Check workflow status:
   mcp__giljo-mcp__get_workflow_status(project_id="{project_id}")

CRITICAL RULES:
- Do NOT call get_orchestrator_instructions() to re-stage
- Do NOT re-write the project mission
- Read 360 Memory session_handover for context from previous session
- You are CONTINUING work, not starting from scratch

When ready, coordinate agents based on current status.
"""
    return prompt
```

Also update the `generate()` method to accept `continuation_mode` parameter:

```python
async def generate(
    self,
    project_id: str,
    user_id: str,
    continuation_mode: bool = False,  # NEW parameter
    instance_number: int = 1,  # DEPRECATED but kept for compatibility
) -> dict:
    """
    Generate thin client prompt.

    Args:
        project_id: Project UUID
        user_id: User UUID
        continuation_mode: If True, generate continuation prompt (reads 360 Memory)
        instance_number: DEPRECATED - kept for backward compatibility only
    """
    # ... existing logic ...

    if continuation_mode:
        # Generate continuation prompt that reads 360 Memory
        prompt = self._generate_continuation_prompt(
            project_name=project.name,
            agent_id=orchestrator_execution.agent_id,
            orchestrator_id=orchestrator_job.job_id,
            project_id=str(project.id),
            product_id=str(project.product_id),
            instance_number=1,  # Always 1 in new model
            mcp_url=mcp_url,
        )
    else:
        # Normal staging prompt
        prompt = self._build_thin_prompt(...)

    return {"thin_prompt": prompt, ...}
```

### Task 4: Simplify OrchestrationService.trigger_succession()

**File**: `src/giljo_mcp/services/orchestration_service.py`

Replace the complex Agent ID Swap logic with a redirect to simple_handover:

**Current method** (lines 2022-2119): Complex Agent ID Swap with OrchestratorSuccessionManager.

**New method**: Simplified, calls simple handover logic:

```python
async def trigger_succession(
    self, job_id: str, reason: str = "manual", tenant_key: Optional[str] = None, agent_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Trigger orchestrator handover (simplified - Handover 0461c).

    DEPRECATED: This method is deprecated. Use simple_handover endpoint instead.

    This now delegates to simple handover logic:
    1. Write session_handover to 360 Memory
    2. Reset context_used to 0
    3. Return continuation prompt info

    No more Agent ID Swap. No new AgentExecution rows.
    """
    async with self._get_session() as session:
        # Find execution
        executor_id = agent_id or job_id

        query = select(AgentExecution).where(AgentExecution.agent_id == executor_id)
        if tenant_key:
            query = query.where(AgentExecution.tenant_key == tenant_key)
        query = query.order_by(AgentExecution.instance_number.desc()).limit(1)

        result = await session.execute(query)
        execution = result.scalar_one_or_none()

        if not execution:
            # Fallback to job_id
            query = select(AgentExecution).where(AgentExecution.job_id == executor_id)
            if tenant_key:
                query = query.where(AgentExecution.tenant_key == tenant_key)
            query = query.order_by(AgentExecution.instance_number.desc()).limit(1)
            result = await session.execute(query)
            execution = result.scalar_one_or_none()

        if not execution:
            raise ValueError("Execution not found")

        if execution.agent_display_name != "orchestrator":
            raise ValueError("Only orchestrator agents can trigger succession")

        # Get job for project_id
        job_query = select(AgentJob).where(AgentJob.job_id == execution.job_id)
        job_result = await session.execute(job_query)
        job = job_result.scalar_one_or_none()

        if not job:
            raise ValueError("Job not found")

        # Write to 360 Memory
        from src.giljo_mcp.tools.write_360_memory import write_360_memory

        session_context = {
            "context_used": execution.context_used,
            "context_budget": execution.context_budget,
            "progress": execution.progress,
            "current_task": execution.current_task,
            "reason": reason,
        }

        await write_360_memory(
            project_id=str(job.project_id),
            summary=f"Session handover ({reason}) at {execution.context_used}/{execution.context_budget} tokens.",
            key_outcomes=[f"Progress: {execution.progress}%"],
            decisions_made=[f"Handover triggered: {reason}"],
            entry_type="session_handover",
            author_job_id=execution.job_id,
            tenant_key=tenant_key or execution.tenant_key,
            metrics={"session_context": session_context}
        )

        # Reset context
        old_context = execution.context_used
        execution.context_used = 0
        await session.commit()

        self._logger.info(
            f"Simple handover: {execution.agent_id} context reset "
            f"({old_context} -> 0), reason: {reason}"
        )

        # Return simplified response (backward compatible fields)
        return {
            "success": True,
            "job_id": execution.job_id,
            "successor_agent_id": execution.agent_id,  # Same agent, no swap
            "decommissioned_agent_id": None,  # No decommissioning
            "successor_instance_number": execution.instance_number,  # Same instance
            "instance_number": execution.instance_number,
            "reason": reason,
            "context_reset": True,
            "old_context_used": old_context,
        }
```

### Task 5: Update /gil_handover Slash Command

**File**: `src/giljo_mcp/slash_commands/handover.py` (or similar)

Find the slash command implementation and update to use simple handover:

```python
# Update the handover command to:
# 1. Call simple_handover endpoint
# 2. Return continuation prompt
# 3. Remove references to Agent ID Swap

# The prompt should instruct:
# - Write session context to 360 Memory (automatic via endpoint)
# - Copy continuation prompt
# - Continue in same or new terminal
```

### Task 6: Remove OrchestratorSuccessionManager Usage (Optional)

After the above changes, `OrchestratorSuccessionManager` methods are no longer called:
- `create_successor()` - Not used
- `generate_handover_summary()` - Not used (context goes to 360 Memory instead)
- `complete_handover()` - Not used

**Note**: Don't delete the file in this handover. Just ensure nothing calls these methods. The file will be removed in a future cleanup handover.

### Task 7: Update API Endpoint Registration

**File**: `api/endpoints/agent_jobs/__init__.py`

Ensure the new endpoint is properly exported:

```python
from .simple_handover import router as simple_handover_router

__all__ = [
    # ... existing exports ...
    "simple_handover_router",
]
```

---

## Verification

### Unit Tests

Create tests for the new simple handover:

```python
# tests/api/test_simple_handover.py

async def test_simple_handover_writes_360_memory(client, test_orchestrator):
    """Simple handover writes session_handover to 360 Memory."""
    response = await client.post(
        f"/api/agent-jobs/{test_orchestrator.job_id}/simple-handover"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["context_reset"] is True
    assert "continuation_prompt" in data

async def test_simple_handover_resets_context(client, test_orchestrator):
    """Simple handover resets context_used to 0."""
    # Set some context usage first
    test_orchestrator.context_used = 100000
    await db.commit()

    response = await client.post(
        f"/api/agent-jobs/{test_orchestrator.job_id}/simple-handover"
    )
    assert response.status_code == 200

    # Verify context reset
    await db.refresh(test_orchestrator)
    assert test_orchestrator.context_used == 0

async def test_continuation_prompt_mentions_360_memory(client, test_orchestrator):
    """Continuation prompt instructs reading 360 Memory."""
    response = await client.post(
        f"/api/agent-jobs/{test_orchestrator.job_id}/simple-handover"
    )
    prompt = response.json()["continuation_prompt"]
    assert "fetch_context" in prompt
    assert "memory_360" in prompt
    assert "session_handover" in prompt
```

### Integration Test

```bash
pytest tests/api/test_simple_handover.py -v
pytest tests/services/test_orchestration_service.py -v -k "succession"
```

### Full Test Suite

```bash
pytest tests/ -v
```

---

## Files Modified Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `api/endpoints/agent_jobs/simple_handover.py` | CREATE | ~150 lines |
| `api/endpoints/agent_jobs/__init__.py` | UPDATE | ~5 lines |
| `api/app.py` | UPDATE | ~5 lines |
| `src/giljo_mcp/thin_prompt_generator.py` | UPDATE | ~50 lines |
| `src/giljo_mcp/services/orchestration_service.py` | SIMPLIFY | ~100 lines changed |
| `src/giljo_mcp/slash_commands/handover.py` | UPDATE | ~30 lines |
| `tests/api/test_simple_handover.py` | CREATE | ~80 lines |

**Total**: ~15 files, ~500 lines (net reduction after simplification)

---

## Success Criteria

- [ ] New `/api/agent-jobs/{job_id}/simple-handover` endpoint created
- [ ] Endpoint writes `session_handover` to 360 Memory
- [ ] Endpoint resets `context_used` to 0
- [ ] Endpoint emits `orchestrator:context_reset` WebSocket event
- [ ] Continuation prompt instructs reading 360 Memory
- [ ] `trigger_succession()` simplified (no Agent ID Swap)
- [ ] Slash command updated
- [ ] All tests pass
- [ ] No new `AgentExecution` rows created during handover

---

## Backward Compatibility

The response from `trigger_succession()` maintains the same structure for backward compatibility:
- `job_id`: Same value
- `successor_agent_id`: Same as current agent_id (no swap)
- `decommissioned_agent_id`: `None` (no decommissioning)
- `instance_number`: Same (no increment)

Frontend code expecting these fields will still work, but values won't change.

---

## Rollback

If issues arise:
```bash
git checkout HEAD -- src/giljo_mcp/services/orchestration_service.py
git checkout HEAD -- src/giljo_mcp/thin_prompt_generator.py
# Remove new file:
rm api/endpoints/agent_jobs/simple_handover.py
```

---

## Next Handover

After 0461c completes, proceed to **0461d: Frontend Simplification**.
