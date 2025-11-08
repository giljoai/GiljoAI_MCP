# Migration Strategy - Unified Agent State Architecture

## Timeline: 4 Weeks

### Week 1: Database Schema
- Create migration script
- Test on staging
- Deploy to production
- Verify with queries

### Week 2: Core Components + API
- Create StateTransitionManager
- Create MessageInterceptor
- Enhance Health Monitor
- Update API endpoints
- Deploy to production

### Week 3-4: Agent Model Deprecation
- Add deprecation warnings
- Create migration script
- Test migration
- Deploy migration

## Phase 1: Database (Week 1)

### Migration Script

alembic/versions/0108_unified_agent_state.py

```python
def upgrade():
    op.add_column('mcp_agent_jobs',
        sa.Column('version', sa.Integer(), default=1))
    op.add_column('mcp_agent_jobs',
        sa.Column('cancelled_at', sa.DateTime(timezone=True)))
    op.drop_constraint('ck_mcp_agent_job_status')
    op.create_check_constraint('ck_mcp_agent_job_status',
        'mcp_agent_jobs', "status IN (...)")
```

### Verification

```sql
SELECT COUNT(*) FROM mcp_agent_jobs WHERE version IS NULL;
-- Expected: 0
```

### Rollback

```bash
alembic downgrade -1
```

## Phase 2: Code Deployment (Week 2)

### New Files
- src/giljo_mcp/types/job_status.py
- src/giljo_mcp/state_manager.py
- src/giljo_mcp/message_interceptor.py

### Modified Files
- api/endpoints/agent_jobs.py
- api/schemas/agent_jobs.py

### Testing
- Unit tests: 100+ tests
- Integration tests: 30+ tests
- API tests: 20+ tests

## Phase 3: Agent Migration (Week 3-4)

### Add Deprecation Warning

```python
class Agent(Base):
    def __init__(self):
        warnings.warn("Agent deprecated. Use MCPAgentJob.")
```

### Migration Script

scripts/migrate_agent_to_mcpagentjob.py

```bash
python scripts/migrate_agent_to_mcpagentjob.py --dry-run
python scripts/migrate_agent_to_mcpagentjob.py --execute
```

## Rollback Procedures

### Database Rollback
alembic downgrade -1

### Code Rollback
git revert <commit>

### Data Rollback
Restore from backup

## Success Criteria

- Zero data loss
- All tests passing
- Performance < 100ms
- Zero production incidents
