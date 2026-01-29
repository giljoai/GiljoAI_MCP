# Handover 0484: API Test Fixture Remediation

## Mission
Fix remaining 90 API test failures caused by SQLAlchemy session issues and outdated test fixtures that don't follow the AgentJob + AgentExecution dual-model architecture.

## Context
Branch: `0480-exception-handling-remediation`
Previous handover: 0483 (service layer bug fixes)

### What Was Already Fixed (Handover 0483)
1. **Production code bugs**:
   - `api/endpoints/messages.py` - nested data structure handling
   - `api/endpoints/templates/crud.py` - HTTPException swallowing
   - `api/endpoints/templates/history.py` - tenant isolation
   - `api/endpoints/users.py` - per-user tenancy
   - `api/exception_handlers.py` - JSON serialization

2. **Test files already fixed**:
   - `test_messages_api.py` - 29 passed, 2 skipped
   - `test_users_api.py` - 38 passed
   - `test_templates_api.py` - 26 passed, 21 skipped
   - `test_unified_message_send.py` - mostly passing

### Current Test Status
```
423 passed, 90 failed, 50 skipped, 75 errors
```

## Root Causes of Remaining Failures

### 1. SQLAlchemy Session Issues (Most Common)
**Error Pattern:**
```
sqlalchemy.exc.InvalidRequestError: Instance '<AgentExecution at 0x...>' is not persistent within this Session
```

**Cause:** Fixtures create database objects in one session, but tests try to `refresh()` or access them in a different session.

**Affected Tests:**
- `test_simple_handover.py` - All 7 tests fail with this error
- Several other tests that try to verify database state after API calls

**Fix Pattern:**
Instead of:
```python
await db_session.refresh(orchestrator_execution)
assert orchestrator_execution.context_used == 0
```

Do:
```python
async with db_manager.get_session_async() as session:
    result = await session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == orchestrator_execution.agent_id)
    )
    refreshed = result.scalar_one()
    assert refreshed.context_used == 0
```

### 2. Dual-Model Architecture Not Followed
**Error Pattern:**
```
TypeError: 'project_id' is an invalid keyword argument for AgentExecution
TypeError: 'mission' is an invalid keyword argument for AgentExecution
```

**Cause:** Old tests create `AgentExecution` with fields that belong to `AgentJob`.

**Correct Model Structure:**
- **AgentJob** (work order): `job_id`, `tenant_key`, `project_id`, `job_type`, `mission`, `status`, `job_metadata`
- **AgentExecution** (executor): `agent_id`, `job_id` (FK), `tenant_key`, `agent_display_name`, `status`

**Fix Pattern:**
```python
# WRONG - Old pattern
execution = AgentExecution(
    job_id=str(uuid4()),
    project_id=project.id,  # INVALID
    mission="Test mission",  # INVALID
    agent_display_name="worker",
    status="working",
)

# CORRECT - Dual-model pattern
job_id = str(uuid4())
agent_job = AgentJob(
    job_id=job_id,
    tenant_key=user._test_tenant_key,
    project_id=project.id,
    job_type="worker",
    mission="Test mission",
    status="active",
    created_at=datetime.now(timezone.utc),
    job_metadata={},
)
session.add(agent_job)
await session.flush()

execution = AgentExecution(
    job_id=job_id,
    tenant_key=user._test_tenant_key,
    agent_display_name="worker",
    status="working",
)
session.add(execution)
await session.commit()
```

### 3. Deprecated JSONB Column Usage
**Error Pattern:** Tests create messages in `AgentExecution.messages` JSONB but endpoint reads from `Message` table.

**Fix Pattern:**
```python
# WRONG - Deprecated
job.messages = [{"id": "...", "content": "..."}]

# CORRECT - Use Message table
msg = Message(
    id=str(uuid4()),
    project_id=project.id,
    tenant_key=user._test_tenant_key,
    to_agents=["worker"],
    content="Test message",
    message_type="direct",
    priority="normal",
    status="pending",
    meta_data={"_from_agent": "orchestrator"},
)
session.add(msg)
```

### 4. Missing Endpoints
Some tests expect endpoints that don't exist:
- `/messages/{id}/acknowledge` - doesn't exist (use agent_jobs endpoint)

**Fix:** Skip these tests with explanation, or rewrite to use existing endpoints.

## Files Requiring Fixes

### High Priority (Multiple Failures)
1. **`tests/api/test_simple_handover.py`** - 7 failures
   - All session refresh issues
   - Need to query fresh from database instead of refreshing fixture objects

2. **`tests/api/test_project_execution_mode_api.py`** - 8 failures
   - Likely fixture issues with project/execution setup

3. **`tests/api/test_products_api.py`** - 6 failures (vision document tests)
   - May need proper product/tenant setup

4. **`tests/api/test_projects_api.py`** - 6 failures
   - Project lifecycle tests may need fixture updates

### Medium Priority
5. **`tests/api/test_prompts_execution_mode.py`** - 5 failures
6. **`tests/api/test_mcp_security.py`** - 2 failures
7. **`tests/api/test_slash_commands_api.py`** - 1 failure
8. **`tests/api/test_priority_system.py`** - 1 failure

### Low Priority (Skip Candidates)
- Tests for features that may not exist or are deprecated
- Cross-tenant tests that may need architectural review

## Execution Strategy

1. **Start with test_simple_handover.py** - Fix session issues as a pattern
2. **Apply dual-model fix** to remaining fixtures
3. **Update deprecated JSONB usage** to Message table
4. **Skip tests for missing endpoints** with clear documentation
5. **Run full test suite** after each file fix to track progress

## Success Criteria
- Reduce failures from 90 to < 20
- No errors (currently 75)
- Document any skipped tests with clear reasons

## Commands

```bash
# Run specific test file
python -m pytest tests/api/test_simple_handover.py -v --tb=short --no-cov

# Run all API tests
python -m pytest tests/api/ -v --tb=line --no-cov

# Quick summary
python -m pytest tests/api/ -q --tb=no --no-cov
```

## Reference: Model Imports

```python
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models import Message, Project, Product, User
from datetime import datetime, timezone
from uuid import uuid4
```
