# Handover 0246c: Execution Mode Preservation Through Succession

**Date**: 2025-11-24
**Status**: READY FOR IMPLEMENTATION
**Priority**: MEDIUM
**Type**: Enhancement (Orchestrator Succession)
**Builds Upon**: Handover 0246a (Frontend Toggle Connection)
**Estimated Time**: 6-8 hours

---

## Executive Summary

Preserve execution mode through orchestrator succession to ensure consistent agent spawning behavior across orchestrator handovers.

**Current Problem**:
- Orchestrator_A runs in "claude-code" mode (uses Task tool)
- Orchestrator_A hits 90% context capacity → triggers succession
- Orchestrator_B spawns with default "multi-terminal" mode
- User confused: "Why is orchestrator asking me to start agents manually?"

**Solution**:
- Include execution mode in handover context
- Successor inherits predecessor's execution mode
- Mode consistency maintained across entire project lifecycle

**Result**:
- Seamless succession without mode changes
- Consistent user experience throughout project
- No manual mode reconfiguration needed

---

## Problem Statement

### The Succession Risk

**Scenario**:
1. User starts project in **Claude Code mode**
2. Orchestrator_A spawns with mode = "claude-code"
3. Orchestrator_A uses Task tool to spawn subagents (single terminal workflow)
4. Orchestrator_A hits 90% context capacity
5. System triggers automatic succession (handover to Orchestrator_B)
6. **Problem**: Orchestrator_B spawns with mode = "multi-terminal" (default)
7. **Result**: Orchestrator_B tries to use message passing, but user expects Task tool
8. **User Experience**: "Why did the workflow change mid-execution?"

### Why This Breaks User Flow

**User Perspective**:
- Started project in Claude Code mode (single terminal)
- Orchestrator was using Task tool (@implementer, @tester, etc.)
- Suddenly asked to start agents in separate terminals
- Confusion: "Did something break? Why did the mode change?"

**Technical Perspective**:
- Execution mode stored in `project.meta_data['execution_mode']`
- Succession context includes project data but not explicit mode
- Successor spawns with default mode (multi-terminal)
- Mode information lost during handover

---

## Solution Overview

### What We're Building

**Component 1: Mode Inclusion in Handover Context**
- Fetch execution mode from project metadata
- Include mode in `_create_handover_summary()`
- Pass mode to successor during spawning

**Component 2: Successor Mode Inheritance**
- Successor reads mode from handover context
- Successor spawns with same mode as predecessor
- Mode consistency validated during succession

**Component 3: Mode Validation**
- Verify mode exists in project metadata
- Log warning if mode missing (legacy projects)
- Default to "multi-terminal" if not set

### Architecture

**Current Succession Flow (Mode Lost)**:
```
Orchestrator_A (claude-code mode)
    ↓ [Hits 90% context]
trigger_succession(current_job_id, reason="context_limit")
    ↓
create_handover_summary(current_job_id)
    ↓
spawn_orchestrator(project_id, handover_context)  ← Mode NOT included
    ↓
Orchestrator_B (multi-terminal mode - DEFAULT)  ← Wrong mode!
```

**Target Succession Flow (Mode Preserved)**:
```
Orchestrator_A (claude-code mode)
    ↓ [Hits 90% context]
trigger_succession(current_job_id, reason="context_limit")
    ↓
_get_project(project_id) → execution_mode = "claude-code"
    ↓
create_handover_summary(current_job_id, include_execution_mode=True)
    ↓
spawn_orchestrator(project_id, handover_context, execution_mode="claude-code")
    ↓
Orchestrator_B (claude-code mode)  ← Correct mode!
```

---

## Implementation Details

### Phase 1: Fetch Mode from Project (2-3 hours)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\services\orchestration_service.py`

**Current `trigger_succession()` Method** (Lines 977-1046):

