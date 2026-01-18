# Handover 0387e: Add Message Counter Columns

**Part 1 of 5** in the JSONB Messages Normalization series (Phase 4 of 0387)
**Date**: 2026-01-17
**Status**: Ready for Implementation
**Complexity**: Medium-High
**Estimated Duration**: 6-8 hours
**Branch**: `0387-jsonb-normalization`

---

## 1. EXECUTIVE SUMMARY

### Mission
Add `messages_sent_count`, `messages_waiting_count`, `messages_read_count` columns to `AgentExecution` model. These counter columns will replace JSONB array derivation for message counts, establishing single source of truth.

### Context
Currently, message counts are derived by iterating over `AgentExecution.messages` JSONB array. This creates:
- Performance overhead (count on every read)
- Dual-write pattern (Message table + JSONB)
- Sync risk between two data sources

Counter columns solve this by maintaining counts atomically at write time.

### Why This Matters
- **Foundation**: All subsequent handovers (0387f-i) depend on these counter columns
- **Performance**: Counter read is O(1) vs JSONB iteration O(n)
- **Atomicity**: Database handles increment/decrement atomically
- **Frontend Ready**: Frontend already checks for these fields as fallback

### Success Criteria
- [ ] 3 counter columns exist on `AgentExecution` model
- [ ] Migration adds columns with default 0
- [ ] Migration backfills counts from Message table
- [ ] Atomic increment/decrement methods exist in repository
- [ ] All TDD tests pass (GREEN)
- [ ] Existing tests still pass
- [ ] Branch `0387-jsonb-normalization` created

---

## 2. TECHNICAL CONTEXT

### Architecture Overview

**Current State (JSONB-based counting)**:
```
Frontend → API → AgentExecution.messages (JSONB array)
                       ↓
              Iterate array, count by status
                       ↓
              Return counts
```

**Target State (Counter columns)**:
```
Frontend → API → AgentExecution.messages_sent_count
                 AgentExecution.messages_waiting_count
                 AgentExecution.messages_read_count
                       ↓
              Direct column read (O(1))
```

### Database Schema Changes

**Add to `mcp_agent_executions` table**:
```sql
ALTER TABLE mcp_agent_executions
ADD COLUMN messages_sent_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE mcp_agent_executions
ADD COLUMN messages_waiting_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE mcp_agent_executions
ADD COLUMN messages_read_count INTEGER NOT NULL DEFAULT 0;
```

### Counter Semantics

