# Handover 0622: Self-Healing Decorators Implementation

**Phase**: 4 | **Tool**: CLI | **Agent**: architectural-engineer | **Duration**: 1 day
**Parallel Group**: Sequential | **Depends On**: 0621

## Context
**Read First**: `handovers/600/AGENT_REFERENCE_GUIDE.md`
**This Handover**: Design and implement @ensure_table_exists decorator pattern for on-demand table recreation.

## Tasks

1. **Design Decorator**: Create `@ensure_table_exists(model_class)` in `src/giljo_mcp/utils/decorators.py`
2. **Implementation**: Check if table exists → If not, create from SQLAlchemy model → Log action
3. **Apply to Services**: All CRUD methods in ProductService, ProjectService, TaskService, MessageService, ContextService, OrchestrationService
4. **Test**: Delete table → Call decorated method → Verify table recreated
5. **Document**: Create `docs/guides/self_healing_architecture.md`

## Example Implementation
```python
def ensure_table_exists(model_class):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            engine = get_engine()
            inspector = inspect(engine)
            table_name = model_class.__tablename__
            if table_name not in inspector.get_table_names():
                logger.warning(f"Table {table_name} missing - creating on-demand")
                model_class.__table__.create(engine)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## Test Coverage
**File**: `tests/unit/test_decorators.py` (10+ tests)
- Table recreation, logging verification, multi-table handling, performance impact

## Success Criteria
- [ ] @ensure_table_exists implemented
- [ ] Applied to all service CRUD methods
- [ ] Tests pass (table recreation verified)
- [ ] Documentation created

## Deliverables
**Created**: `src/giljo_mcp/utils/decorators.py`, `tests/unit/test_decorators.py`, `docs/guides/self_healing_architecture.md`
**Commit**: `feat: Implement self-healing table decorators (Handover 0622)`

**Document Control**: 0622 | 2025-11-14