```python
async def trigger_succession(
    self,
    current_job_id: str,
    reason: str = "context_limit"
) -> Dict[str, Any]:
    """
    Trigger orchestrator succession (handover to new instance).

    Args:
        current_job_id: Current orchestrator job UUID
        reason: Succession reason (context_limit, manual, phase_transition)

    Returns:
        dict with success/data/error
    """
    try:
        # Get current job
        current_job = await self._get_job(current_job_id)

        # Create handover summary
        handover_summary = await self._create_handover_summary(current_job_id)

        # Spawn successor
        successor = await self.spawn_orchestrator(
            project_id=current_job.project_id,
            spawned_by=current_job_id,
            handover_context=handover_summary
        )

        return {"success": True, "data": successor}

    except Exception as e:
        logger.error(f"Failed to trigger succession: {e}")
        return {"success": False, "error": str(e)}
```

**Add Mode Fetching**:

```python
async def trigger_succession(
    self,
    current_job_id: str,
    reason: str = "context_limit"
) -> Dict[str, Any]:
    """
    Trigger orchestrator succession (handover to new instance).

    Handover 0246c: Preserves execution mode through succession.

    Args:
        current_job_id: Current orchestrator job UUID
        reason: Succession reason (context_limit, manual, phase_transition)

    Returns:
        dict with success/data/error
    """
    try:
        # Get current job
        current_job = await self._get_job(current_job_id)

        # NEW: Fetch execution mode from project metadata
        project = await self._get_project(current_job.project_id)
        execution_mode = project.meta_data.get('execution_mode', 'multi-terminal')

        logger.info(
            "Triggering orchestrator succession",
            extra={
                "current_job_id": current_job_id,
                "project_id": current_job.project_id,
                "execution_mode": execution_mode,  # NEW
                "reason": reason
            }
        )

        # Create handover summary with mode
        handover_summary = await self._create_handover_summary(
            current_job_id,
            include_execution_mode=True  # NEW
        )

        # Spawn successor with same mode
        successor = await self.spawn_orchestrator(
            project_id=current_job.project_id,
            spawned_by=current_job_id,
            handover_context=handover_summary,
            execution_mode=execution_mode  # NEW: Preserved!
        )

        return {"success": True, "data": successor}

    except Exception as e:
        logger.error(f"Failed to trigger succession: {e}")
        return {"success": False, "error": str(e)}
```

**Add Helper Method**:

```python
async def _get_project(self, project_id: str):
    """Get project by ID (tenant-isolated)"""
    from src.giljo_mcp.models import Project
    from sqlalchemy import select

    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == self.tenant_key
    )
    result = await self.session.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise ValueError(f"Project {project_id} not found")

    return project
```

**Estimated Time**: 2-3 hours

---

### Phase 2: Include Mode in Handover Summary (2-3 hours)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\services\orchestration_service.py`

**Current `_create_handover_summary()` Method**:

```python
async def _create_handover_summary(
    self,
    current_job_id: str
) -> dict:
    """Create condensed handover summary (<10K tokens)"""

    # Fetch current job data
    current_job = await self._get_job(current_job_id)

    # Build summary
    summary = {
        "predecessor_id": current_job_id,
        "project_id": current_job.project_id,
        "context_used": current_job.context_used,
        "context_budget": current_job.context_budget,
        "mission_condensed": current_job.mission[:10000],  # Truncate
        "agent_jobs": await self._get_active_agent_jobs(current_job.project_id),
        "timestamp": datetime.utcnow().isoformat()
    }

    return summary
```

**Add Mode to Summary**:

```python
async def _create_handover_summary(
    self,
    current_job_id: str,
    include_execution_mode: bool = False  # NEW parameter
) -> dict:
    """
    Create condensed handover summary (<10K tokens).

    Handover 0246c: Includes execution mode when requested.

    Args:
        current_job_id: Current orchestrator job UUID
        include_execution_mode: Include execution mode in summary

    Returns:
        dict with handover context
    """

    # Fetch current job data
    current_job = await self._get_job(current_job_id)

    # Build summary
    summary = {
        "predecessor_id": current_job_id,
        "project_id": current_job.project_id,
        "context_used": current_job.context_used,
        "context_budget": current_job.context_budget,
        "mission_condensed": current_job.mission[:10000],
        "agent_jobs": await self._get_active_agent_jobs(current_job.project_id),
        "timestamp": datetime.utcnow().isoformat()
    }

    # NEW: Include execution mode if requested
    if include_execution_mode:
        project = await self._get_project(current_job.project_id)
        execution_mode = project.meta_data.get('execution_mode', 'multi-terminal')

        summary["execution_mode"] = execution_mode

        logger.info(
            "Execution mode included in handover summary",
            extra={
                "current_job_id": current_job_id,
                "execution_mode": execution_mode
            }
        )

    return summary
```

