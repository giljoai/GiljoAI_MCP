# Implementation Guide - Unified Agent State Architecture

## Overview

Step-by-step implementation guide for ADR-0108.

## File Locations

All files relative to `F:\GiljoAI_MCP\`

### New Files
- `src/giljo_mcp/types/job_status.py` - JobStatus enum
- `src/giljo_mcp/state_manager.py` - StateTransitionManager
- `src/giljo_mcp/message_interceptor.py` - MessageInterceptor

### Modified Files
- `src/giljo_mcp/models.py` - Add version, cancelled_at fields
- `src/giljo_mcp/monitoring/agent_health_monitor.py` - Add state triggers
- `api/schemas/agent_jobs.py` - New request/response models
- `api/endpoints/agent_jobs.py` - New endpoints

## Phase 1: Database Migration (Week 1)

### Create Migration Script

File: `alembic/versions/0108_unified_agent_state.py`

```python
def upgrade():
    # Add version field
    op.add_column('mcp_agent_jobs',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1')
    )
    
    # Add cancellation fields
    op.add_column('mcp_agent_jobs',
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('mcp_agent_jobs',
        sa.Column('cancellation_reason', sa.Text(), nullable=True)
    )
    
    # Update status constraint
    op.drop_constraint('ck_mcp_agent_job_status', 'mcp_agent_jobs')
    op.create_check_constraint(
        'ck_mcp_agent_job_status',
        'mcp_agent_jobs',
        "status IN ('waiting', 'preparing', 'working', 'review', 'blocked', "
        "'complete', 'failed', 'cancelled', 'decommissioned')"
    )
    
    # Create indexes
    op.create_index(
        'idx_mcp_agent_jobs_version',
        'mcp_agent_jobs',
        ['job_id', 'version']
    )

def downgrade():
    op.drop_index('idx_mcp_agent_jobs_version')
    op.drop_constraint('ck_mcp_agent_job_status', 'mcp_agent_jobs')
    # Restore old constraint...
    op.drop_column('mcp_agent_jobs', 'cancellation_reason')
    op.drop_column('mcp_agent_jobs', 'cancelled_at')
    op.drop_column('mcp_agent_jobs', 'version')
```

### Test Migration

```bash
# Upgrade
alembic upgrade head

# Verify
psql -U postgres -d giljo_mcp -c "\d mcp_agent_jobs"

# Test rollback
alembic downgrade -1
alembic upgrade head
```

## Phase 2: Core Components (Week 2)

### Create JobStatus Enum

File: `src/giljo_mcp/types/job_status.py`

See python-type-definitions.md for complete code.

### Create StateTransitionManager

File: `src/giljo_mcp/state_manager.py`

```python
class StateTransitionManager:
    async def transition_state(
        self,
        job_id: str,
        new_status: JobStatus,
        reason: str,
        tenant_key: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> StateTransitionResult:
        async with self.db_manager.get_session_async() as session:
            # Load job with FOR UPDATE lock
            stmt = select(AgentJob).where(
                AgentJob.job_id == job_id,
                AgentJob.tenant_key == tenant_key
            ).with_for_update()
            
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            
            if not job:
                raise JobNotFoundError(job_id)
            
            # Validate transition
            old_status = JobStatus(job.status)
            if not old_status.can_transition_to(new_status):
                raise InvalidTransitionError(old_status, new_status)
            
            # Update with version increment
            job.status = new_status.value
            job.version = job.version + 1
            
            # Add to state history
            state_entry = {
                "from_status": old_status.value,
                "to_status": new_status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "triggered_by": user_id or "system"
            }
            
            job_meta = job.job_metadata or {}
            job_meta.setdefault("state_history", []).append(state_entry)
            job.job_metadata = job_meta
            flag_modified(job, "job_metadata")
            
            await session.commit()
            await self._broadcast_status_change(job, old_status, new_status, reason)
            
            return StateTransitionResult(success=True)
```

### Create MessageInterceptor

File: `src/giljo_mcp/message_interceptor.py`

```python
class MessageInterceptor:
    TERMINAL_RESPONSES = {
        JobStatus.CANCELLED: "Agent cancelled by user. Re-enable to resume.",
        JobStatus.DECOMMISSIONED: "Agent retired from project.",
        JobStatus.COMPLETE: "Agent completed mission. Create new job.",
        JobStatus.FAILED: "Agent failed. Review logs or create new job."
    }
    
    async def send_message(
        self,
        job_id: str,
        message: str,
        from_agent: str,
        tenant_key: str
    ) -> MessageResult:
        job = await self._load_job(job_id, tenant_key)
        job_status = JobStatus(job.status)
        
        if job_status.is_terminal:
            # Block message
            return MessageResult(
                success=False,
                blocked=True,
                reason=self.TERMINAL_RESPONSES[job_status]
            )
        
        # Deliver normally
        return await self._deliver_message(job, message, from_agent)
```

## Phase 3: API Endpoints (Week 2)

### Update API Endpoints

File: `api/endpoints/agent_jobs.py`

```python
@router.post("/{job_id}/transition", response_model=StateTransitionResponse)
async def transition_job_status(
    job_id: str,
    request: StateTransitionRequest,
    current_user: User = Depends(get_current_active_user)
):
    try:
        result = await state_manager.transition_state(
            job_id=job_id,
            new_status=request.new_status,
            reason=request.reason,
            tenant_key=current_user.tenant_key,
            user_id=str(current_user.id)
        )
        return result
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{job_id}/decommission")
async def decommission_agent(
    job_id: str,
    request: DecommissionRequest,
    current_user: User = Depends(get_current_active_user)
):
    result = await state_manager.transition_state(
        job_id=job_id,
        new_status=JobStatus.DECOMMISSIONED,
        reason=request.reason,
        tenant_key=current_user.tenant_key
    )
    return DecommissionResponse(
        job_id=job_id,
        status=JobStatus.DECOMMISSIONED,
        message="Agent decommissioned",
        decommissioned_at=datetime.now(timezone.utc)
    )
```

## Testing Checklist

- [ ] Unit tests: All valid transitions
- [ ] Unit tests: Invalid transitions raise error
- [ ] Unit tests: Optimistic locking conflicts
- [ ] Unit tests: Message interception
- [ ] Integration tests: API endpoints
- [ ] Integration tests: WebSocket broadcasts
- [ ] Integration tests: Health monitor triggers
- [ ] Load tests: Concurrent state changes

## Deployment

1. Database migration (Phase 1)
2. Deploy backend code (Phase 2)
3. Deploy API changes (Phase 3)
4. Monitor for 24 hours
5. Proceed to Agent model migration (future phase)