| Counter | Incremented When | Decremented When |
|---------|------------------|------------------|
| `messages_sent_count` | Agent sends a message | Never (outbound messages don't change) |
| `messages_waiting_count` | Agent receives a message | Message acknowledged/read |
| `messages_read_count` | Message acknowledged | Never (read count only increases) |

---

## 3. SCOPE

### In Scope
1. **Model Changes**
   - Add 3 counter columns to `AgentExecution` model
   - Add column comments for documentation

2. **Migration Script**
   - Create Alembic migration
   - Backfill counts from Message table
   - Handle existing data correctly

3. **Repository Methods**
   - Add `increment_sent_count(agent_id, tenant_key)`
   - Add `increment_waiting_count(agent_id, tenant_key)`
   - Add `decrement_waiting_increment_read(agent_id, tenant_key)`
   - All operations must be atomic (single UPDATE)

4. **TDD Tests**
   - Write tests FIRST (RED phase)
   - Implement to pass tests (GREEN phase)
   - Refactor if needed

### Out of Scope (Future Handovers)
- Using counters instead of JSONB (0387f)
- Frontend updates (0387g)
- Test cleanup (0387h)
- JSONB deprecation (0387i)

### Dependencies
- PostgreSQL database running
- Alembic configured
- `AgentExecution` model exists

---

## 4. IMPLEMENTATION PLAN

### Phase 0: Safety Net (15 minutes)

**Goal**: Create branch and backup before ANY changes.

**Tasks**:
```bash
# 1. Create feature branch from current branch
git checkout -b 0387-jsonb-normalization

# 2. Push branch
git push -u origin 0387-jsonb-normalization

# 3. Database backup
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/pg_dump.exe -U postgres giljo_mcp > backup_pre_0387_phase4.sql

# 4. Document baseline
pytest tests/ --tb=no -q | grep -E "passed|failed"
# Record count in closeout notes
```

**Validation**:
- [ ] Branch exists: `git branch --show-current` → `0387-jsonb-normalization`
- [ ] Backup exists and non-zero size
- [ ] Baseline test count recorded

---

### Phase 1: RED - Write Failing Tests (45 minutes)

**Goal**: Define expected behavior through tests before implementation.

**Test File**: `tests/unit/test_message_counters.py`

```python
"""
TDD tests for message counter columns (Handover 0387e).

Run with: pytest tests/unit/test_message_counters.py -v
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.repositories.agent_job_repository import AgentJobRepository


class TestMessageCounterColumns:
    """Tests for message counter columns on AgentExecution."""

    @pytest.mark.asyncio
    async def test_counter_columns_exist(self, async_session: AsyncSession):
        """AgentExecution should have messages_sent_count, messages_waiting_count, messages_read_count columns."""
        # Create a test execution
        from tests.fixtures.agent_fixtures import create_test_execution
        execution = await create_test_execution(async_session, tenant_key="test_tenant")

        # Assert columns exist with default values
        assert hasattr(execution, 'messages_sent_count')
        assert hasattr(execution, 'messages_waiting_count')
        assert hasattr(execution, 'messages_read_count')
        assert execution.messages_sent_count == 0
        assert execution.messages_waiting_count == 0
        assert execution.messages_read_count == 0

    @pytest.mark.asyncio
    async def test_increment_sent_count(self, async_session: AsyncSession):
        """increment_sent_count should atomically increase sent counter by 1."""
        from tests.fixtures.agent_fixtures import create_test_execution
        execution = await create_test_execution(async_session, tenant_key="test_tenant")

        repo = AgentJobRepository(None)
        await repo.increment_sent_count(
            session=async_session,
            agent_id=execution.agent_id,
            tenant_key="test_tenant"
        )

        await async_session.refresh(execution)
        assert execution.messages_sent_count == 1

    @pytest.mark.asyncio
    async def test_increment_waiting_count(self, async_session: AsyncSession):
        """increment_waiting_count should atomically increase waiting counter by 1."""
        from tests.fixtures.agent_fixtures import create_test_execution
        execution = await create_test_execution(async_session, tenant_key="test_tenant")

        repo = AgentJobRepository(None)
        await repo.increment_waiting_count(
            session=async_session,
            agent_id=execution.agent_id,
            tenant_key="test_tenant"
        )

        await async_session.refresh(execution)
        assert execution.messages_waiting_count == 1

    @pytest.mark.asyncio
    async def test_decrement_waiting_increment_read(self, async_session: AsyncSession):
        """Acknowledging a message should decrement waiting and increment read atomically."""
        from tests.fixtures.agent_fixtures import create_test_execution
        execution = await create_test_execution(async_session, tenant_key="test_tenant")

        repo = AgentJobRepository(None)

        # First, receive a message (increment waiting)
        await repo.increment_waiting_count(
            session=async_session,
            agent_id=execution.agent_id,
            tenant_key="test_tenant"
        )

        # Then acknowledge it (decrement waiting, increment read)
        await repo.decrement_waiting_increment_read(
            session=async_session,
            agent_id=execution.agent_id,
            tenant_key="test_tenant"
        )

        await async_session.refresh(execution)
        assert execution.messages_waiting_count == 0
        assert execution.messages_read_count == 1

    @pytest.mark.asyncio
    async def test_counters_are_atomic(self, async_session: AsyncSession):
        """Counter operations should be atomic (no race conditions)."""
        from tests.fixtures.agent_fixtures import create_test_execution
        execution = await create_test_execution(async_session, tenant_key="test_tenant")

        repo = AgentJobRepository(None)

        # Increment sent 5 times
        for _ in range(5):
            await repo.increment_sent_count(
                session=async_session,
                agent_id=execution.agent_id,
                tenant_key="test_tenant"
            )

        await async_session.refresh(execution)
        assert execution.messages_sent_count == 5

    @pytest.mark.asyncio
    async def test_counters_respect_tenant_isolation(self, async_session: AsyncSession):
        """Counter updates should only affect executions in the same tenant."""
        from tests.fixtures.agent_fixtures import create_test_execution

        # Create executions in different tenants
        exec_a = await create_test_execution(async_session, tenant_key="tenant_a")
        exec_b = await create_test_execution(async_session, tenant_key="tenant_b")

        repo = AgentJobRepository(None)

        # Increment only tenant_a
        await repo.increment_sent_count(
            session=async_session,
            agent_id=exec_a.agent_id,
            tenant_key="tenant_a"
        )

        await async_session.refresh(exec_a)
        await async_session.refresh(exec_b)

        assert exec_a.messages_sent_count == 1
        assert exec_b.messages_sent_count == 0  # Unchanged

    @pytest.mark.asyncio
    async def test_waiting_count_cannot_go_negative(self, async_session: AsyncSession):
        """decrement_waiting_increment_read should not make waiting_count negative."""
        from tests.fixtures.agent_fixtures import create_test_execution
        execution = await create_test_execution(async_session, tenant_key="test_tenant")

        repo = AgentJobRepository(None)

        # Try to decrement when count is 0
        await repo.decrement_waiting_increment_read(
            session=async_session,
            agent_id=execution.agent_id,
            tenant_key="test_tenant"
        )

        await async_session.refresh(execution)
        # Should either stay at 0 or raise an error, not go negative
        assert execution.messages_waiting_count >= 0
```

**Validation**:
- [ ] Run tests: `pytest tests/unit/test_message_counters.py -v`
- [ ] All 7 tests should FAIL (columns/methods don't exist yet)
- [ ] Failure messages are clear and actionable

---

### Phase 2: GREEN - Add Counter Columns (1 hour)

**Goal**: Add columns to model to make column-existence tests pass.

**File**: `src/giljo_mcp/models/agent_identity.py`

**Add after line 286 (after existing `messages` column)**:

```python
    # Message counter columns (Handover 0387e - replaces JSONB array counting)
    messages_sent_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Count of outbound messages sent by this agent",
    )
    messages_waiting_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Count of inbound messages waiting to be read",
    )
    messages_read_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Count of inbound messages that have been acknowledged/read",
    )
```

**Validation**:
- [ ] No syntax errors
- [ ] `test_counter_columns_exist` passes

---

### Phase 3: GREEN - Create Migration (1 hour)

**Goal**: Create Alembic migration with backfill logic.

**File**: `alembic/versions/xxxx_add_message_counters_0387e.py`

```python
"""Add message counter columns to agent_executions (Handover 0387e)

Revision ID: 0387e_counters
Revises: [previous_revision]
Create Date: 2026-01-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '0387e_counters'
down_revision = None  # UPDATE THIS to actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Add counter columns with defaults
    op.add_column(
        'mcp_agent_executions',
        sa.Column('messages_sent_count', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'mcp_agent_executions',
        sa.Column('messages_waiting_count', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'mcp_agent_executions',
        sa.Column('messages_read_count', sa.Integer(), nullable=False, server_default='0')
    )

    # Backfill from Message table (if data exists)
    # This uses raw SQL for performance on large datasets
    op.execute("""
        UPDATE mcp_agent_executions ae
        SET messages_sent_count = COALESCE((
            SELECT COUNT(*)
            FROM messages m
            WHERE m.from_agent = ae.agent_id::text
        ), 0)
    """)

    op.execute("""
        UPDATE mcp_agent_executions ae
        SET messages_waiting_count = COALESCE((
            SELECT COUNT(*)
            FROM messages m
            WHERE m.to_agents @> to_jsonb(ae.agent_id::text)
            AND m.status = 'pending'
        ), 0)
    """)

    op.execute("""
        UPDATE mcp_agent_executions ae
        SET messages_read_count = COALESCE((
            SELECT COUNT(*)
            FROM messages m
            WHERE m.to_agents @> to_jsonb(ae.agent_id::text)
            AND m.status IN ('read', 'acknowledged')
        ), 0)
    """)


def downgrade():
    op.drop_column('mcp_agent_executions', 'messages_read_count')
    op.drop_column('mcp_agent_executions', 'messages_waiting_count')
    op.drop_column('mcp_agent_executions', 'messages_sent_count')
```

**Run Migration**:
```bash
alembic upgrade head
```

**Validation**:
- [ ] Migration runs without errors
- [ ] Columns exist in database: `psql -c "\d mcp_agent_executions"`
- [ ] Existing data backfilled correctly

---

### Phase 4: GREEN - Add Repository Methods (1.5 hours)

**Goal**: Implement atomic counter operations.

**File**: `src/giljo_mcp/repositories/agent_job_repository.py`

**Add methods to `AgentJobRepository` class**:

```python
async def increment_sent_count(
    self,
    session: AsyncSession,
    agent_id: str,
    tenant_key: str,
) -> None:
    """
    Atomically increment messages_sent_count by 1.

    Called when agent sends a message (outbound).

    Args:
        session: Database session
        agent_id: Agent execution ID
        tenant_key: Tenant isolation key
    """
    stmt = (
        update(AgentExecution)
        .where(
            AgentExecution.agent_id == agent_id,
            AgentExecution.tenant_key == tenant_key,
        )
        .values(messages_sent_count=AgentExecution.messages_sent_count + 1)
    )
    await session.execute(stmt)
    await session.commit()

async def increment_waiting_count(
    self,
    session: AsyncSession,
    agent_id: str,
    tenant_key: str,
) -> None:
    """
    Atomically increment messages_waiting_count by 1.

    Called when agent receives a message (inbound, pending).

    Args:
        session: Database session
        agent_id: Agent execution ID
        tenant_key: Tenant isolation key
    """
    stmt = (
        update(AgentExecution)
        .where(
            AgentExecution.agent_id == agent_id,
            AgentExecution.tenant_key == tenant_key,
        )
        .values(messages_waiting_count=AgentExecution.messages_waiting_count + 1)
    )
    await session.execute(stmt)
    await session.commit()

async def decrement_waiting_increment_read(
    self,
    session: AsyncSession,
    agent_id: str,
    tenant_key: str,
) -> None:
    """
    Atomically decrement waiting and increment read counts.

    Called when agent acknowledges/reads a message.
    Uses GREATEST(0, count-1) to prevent negative values.

    Args:
        session: Database session
        agent_id: Agent execution ID
        tenant_key: Tenant isolation key
    """
    stmt = (
        update(AgentExecution)
        .where(
            AgentExecution.agent_id == agent_id,
            AgentExecution.tenant_key == tenant_key,
        )
        .values(
            messages_waiting_count=func.greatest(
                0, AgentExecution.messages_waiting_count - 1
            ),
            messages_read_count=AgentExecution.messages_read_count + 1,
        )
    )
    await session.execute(stmt)
    await session.commit()
```

**Add imports at top of file**:
```python
from sqlalchemy import update, func
```

**Validation**:
- [ ] Run tests: `pytest tests/unit/test_message_counters.py -v`
- [ ] All 7 tests should PASS (GREEN)

---

### Phase 5: Regression Testing (30 minutes)

**Goal**: Ensure no existing functionality broken.

**Tasks**:
```bash
# Run full test suite
pytest tests/ -v --tb=short

# Check for failures
pytest tests/ --tb=no -q | grep -E "passed|failed"

# Compare to baseline
# Before: X passed, Y failed
# After: Should be same or better
```

**Validation**:
- [ ] No new test failures introduced
- [ ] Coverage maintained: `pytest tests/ --cov=src/giljo_mcp --cov-report=term`

---

## 5. TESTING REQUIREMENTS

### Unit Tests (Required)
**File**: `tests/unit/test_message_counters.py`

**Coverage Target**: >90% for new counter code

**Test Cases**:
1. `test_counter_columns_exist` - Columns exist with defaults
2. `test_increment_sent_count` - Atomic increment
3. `test_increment_waiting_count` - Atomic increment
4. `test_decrement_waiting_increment_read` - Atomic dual update
5. `test_counters_are_atomic` - Multiple increments work
6. `test_counters_respect_tenant_isolation` - Security
7. `test_waiting_count_cannot_go_negative` - Edge case

### Integration Tests (Optional)
If time permits, add:
- Test migration on populated database
- Test backfill accuracy

---

## 6. ROLLBACK PLAN

### Pre-Work Safety Net
- [ ] Branch: `0387-jsonb-normalization`
- [ ] Backup: `backup_pre_0387_phase4.sql`

### Rollback Triggers
**Rollback if**:
- Migration fails and cannot be fixed
- More than 10 existing tests break
- Performance regression detected

### Rollback Steps

**Option 1: Migration Rollback**:
```bash
# Downgrade migration
alembic downgrade -1

# Revert code changes
git checkout master -- src/giljo_mcp/models/agent_identity.py
git checkout master -- src/giljo_mcp/repositories/agent_job_repository.py
```

**Option 2: Full Branch Rollback**:
```bash
git checkout master
git branch -D 0387-jsonb-normalization
```

---

## 7. DEPENDENCIES & RISKS

### Dependencies
- PostgreSQL running
- Alembic configured
- `AgentExecution` model exists in `models/agent_identity.py`
- `AgentJobRepository` exists

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration fails | HIGH | Test on dev first, have rollback ready |
| Backfill incorrect | MEDIUM | Verify counts manually on sample data |
| Performance issue | LOW | Counter ops are O(1), should be faster |

---

## 8. SUCCESS CRITERIA

### Functional
- [ ] 3 counter columns exist on `AgentExecution`
- [ ] Migration completes without errors
- [ ] Backfill populates correct counts
- [ ] Repository methods work atomically

### Quality
- [ ] All 7 TDD tests pass
- [ ] No existing test regressions
- [ ] Code follows existing patterns

### Documentation
- [ ] Closeout notes completed
- [ ] Ready for 0387f handover

---

## 9. VALIDATION CHECKLIST

### Pre-Implementation
- [ ] Branch created: `0387-jsonb-normalization`
- [ ] Backup created: `backup_pre_0387_phase4.sql`
- [ ] Baseline tests recorded

### During Implementation
- [ ] RED phase: All 7 tests fail
- [ ] GREEN phase: All 7 tests pass
- [ ] No linting errors

### Post-Implementation
- [ ] Full test suite passes
- [ ] Migration applied successfully
- [ ] Counters visible in database

---

## 10. REFERENCES

### Related Code
- `src/giljo_mcp/models/agent_identity.py` - AgentExecution model
- `src/giljo_mcp/repositories/agent_job_repository.py` - Repository
- `src/giljo_mcp/services/message_service.py` - Will use counters in 0387f

### Related Handovers
- **0387** (Parent): Broadcast Fan-out at Write
- **0387f** (Next): Backend Stop JSONB Writes
- **0420 Series**: Model for comprehensive refactoring

---

## CLOSEOUT NOTES

**Status**: ✅ COMPLETED

### Implementation Summary
- Date Completed: 2026-01-17
- Implemented By: Claude Opus 4.5 with TDD/database-expert subagents
- Time Taken: ~45 minutes

### Files Modified
1. `src/giljo_mcp/models/agent_identity.py` (+18 lines) - Added 3 counter columns
2. `src/giljo_mcp/repositories/agent_job_repository.py` (+97 lines) - Added 3 atomic counter methods
3. `migrations/versions/0387e_add_message_counters.py` (NEW, 176 lines) - Alembic migration with backfill
4. `tests/unit/test_message_counters.py` (NEW, 338 lines) - 7 TDD tests

### Test Results
- Baseline: 1838 tests collected (4 collection errors)
- Final: All 7 new tests pass
- New tests added: 7
- Pre-existing failures unrelated to this handover

### Unexpected Discoveries
- Test database (`giljo_mcp_test`) runs separately from main database (`giljo_mcp`)
- Migration needed to be applied to BOTH databases manually
- Table name is `agent_executions` (not `mcp_agent_executions` as in handover doc)
- Message sender stored in `meta_data->>'_from_agent'` not `from_agent` column

### Handover to 0387f
- ✅ 3 counter columns exist on `AgentExecution` model
- ✅ Migration applied to both main and test databases
- ✅ Backfill logic runs correctly
- ✅ Repository methods available:
  - `increment_sent_count(session, agent_id, tenant_key)`
  - `increment_waiting_count(session, agent_id, tenant_key)`
  - `decrement_waiting_increment_read(session, agent_id, tenant_key)`
- ✅ All methods use atomic SQL UPDATE with tenant isolation

---

**Document Version**: 1.1
**Last Updated**: 2026-01-17
