# Handover 0414b: TDD RED Tests Summary

**Status**: ✅ Complete
**Date**: 2026-01-11
**Phase**: Phase B - TDD RED (Write Failing Tests)

## Overview

Created comprehensive failing tests that define expected behavior after the `agent_type` → `agent_display_name` migration. Tests are designed to FAIL now and PASS after Phase E implementation.

## Test Files Created

### 1. `tests/models/test_agent_display_name_migration.py`

**Purpose**: Test database model and column changes
**Test Count**: 9 tests
**Coverage**:

#### TestAgentDisplayNameModelAttribute (3 tests)
- ✅ `test_agent_execution_has_agent_display_name_attribute` - Verifies new attribute exists
- ✅ `test_agent_execution_does_not_have_agent_type_attribute` - Verifies old attribute removed
- ✅ `test_agent_execution_agent_name_still_exists` - Verifies NORTH STAR preserved

#### TestAgentDisplayNameDatabaseColumn (3 tests)
- ✅ `test_database_column_named_agent_display_name` - Verifies column renamed in database
- ✅ `test_agent_display_name_column_not_null_constraint` - Verifies NOT NULL constraint
- ✅ `test_agent_display_name_column_max_length` - Verifies VARCHAR(100) constraint

#### TestAgentDisplayNameQueryOperations (2 tests)
- ✅ `test_filter_by_agent_display_name` - Verifies WHERE clause works
- ✅ `test_order_by_agent_display_name` - Verifies ORDER BY works

#### TestAgentDisplayNameReprMethod (1 test)
- ✅ `test_repr_includes_agent_display_name` - Verifies __repr__ updated

**Expected Failures**:
```python
TypeError: 'agent_display_name' is an invalid keyword argument for AgentExecution
OperationalError: column agent_display_name does not exist
AttributeError: 'AgentExecution' object has no attribute 'agent_display_name'
```

### 2. `tests/api/test_agent_display_name_schemas.py`

**Purpose**: Test API schemas and WebSocket events
**Test Count**: 20 tests
**Coverage**:

#### TestSpawnAgentRequestSchema (3 tests)
- ✅ Request schema has `agent_display_name` field
- ✅ Request schema does NOT have `agent_type` field
- ✅ Validation requires `agent_display_name`

#### TestJobResponseSchema (2 tests)
- ✅ Response schema has `agent_display_name` field
- ✅ Response schema does NOT have `agent_type` field

#### TestChildJobSpecSchema (2 tests)
- ✅ Child job spec uses `agent_display_name`
- ✅ Child job spec does NOT use `agent_type`

#### TestAgentStatusChangedEventSchema (3 tests)
- ✅ WebSocket event data has `agent_display_name`
- ✅ WebSocket event data does NOT have `agent_type`
- ✅ EventFactory uses `agent_display_name` parameter

#### TestAgentCreatedEventSchema (2 tests)
- ✅ Agent data in event has `agent_display_name`
- ✅ Agent data does NOT have `agent_type`

#### TestAPIEndpointResponseSchemas (1 test)
- ✅ Endpoint model uses `agent_display_name`

#### TestAPIIntegrationEndToEnd (3 tests)
- ✅ Spawn agent API uses `agent_display_name` in request
- ✅ List jobs API returns `agent_display_name` in response
- ✅ Get job API returns `agent_display_name` in response

#### TestWebSocketEventSchemas (2 tests)
- ✅ EventFactory creates events with `agent_display_name`
- ✅ Agent created events use `agent_display_name`

#### TestBackwardCompatibilityConsiderations (2 tests)
- ✅ Documents breaking change of removing `agent_type`
- ✅ Documents preservation of `agent_name` (NORTH STAR)

**Expected Failures**:
```python
ValidationError: Field 'agent_type' required [type=missing]
KeyError: 'agent_display_name' not in response
TypeError: unexpected keyword argument 'agent_display_name'
```

## Verification Results

### Model Tests (9 tests collected)
```bash
$ pytest tests/models/test_agent_display_name_migration.py --collect-only
collected 9 items
```

**Sample Failure**:
```
TypeError: 'agent_display_name' is an invalid keyword argument for AgentExecution
```
✅ Expected failure confirmed

### API Schema Tests (20 tests collected)
```bash
$ pytest tests/api/test_agent_display_name_schemas.py --collect-only
collected 20 items
```

**Sample Failure**:
```
ValidationError: 1 validation error for SpawnAgentRequest
agent_type
  Field required [type=missing]
```
✅ Expected failure confirmed

## Semantic Clarity Preserved

All tests maintain semantic distinction:
- `agent_name` = NORTH STAR (template lookup key) - **UNCHANGED**
- `agent_display_name` = UI LABEL (what humans see) - **NEW NAME**
- `agent_type` = OLD ambiguous name - **TO BE REMOVED**

## Test Design Principles

1. **TDD RED Phase**: Tests written FIRST, implementation LATER
2. **Expected Failures**: All tests designed to fail with specific errors
3. **Comprehensive Coverage**: Models, schemas, events, API endpoints
4. **Clear Documentation**: Each test explains WHY it should fail
5. **Backward Compatibility**: Tests document breaking changes

## Files Modified

### Created
- `tests/models/test_agent_display_name_migration.py` (529 lines)
- `tests/api/test_agent_display_name_schemas.py` (605 lines)
- `handovers/0414b_tdd_red_test_summary.md` (this file)

### Referenced (for patterns)
- `tests/models/test_agent_execution.py`
- `tests/api/test_agent_jobs_api.py`
- `src/giljo_mcp/models/agent_identity.py`
- `api/schemas/agent_job.py`
- `api/events/schemas.py`
- `api/endpoints/agent_jobs/models.py`

## Next Steps (Phase 0414e)

After Phase 0414c (Database Migration Script) and Phase 0414d (Service Layer Updates):

### Phase 0414e: Implementation (GREEN Phase)
1. **Update Model**: Change `agent_type` to `agent_display_name` in AgentExecution
2. **Update Schemas**: Change all Pydantic schemas to use `agent_display_name`
3. **Update Events**: Change WebSocket event schemas
4. **Update __repr__**: Change AgentExecution.__repr__() method
5. **Run Tests**: All 29 tests should PASS after implementation

### Success Criteria
```bash
# All tests should pass after Phase 0414e
pytest tests/models/test_agent_display_name_migration.py -v  # 9 passing
pytest tests/api/test_agent_display_name_schemas.py -v       # 20 passing
```

## Migration Safety

### Breaking Changes Documented
- ✅ Tests document that `agent_type` removal is breaking
- ✅ Tests verify `agent_name` preservation (no breaking change)
- ✅ Tests cover all API request/response schemas
- ✅ Tests cover all WebSocket event schemas

### Validation Coverage
- ✅ Database column constraints (NOT NULL, VARCHAR(100))
- ✅ Pydantic validation (required field)
- ✅ Query operations (WHERE, ORDER BY)
- ✅ API integration (request → response flow)

## Notes

- Tests use existing project patterns from `test_agent_execution.py` and `test_agent_jobs_api.py`
- Integration tests require fixtures from `conftest.py` (tenant_a_admin_token, etc.)
- All tests are async where appropriate (database operations)
- Clear comments explain expected failures and reasons
- Tests will guide implementation in Phase 0414e

## Handover Context

**Previous**: 0414a (Inventory - identified 18+ locations requiring changes)
**Current**: 0414b (TDD RED - wrote 29 failing tests)
**Next**: 0414c (Database Migration Script - Alembic migration)

**Status**: Ready for Phase 0414c (Database Migration Script creation)