**Estimated Time**: 2-3 hours

---

### Phase 3: Successor Mode Inheritance (2 hours)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\services\orchestration_service.py`

**Current `spawn_orchestrator()` Method**:

```python
async def spawn_orchestrator(
    self,
    project_id: str,
    spawned_by: str = None,
    handover_context: dict = None
) -> dict:
    """Spawn new orchestrator job"""

    # Create job
    job = MCPAgentJob(
        project_id=project_id,
        tenant_key=self.tenant_key,
        agent_type="orchestrator",
        status="staging",
        mission="...",  # Generated later
        spawned_by=spawned_by,
        handover_context=handover_context
    )

    self.session.add(job)
    await self.session.commit()

    return job
```

**Add Mode Parameter**:

```python
async def spawn_orchestrator(
    self,
    project_id: str,
    spawned_by: str = None,
    handover_context: dict = None,
    execution_mode: str = None  # NEW parameter
) -> dict:
    """
    Spawn new orchestrator job.

    Handover 0246c: Accepts execution mode for succession preservation.

    Args:
        project_id: Project UUID
        spawned_by: Predecessor job ID (for succession)
        handover_context: Context from predecessor
        execution_mode: Execution mode (claude-code or multi-terminal)

    Returns:
        dict with spawned job
    """

    # NEW: Validate execution mode
    if execution_mode and execution_mode not in ['claude-code', 'multi-terminal']:
        logger.warning(
            f"Invalid execution mode '{execution_mode}', defaulting to 'multi-terminal'",
            extra={"project_id": project_id}
        )
        execution_mode = 'multi-terminal'

    # NEW: If mode not provided, fetch from project
    if not execution_mode:
        project = await self._get_project(project_id)
        execution_mode = project.meta_data.get('execution_mode', 'multi-terminal')

    logger.info(
        "Spawning orchestrator",
        extra={
            "project_id": project_id,
            "execution_mode": execution_mode,
            "spawned_by": spawned_by,
            "is_succession": bool(spawned_by)
        }
    )

    # Create job
    job = MCPAgentJob(
        project_id=project_id,
        tenant_key=self.tenant_key,
        agent_type="orchestrator",
        status="staging",
        mission="...",
        spawned_by=spawned_by,
        handover_context=handover_context,
        # NEW: Store mode in job metadata
        metadata={"execution_mode": execution_mode}
    )

    self.session.add(job)
    await self.session.commit()

    return {"success": True, "data": job}
```

**Estimated Time**: 2 hours

---

## Testing Requirements (TDD)

### RED Phase (Write Failing Tests First)

**Test File**: `F:\GiljoAI_MCP\tests\integration\test_succession_mode_preservation.py`

