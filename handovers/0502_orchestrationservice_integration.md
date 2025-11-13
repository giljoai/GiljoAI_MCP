---
**Document Type:** Handover
**Handover ID:** 0502
**Title:** OrchestrationService Integration - Context Tracking & AgentJobManager
**Version:** 1.0
**Created:** 2025-11-12
**Status:** Ready for Execution
**Duration:** 4-5 hours
**Scope:** Integrate AgentJobManager, implement context_used tracking, fix succession trigger
**Priority:** 🔴 P0 CRITICAL
**Tool:** 🖥️ CLI
**Parallel Execution:** ❌ No (Sequential after 0501)
**Parent Project:** Projectplan_500.md
---

# Handover 0502: OrchestrationService Integration - Context Tracking & AgentJobManager

## 🎯 Mission Statement
Integrate AgentJobManager into orchestration workflow, implement context_used field tracking for succession monitoring, and prepare foundation for trigger_succession endpoint. This completes Phase 0 service layer work.

## 📋 Prerequisites
**Must be complete before starting:**
- ✅ Handover 0500 complete (ProductService)
- ✅ Handover 0501 complete (ProjectService)
- PostgreSQL with context_used, context_budget fields in mcp_agent_jobs table
- Python environment with all dependencies

## ⚠️ Problem Statement

### Issue 1: AgentJobManager Not Integrated
**Evidence**: Projectplan_500.md line 53
- AgentJobManager exists (src/giljo_mcp/agent_job_manager.py) but not used in orchestration
- Orchestrator creates jobs manually via ORM instead of using manager
- Missing lifecycle management (acknowledge, progress reporting, completion)
- **Impact**: Job state management inconsistent, no standardized workflow

**Current State**:
```python
# ProjectOrchestrator currently does this:
job = AgentJob(
    agent_type="orchestrator",
    mission=mission,
    project_id=project_id,
    tenant_key=tenant_key
)
session.add(job)
await session.commit()
```

**Should be**:
```python
job_manager = AgentJobManager(session, tenant_key)
job = await job_manager.create_job(
    agent_type="orchestrator",
    agent_name="Orchestrator",
    mission=mission,
    project_id=project_id
)
```