```python
import pytest
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models import MCPAgentJob, Project

@pytest.mark.asyncio
async def test_execution_mode_preserved_through_succession(
    db_session,
    test_project,
    test_tenant
):
    """Test execution mode preserved during orchestrator succession"""

    # Set project execution mode
    test_project.meta_data = {"execution_mode": "claude-code"}
    await db_session.commit()

    # Create orchestrator_A
    service = OrchestrationService(session=db_session, tenant_key=test_tenant)

    orchestrator_a = MCPAgentJob(
        project_id=test_project.id,
        tenant_key=test_tenant,
        agent_type="orchestrator",
        status="working",
        mission="Test mission",
        context_used=90000,  # 90% capacity
        context_budget=100000
    )
    db_session.add(orchestrator_a)
    await db_session.commit()

    # Trigger succession
    result = await service.trigger_succession(
        current_job_id=str(orchestrator_a.id),
        reason="context_limit"
    )

    assert result["success"] is True
    successor = result["data"]

    # BEHAVIOR: Successor inherits claude-code mode
    assert successor.metadata["execution_mode"] == "claude-code"


@pytest.mark.asyncio
async def test_handover_summary_includes_execution_mode(
    db_session,
    test_project,
    test_tenant
):
    """Test handover summary includes execution mode"""

    # Set project execution mode
    test_project.meta_data = {"execution_mode": "multi-terminal"}
    await db_session.commit()

    # Create orchestrator
    orchestrator = MCPAgentJob(
        project_id=test_project.id,
        tenant_key=test_tenant,
        agent_type="orchestrator",
        status="working",
        mission="Test"
    )
    db_session.add(orchestrator)
    await db_session.commit()

    # Create handover summary
    service = OrchestrationService(session=db_session, tenant_key=test_tenant)
    summary = await service._create_handover_summary(
        current_job_id=str(orchestrator.id),
        include_execution_mode=True
    )

    # BEHAVIOR: Summary includes mode
    assert "execution_mode" in summary
    assert summary["execution_mode"] == "multi-terminal"


@pytest.mark.asyncio
async def test_mode_defaults_to_multi_terminal_if_not_set(
    db_session,
    test_project,
    test_tenant
):
    """Test legacy projects without mode default to multi-terminal"""

    # Legacy project (no execution mode in metadata)
    test_project.meta_data = {}
    await db_session.commit()

    # Create orchestrator
    orchestrator = MCPAgentJob(
        project_id=test_project.id,
        tenant_key=test_tenant,
        agent_type="orchestrator",
        status="working",
        mission="Test"
    )
    db_session.add(orchestrator)
    await db_session.commit()

    # Trigger succession
    service = OrchestrationService(session=db_session, tenant_key=test_tenant)
    result = await service.trigger_succession(
        current_job_id=str(orchestrator.id),
        reason="context_limit"
    )

    successor = result["data"]

    # BEHAVIOR: Defaults to multi-terminal
    assert successor.metadata["execution_mode"] == "multi-terminal"


@pytest.mark.asyncio
async def test_mode_consistency_across_multiple_successions(
    db_session,
    test_project,
    test_tenant
):
    """Test mode preserved across multiple orchestrator successions"""

    # Set initial mode
    test_project.meta_data = {"execution_mode": "claude-code"}
    await db_session.commit()

    service = OrchestrationService(session=db_session, tenant_key=test_tenant)

    # Orchestrator_A
    orch_a = MCPAgentJob(
        project_id=test_project.id,
        tenant_key=test_tenant,
        agent_type="orchestrator",
        status="working",
        mission="Test",
        context_used=90000,
        context_budget=100000
    )
    db_session.add(orch_a)
    await db_session.commit()

    # Succession 1: A → B
    result_b = await service.trigger_succession(str(orch_a.id), "context_limit")
    orch_b = result_b["data"]
    assert orch_b.metadata["execution_mode"] == "claude-code"

    # Succession 2: B → C
    orch_b.context_used = 90000
    orch_b.context_budget = 100000
    await db_session.commit()

    result_c = await service.trigger_succession(str(orch_b.id), "context_limit")
    orch_c = result_c["data"]

    # BEHAVIOR: Mode preserved across chain A → B → C
    assert orch_c.metadata["execution_mode"] == "claude-code"
```

**Run Tests (Must See RED)**:
```bash
pytest tests/integration/test_succession_mode_preservation.py -v
# EXPECTED: FAILED (implementation not yet complete)
```

---

### GREEN Phase (Minimal Implementation)

Implement Phases 1-3 above.

**Run Tests (Must See GREEN)**:
```bash
pytest tests/integration/test_succession_mode_preservation.py -v
# EXPECTED: PASSED (all tests green)
```

---

### REFACTOR Phase (Polish)

**Optimizations**:
- Extract mode fetching into helper method
- Add validation for mode values
- Add comprehensive logging
- Optimize database queries

**Run Tests (Must Stay GREEN)**:
```bash
pytest tests/integration/test_succession_mode_preservation.py -v
# EXPECTED: PASSED (tests still green after refactor)
```

---

## Success Criteria

### Functional Requirements

**Must Have**:
- ✅ Execution mode fetched from project metadata during succession
- ✅ Mode included in handover summary
- ✅ Successor spawns with same mode as predecessor
- ✅ Mode consistency validated across multiple successions
- ✅ Legacy projects default to "multi-terminal"

**Nice to Have**:
- ✅ Mode validation (reject invalid values)
- ✅ Logging mode changes during succession
- ✅ WebSocket event on mode preservation

### Testing Requirements

**Test Coverage**:
- ✅ >80% coverage on new code
- ✅ Integration tests for succession
- ✅ Mode consistency tests
- ✅ Legacy project handling

**Test Cases**:
1. ✅ Mode preserved: claude-code → claude-code
2. ✅ Mode preserved: multi-terminal → multi-terminal
3. ✅ Legacy project defaults to multi-terminal
4. ✅ Mode preserved across chain (A → B → C)
5. ✅ Invalid mode defaults to multi-terminal

---

## Edge Cases & Mitigations

### Edge Case 1: Mode Changed Mid-Succession

**Scenario**: User changes project mode while succession is in progress.

**Mitigation**: Mode locked after project staging (Handover 0246a handles this).

---

### Edge Case 2: Missing Metadata Field

**Scenario**: Project has `meta_data = None` instead of `{}`

**Mitigation**:
```python
execution_mode = (project.meta_data or {}).get('execution_mode', 'multi-terminal')
```

---

### Edge Case 3: Invalid Mode Value

**Scenario**: Corrupted metadata has `execution_mode = "invalid"`

**Mitigation**:
```python
if execution_mode not in ['claude-code', 'multi-terminal']:
    logger.warning(f"Invalid mode '{execution_mode}', defaulting to 'multi-terminal'")
    execution_mode = 'multi-terminal'
```

---

## Related Work

**Depends On**:
- Handover 0246a (Frontend Toggle) - mode must be set before succession

**Enables**:
- Consistent user experience across orchestrator handovers
- No manual mode reconfiguration needed

**Related Handovers**:
- Handover 0080 (Orchestrator Succession) - base succession mechanism
- Handover 0246d (Testing & Integration) - comprehensive validation

---

## Rollback Plan

### Rollback Triggers

Rollback if:
- Succession fails after mode preservation added
- Mode causes orchestrator spawning errors
- Performance degrades

### Rollback Steps

1. **Immediate**: Remove mode parameter from `spawn_orchestrator()`
2. **Handover**: Remove mode from `_create_handover_summary()`
3. **Succession**: Remove mode fetching from `trigger_succession()`

**Rollback Command**:
```bash
git revert HEAD
pytest tests/integration/test_succession_mode_preservation.py -v
```

---

## Deliverables

**Before marking complete, verify**:

1. ✅ Tests written FIRST (TDD Red → Green → Refactor)
2. ✅ All tests passing
3. ✅ Coverage >80% for new code
4. ✅ Service layer compliance
5. ✅ Multi-tenant isolation verified
6. ✅ No zombie code
7. ✅ Structured logging added
8. ✅ Mode consistency validated
9. ✅ Manual succession testing complete
10. ✅ Git commit with descriptive message

**Git Commit Template**:
```bash
git add .
git commit -m "feat: Preserve execution mode through succession (Handover 0246c)

- Add mode fetching in trigger_succession()
- Include mode in handover summary
- Pass mode to successor orchestrator
- Add validation and logging
- Add comprehensive integration tests

Tests: 5 passed, 0 failed
Coverage: 91%


```

---

## Conclusion

This handover ensures execution mode consistency across orchestrator successions. By including mode in the handover context, successors inherit their predecessor's execution mode, maintaining a seamless user experience throughout the project lifecycle.

**Key Insight**: Succession context is the right place to preserve mode—it's already designed for state transfer between orchestrator instances.

**Implementation Complexity**: Low-Medium (6-8 hours). Most time spent on comprehensive testing, not implementation.

---

**Document Version**: 1.0
**Author**: Documentation Manager Agent
**Date**: 2025-11-24
**Builds Upon**: Handover 0246a
**Estimated Timeline**: 6-8 hours
**Status**: READY FOR IMPLEMENTATION