### Issue 2: Context Usage Tracking NOT IMPLEMENTED
**Evidence**: Projectplan_500.md line 54
- Database fields exist: `context_used`, `context_budget` (added in Handover 0080)
- Fields never populated - always NULL
- Succession monitoring broken (can't detect 90% threshold)
- **Impact**: Orchestrator succession feature non-functional

**Database State**:
```sql
SELECT id, agent_type, context_used, context_budget, succession_reason
FROM mcp_agent_jobs
WHERE agent_type = 'orchestrator';

-- Result: context_used and context_budget are NULL for all rows
```

### Issue 3: trigger_succession Endpoint Missing
**Evidence**: Projectplan_500.md line 51
- Frontend calls `POST /api/v1/agent-jobs/{job_id}/trigger-succession`
- Endpoint returns 404
- **Impact**: Manual succession trigger broken (Handover 0080a feature)

## ✅ Solution Approach

### 1. Integrate AgentJobManager
Replace direct ORM usage with AgentJobManager pattern throughout orchestration code:
- Use `create_job()` for spawning orchestrators
- Use `acknowledge_job()` when orchestrator starts work
- Use `report_progress()` for status updates
- Use `complete_job()` when mission complete
- Use `report_error()` for failures

### 2. Implement Context Tracking
Add token counting and context monitoring:
- Use tiktoken to estimate context_used (sum of mission + all messages)
- Set context_budget based on model (200K for Sonnet 4.5)
- Update context_used on each message/progress report
- Calculate usage percentage (context_used / context_budget)
- Auto-trigger succession at 90% threshold

### 3. Create OrchestrationService
New service layer for orchestration-specific logic:
- Wraps AgentJobManager with orchestration context
- Handles context tracking
- Manages succession logic
- Provides clean interface for endpoints

## 📝 Implementation Tasks

### Task 1: Create OrchestrationService (2 hours)
**File**: `src/giljo_mcp/services/orchestration_service.py` (NEW)

**Class Structure**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
import tiktoken

from src.giljo_mcp.agent_job_manager import AgentJobManager
from src.giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from src.giljo_mcp.models import AgentJob

class OrchestrationService:
    """Service layer for orchestration and succession management."""

    def __init__(self, session: AsyncSession, tenant_key: str):
        self.session = session
        self.tenant_key = tenant_key
        self.job_manager = AgentJobManager(session, tenant_key)
        self.succession_manager = OrchestratorSuccessionManager(session, tenant_key)
        self.encoder = tiktoken.get_encoding("cl100k_base")

    async def create_orchestrator_job(
        self,
        project_id: str,
        mission: str,
        context_budget: int = 200000
    ) -> AgentJob:
        """Create orchestrator job with context tracking."""
        job = await self.job_manager.create_job(
            agent_type="orchestrator",
            agent_name="Orchestrator",
            mission=mission,
            project_id=project_id,
            metadata={
                "context_budget": context_budget,
                "context_used": len(self.encoder.encode(mission))
            }
        )

        # Set context fields
        job.context_budget = context_budget
        job.context_used = len(self.encoder.encode(mission))
        await self.session.commit()
        await self.session.refresh(job)

        return job

    async def update_context_usage(
        self,
        job_id: str,
        additional_tokens: int
    ) -> AgentJob:
        """Update context_used and check succession threshold."""
        job = await self.job_manager.get_job(job_id)

        job.context_used = (job.context_used or 0) + additional_tokens
        await self.session.commit()

        # Check if succession needed (90% threshold)
        if job.context_budget and job.context_used:
            usage_pct = (job.context_used / job.context_budget) * 100
            if usage_pct >= 90:
                await self._trigger_auto_succession(job)

        await self.session.refresh(job)
        return job

    async def estimate_message_tokens(self, message: str) -> int:
        """Estimate token count for message."""
        return len(self.encoder.encode(message))

    async def _trigger_auto_succession(self, job: AgentJob):
        """Auto-trigger succession when context threshold reached."""
        if not job.handover_to:  # Don't trigger if already has successor
            successor = await self.succession_manager.create_successor(
                current_job_id=job.id,
                reason="context_limit"
            )
            job.handover_to = successor.id
            job.succession_reason = "context_limit"
            await self.session.commit()
```

**Implementation Steps**:
- [ ] Create file with imports
- [ ] Define OrchestrationService class
- [ ] Implement `create_orchestrator_job()`
- [ ] Implement `update_context_usage()`
- [ ] Implement `estimate_message_tokens()`
- [ ] Implement `_trigger_auto_succession()`
- [ ] Add comprehensive docstrings

### Task 2: Add Database Migration for Context Fields (30 min)
**File**: Check if migration already exists, otherwise create

**Verification Query**:
```sql
-- Check if columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'mcp_agent_jobs'
AND column_name IN ('context_used', 'context_budget', 'succession_reason', 'handover_to');
```

**If columns missing, create migration**:
```python
# alembic/versions/XXXXX_add_context_tracking.py
def upgrade():
    op.add_column('mcp_agent_jobs',
        sa.Column('context_used', sa.Integer(), nullable=True)
    )
    op.add_column('mcp_agent_jobs',
        sa.Column('context_budget', sa.Integer(), nullable=True)
    )
    op.add_column('mcp_agent_jobs',
        sa.Column('succession_reason', sa.String(), nullable=True)
    )
    op.add_column('mcp_agent_jobs',
        sa.Column('handover_to', sa.String(), nullable=True)
    )
```

**Note**: These fields likely already exist from Handover 0080. Verify first!

### Task 3: Update ProjectOrchestrator to Use OrchestrationService (1.5 hours)
**File**: `src/giljo_mcp/project_orchestrator.py`

**Current Pattern** (find and replace):
```python
# BEFORE - Direct AgentJob creation
job = AgentJob(...)
session.add(job)
await session.commit()

# AFTER - Use OrchestrationService
orchestration_service = OrchestrationService(session, tenant_key)
job = await orchestration_service.create_orchestrator_job(
    project_id=project_id,
    mission=mission,
    context_budget=200000
)
```

**Implementation Steps**:
- [ ] Import OrchestrationService
- [ ] Replace direct AgentJob creation with `create_orchestrator_job()`
- [ ] Add context tracking on message sends
- [ ] Update progress reporting to include token counts

**Example - Message Handling**:
```python
async def send_message_to_agent(self, job_id: str, message: str):
    """Send message and track context usage."""
    orchestration_service = OrchestrationService(self.session, self.tenant_key)

    # Estimate tokens
    tokens = await orchestration_service.estimate_message_tokens(message)

    # Update context
    await orchestration_service.update_context_usage(job_id, tokens)

    # Send message via AgentCommunicationQueue
    # ... existing code ...
```

### Task 4: Add Context Tracking to Thin Client Prompt Generator (45 min)
**File**: `src/giljo_mcp/thin_client_prompt_generator.py`

**Enhancement**: Include context usage in generated prompts

**Add Method**:
```python
async def get_context_status(self, job_id: str) -> Dict[str, Any]:
    """Get current context usage for job."""
    job = await self.session.get(AgentJob, job_id)
    if not job:
        return {}

    usage_pct = 0
    if job.context_budget and job.context_used:
        usage_pct = (job.context_used / job.context_budget) * 100

    return {
        "context_used": job.context_used or 0,
        "context_budget": job.context_budget or 200000,
        "usage_percentage": round(usage_pct, 2),
        "succession_recommended": usage_pct >= 90
    }
```

### Task 5: Create trigger_succession Service Method (1 hour)
**File**: `src/giljo_mcp/services/orchestration_service.py` (add to existing class)

**Method**:
```python
async def trigger_succession(
    self,
    job_id: str,
    reason: str = "manual"
) -> AgentJob:
    """
    Manually trigger orchestrator succession.

    Args:
        job_id: Current orchestrator job ID
        reason: Succession reason (manual, context_limit, phase_transition)

    Returns:
        Successor orchestrator job

    Raises:
        JobNotFoundError: Job doesn't exist
        InvalidSuccessionError: Cannot succeed from current state
    """
    # Validate job exists and is orchestrator
    current_job = await self.job_manager.get_job(job_id)
    if current_job.agent_type != "orchestrator":
        raise InvalidSuccessionError("Can only trigger succession for orchestrators")

    # Check if already has successor
    if current_job.handover_to:
        raise InvalidSuccessionError("Succession already triggered")

    # Create successor
    successor = await self.succession_manager.create_successor(
        current_job_id=job_id,
        reason=reason
    )

    # Update current job
    current_job.handover_to = successor.id
    current_job.succession_reason = reason
    await self.session.commit()

    return successor
```

### Task 6: Unit Tests (1 hour)
**File**: `tests/services/test_orchestration_service.py` (NEW)

**Test Cases**:
```python
import pytest
from src.giljo_mcp.services.orchestration_service import OrchestrationService

@pytest.mark.asyncio
async def test_create_orchestrator_job_sets_context_budget(db_session, tenant_key):
    """Test orchestrator job created with context tracking."""
    service = OrchestrationService(db_session, tenant_key)

    job = await service.create_orchestrator_job(
        project_id="test-project",
        mission="Test mission",
        context_budget=200000
    )

    assert job.context_budget == 200000
    assert job.context_used > 0  # Mission tokens counted
    assert job.agent_type == "orchestrator"

@pytest.mark.asyncio
async def test_update_context_usage_increments(db_session, tenant_key, orchestrator_job):
    """Test context_used increments correctly."""
    service = OrchestrationService(db_session, tenant_key)

    initial_usage = orchestrator_job.context_used
    await service.update_context_usage(orchestrator_job.id, 1000)

    updated_job = await service.job_manager.get_job(orchestrator_job.id)
    assert updated_job.context_used == initial_usage + 1000

@pytest.mark.asyncio
async def test_auto_succession_at_90_percent(db_session, tenant_key):
    """Test automatic succession triggered at 90% context usage."""
    service = OrchestrationService(db_session, tenant_key)

    # Create job with low budget
    job = await service.create_orchestrator_job(
        project_id="test-project",
        mission="Test",
        context_budget=1000
    )

    # Push to 90%
    await service.update_context_usage(job.id, 900)

    # Check successor created
    updated_job = await service.job_manager.get_job(job.id)
    assert updated_job.handover_to is not None
    assert updated_job.succession_reason == "context_limit"

@pytest.mark.asyncio
async def test_trigger_succession_manual(db_session, tenant_key, orchestrator_job):
    """Test manual succession trigger."""
    service = OrchestrationService(db_session, tenant_key)

    successor = await service.trigger_succession(
        job_id=orchestrator_job.id,
        reason="manual"
    )

    assert successor is not None
    assert successor.spawned_by == orchestrator_job.id
    assert orchestrator_job.handover_to == successor.id
    assert orchestrator_job.succession_reason == "manual"
```

## 🧪 Testing Strategy

### Database Validation
```sql
-- Verify context fields populated
SELECT
    id,
    agent_type,
    context_used,
    context_budget,
    ROUND((context_used::float / context_budget::float) * 100, 2) as usage_pct,
    succession_reason,
    handover_to
FROM mcp_agent_jobs
WHERE agent_type = 'orchestrator'
ORDER BY created_at DESC
LIMIT 5;

-- Should return rows with non-NULL context_used/context_budget
```

### Integration Testing
- [ ] Create orchestrator job via service
- [ ] Send 10 messages, verify context_used increments
- [ ] Push usage to 91%, verify auto-succession triggered
- [ ] Manually trigger succession, verify successor created

### Manual Validation
- [ ] Start local server: `python startup.py --dev`
- [ ] Create project, launch orchestrator
- [ ] Check database: context_used should be non-NULL
- [ ] Send messages via dashboard
- [ ] Verify context_used increases with each message

## ✅ Success Criteria
- [ ] OrchestrationService class created and tested
- [ ] AgentJobManager integrated throughout orchestration code
- [ ] context_used field populated on job creation
- [ ] context_used increments on message sends
- [ ] Auto-succession triggers at 90% threshold
- [ ] trigger_succession() method implemented
- [ ] All unit tests pass (>80% coverage)
- [ ] Database shows non-NULL context fields
- [ ] Manual succession works (foundation for endpoint in 0505)

## 🔄 Rollback Plan
1. Revert OrchestrationService: `git rm src/giljo_mcp/services/orchestration_service.py`
2. Revert ProjectOrchestrator changes: `git checkout HEAD~1 -- src/giljo_mcp/project_orchestrator.py`
3. Revert ThinClientPromptGenerator: `git checkout HEAD~1 -- src/giljo_mcp/thin_client_prompt_generator.py`
4. Database rollback NOT needed (context fields already exist)

## 📚 Related Handovers
**Depends on**:
- 0500 (ProductService) - foundation
- 0501 (ProjectService) - foundation
- Handover 0080 (Orchestrator Succession) - context_used/context_budget fields

**Blocks**:
- 0505 (Orchestrator Succession Endpoint) - needs trigger_succession() method

**Related**:
- Handover 0088 (Thin Client Architecture) - prompt generation
- Handover 0019 (Agent Job Management) - AgentJobManager

## 🛠️ Tool Justification
**Why CLI (Local)**:
- Service layer implementation requires database access
- Context tracking needs live PostgreSQL for testing
- Token estimation with tiktoken requires local environment
- Integration tests need full application stack
- WebSocket event testing requires local server

## 📊 Parallel Execution
**Cannot run in parallel** - This completes Phase 0 (Service Layer).

**Sequential Execution**:
1. 0500 (ProductService) → 2. 0501 (ProjectService) → 3. 0502 (OrchestrationService) ← This handover

**After this completes**: Phase 1 (Endpoints) can run in 4 parallel branches via CCW.

---
**Status:** Ready for Execution
**Estimated Effort:** 4-5 hours
**Archive Location:** `handovers/completed/0502_orchestrationservice_integration-COMPLETE.md`
