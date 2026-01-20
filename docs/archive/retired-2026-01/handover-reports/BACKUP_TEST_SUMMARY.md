# Database Backup Test Suite - TDD Summary

**Date**: 2025-10-24
**Agent**: Backend Integration Tester
**Methodology**: Test-Driven Development (TDD)

## Overview

Comprehensive test suite for database backup functionality following TDD methodology. Tests define expected behavior for both MCP tool and API endpoint **before** implementation exists.

## Test Coverage Summary

| Component | Integration Tests | Unit Tests | Total Tests |
|-----------|------------------|------------|-------------|
| MCP Tool (`backup_database`) | 21 | 42 | 63 |
| API Endpoint (`POST /api/backup/database`) | 16 | 27 | 43 |
| **Total** | **37** | **69** | **106** |

## Test Files

### Integration Tests
- **File**: `tests/integration/test_backup_integration.py`
- **Lines**: 700+
- **Coverage**: End-to-end workflows with real database

### Unit Tests
- **File**: `tests/unit/test_backup_tool.py` (MCP tool)
- **Lines**: 400+
- **Coverage**: Tool registration, validation, error handling

- **File**: `tests/unit/test_backup_endpoint.py` (API endpoint)
- **Lines**: 600+
- **Coverage**: Routing, authentication, response structure

## Expected Behavior (Defined by Tests)

### MCP Tool: `backup_database`

**Function Signature**:
```python
async def backup_database(tenant_key: str) -> dict
```

**Success Response**:
```json
{
  "success": true,
  "backup_path": "docs/archive/database_backups/2025-10-24_14-30-00",
  "metadata": {
    "timestamp": "2025-10-24T14:30:00Z",
    "tenant_key": "tenant_abc123",
    "tables_backed_up": ["users", "projects", "agents", "messages", "tasks"],
    "record_counts": {
      "users": 10,
      "projects": 5,
      "agents": 15,
      "messages": 42,
      "tasks": 8
    },
    "duration_seconds": 2.34
  }
}
```

**Failure Response**:
```json
{
  "success": false,
  "error": "Database connection failed: FATAL: password authentication failed"
}
```

### API Endpoint: `POST /api/backup/database`

**Authentication**: Required (JWT token in Authorization header)

**Request**: No body required (tenant extracted from authenticated user)

**Success Response (200 OK)**:
```json
{
  "success": true,
  "backup_path": "docs/archive/database_backups/2025-10-24_14-30-00",
  "metadata": {
    "timestamp": "2025-10-24T14:30:00Z",
    "tenant_key": "tenant_abc123",
    "tables_backed_up": ["users", "projects", "agents"],
    "record_counts": {"users": 10, "projects": 5, "agents": 15}
  },
  "message": "Database backup completed successfully"
}
```

**Error Responses**:
- **401 Unauthorized**: Missing or invalid JWT token
- **403 Forbidden**: Inactive user or insufficient permissions
- **500 Internal Server Error**: Database or filesystem errors

## Test Categories

### 1. Happy Path Tests (Success Scenarios)

**MCP Tool**:
- `test_backup_database_tool_success` - Basic successful backup
- `test_backup_tool_returns_dict` - Returns dictionary structure
- `test_backup_tool_returns_required_fields` - All required fields present

**API Endpoint**:
- `test_backup_endpoint_success` - Successful backup via API
- `test_backup_endpoint_returns_json` - JSON response format
- `test_backup_endpoint_success_response_structure` - Complete structure

### 2. Multi-Tenant Isolation (CRITICAL)

**MCP Tool**:
- `test_backup_database_tool_multi_tenant_isolation` - Only backs up specified tenant
- `test_backup_tool_metadata_contains_tenant` - Metadata includes tenant_key

**API Endpoint**:
- `test_backup_endpoint_uses_authenticated_user_tenant` - Uses user's tenant
- `test_backup_endpoint_multi_tenant_isolation` - Filters by user's tenant

**Expected Behavior**:
- Backup includes ONLY data for specified tenant_key
- Other tenants' data must NOT appear in backup
- Metadata must clearly indicate which tenant was backed up

### 3. Authentication & Authorization

**API Endpoint**:
- `test_backup_endpoint_requires_authentication` - Returns 401 without token
- `test_backup_endpoint_rejects_invalid_token` - Returns 401 for invalid token
- `test_backup_endpoint_accepts_valid_token` - Accepts valid JWT
- `test_backup_endpoint_inactive_user_denied` - Denies inactive users (401/403)
- `test_backup_endpoint_rejects_inactive_user` - Unit test for inactive users

### 4. Input Validation

**MCP Tool**:
- `test_backup_tool_handles_missing_tenant_key` - Raises ValueError/TypeError for None
- `test_backup_tool_handles_invalid_tenant_key_type` - Validates type
- `test_backup_tool_passes_tenant_to_utility` - Correctly passes tenant_key

**API Endpoint**:
- `test_backup_endpoint_accepts_empty_body` - No body required
- `test_backup_endpoint_ignores_extra_fields` - Ignores unexpected fields

### 5. Error Handling

**MCP Tool**:
- `test_backup_database_tool_handles_database_error` - ConnectionError handling
- `test_backup_database_tool_handles_filesystem_error` - PermissionError handling
- `test_backup_tool_handles_import_error` - ImportError handling
- `test_backup_tool_handles_connection_error` - Database connection failures
- `test_backup_tool_handles_permission_error` - Filesystem permission errors
- `test_backup_tool_handles_generic_exception` - Unexpected exceptions
- `test_backup_tool_logs_errors` - Error logging verification

**API Endpoint**:
- `test_backup_endpoint_handles_database_error` - Returns 500 for DB errors
- `test_backup_endpoint_handles_filesystem_error` - Returns 500 for FS errors
- `test_backup_endpoint_returns_500_on_database_error` - Status code validation
- `test_backup_endpoint_returns_500_on_filesystem_error` - Status code validation
- `test_backup_endpoint_database_error_message` - Helpful error messages
- `test_backup_endpoint_filesystem_error_message` - Clear error descriptions

### 6. Edge Cases

**MCP Tool**:
- `test_backup_database_tool_handles_empty_database` - Handles tenant with no data
- `test_backup_with_special_characters_in_tenant` - Unicode characters
- `test_backup_with_very_long_tenant_key` - 500+ character tenant keys
- `test_backup_creates_directory_structure` - Creates necessary directories
- `test_backup_tool_with_unicode_tenant_key` - Japanese characters
- `test_backup_tool_timeout_handling` - Long-running operations

**API Endpoint**:
- `test_backup_endpoint_with_special_tenant_characters` - Unicode handling
- `test_backup_endpoint_handles_concurrent_requests` - Multiple simultaneous requests

### 7. Performance Tests

**MCP Tool**:
- `test_backup_database_tool_performance` - Completes in <5s for small datasets
- `test_backup_with_large_dataset` - 50 projects + 150 agents in <30s
- `test_backup_does_not_lock_database` - No blocking of concurrent operations

**API Endpoint**:
- `test_backup_endpoint_performance` - API responds in <10s
- `test_backup_endpoint_concurrent_requests` - Handles concurrent backups

**Performance Targets**:
- Small datasets (1 project, 3 agents): **< 5 seconds**
- Large datasets (50 projects, 150 agents): **< 30 seconds**
- API overhead: **< 5 seconds** (on top of backup time)
- No database locking (concurrent operations allowed)

### 8. Tool Registration & Integration

**MCP Tool**:
- `test_backup_tool_registered` - Appears in MCP tool list
- `test_backup_tool_has_description` - Has proper description
- `test_backup_tool_has_correct_signature` - Correct function signature
- `test_backup_tool_is_async` - Is async function
- `test_backup_tool_can_be_invoked_via_tool_system` - Callable through system
- `test_backup_tool_metadata_correct` - Correct metadata
- `test_backup_tool_appears_in_tool_list` - In tool listing

**API Endpoint**:
- `test_backup_endpoint_registered` - Route registered in FastAPI
- `test_backup_endpoint_methods` - Only accepts POST
- `test_backup_endpoint_has_tags` - Has proper OpenAPI tags
- `test_backup_endpoint_in_openapi_schema` - In OpenAPI schema
- `test_backup_endpoint_openapi_method` - POST documented
- `test_backup_endpoint_openapi_responses` - Response codes documented
- `test_backup_endpoint_has_summary` - Has summary/description

### 9. Return Value Structure

**MCP Tool**:
- `test_backup_tool_success_return_structure` - Success structure validation
- `test_backup_tool_failure_return_structure` - Error structure validation
- `test_backup_tool_metadata_contains_timestamp` - Timestamp in ISO format

**API Endpoint**:
- `test_backup_endpoint_returns_proper_json_structure` - Complete JSON structure
- `test_backup_endpoint_error_response_structure` - Error structure (detail field)
- `test_backup_endpoint_returns_200_on_success` - HTTP 200 OK
- `test_backup_endpoint_returns_401_unauthorized` - HTTP 401
- `test_backup_endpoint_returns_500_on_database_error` - HTTP 500

## Critical Test Assertions

### Multi-Tenant Isolation (Zero Tolerance)
```python
# Test creates data for multiple tenants
other_project = Project(tenant_key="other_tenant", ...)
test_project = Project(tenant_key=test_user.tenant_key, ...)

# Backup for test_user
result = await backup_database(tenant_key=test_user.tenant_key)

# MUST only include test_user's data
assert result["metadata"]["tenant_key"] == test_user.tenant_key
# other_tenant data MUST NOT appear in backup
```

### Authentication Requirements
```python
# Without auth header
response = await client.post("/api/backup/database")
assert response.status_code == 401

# With valid auth
response = await client.post("/api/backup/database", headers=auth_headers)
assert response.status_code == 200
```

### Error Handling
```python
# Database error
with patch("...", side_effect=ConnectionError("DB unavailable")):
    result = await backup_database(tenant_key="test")
    assert result["success"] is False
    assert "error" in result
    assert "DB unavailable" in result["error"]
```

### Performance
```python
start = time.time()
result = await backup_database(tenant_key="test")
duration = time.time() - start

assert result["success"] is True
assert duration < 5.0  # Must complete quickly
```

## Test Execution

### Running Tests

```bash
# Run all backup tests
pytest tests/integration/test_backup_integration.py tests/unit/test_backup_tool.py tests/unit/test_backup_endpoint.py -v

# Run integration tests only
pytest tests/integration/test_backup_integration.py -v

# Run unit tests only
pytest tests/unit/test_backup_tool.py tests/unit/test_backup_endpoint.py -v

# Run performance tests (marked as slow)
pytest -m slow tests/integration/test_backup_integration.py -v

# Run with coverage
pytest tests/integration/test_backup_integration.py --cov=src.giljo_mcp.tools.backup --cov=api.endpoints.backup --cov-report=html
```

### Expected Results (Before Implementation)

All tests should **FAIL** with import errors or missing implementations:

```
ERROR: ModuleNotFoundError: No module named 'src.giljo_mcp.tools.backup'
ERROR: ModuleNotFoundError: No module named 'api.endpoints.backup'
ERROR: ImportError: cannot import name 'backup_database' from 'src.giljo_mcp.tools.backup'
```

This is **expected** and **correct** for TDD methodology.

### Expected Results (After Implementation)

All tests should **PASS** with:
- 106 tests passed
- 0 tests failed
- Coverage > 90%

## Implementation Checklist

Based on these tests, the implementation must provide:

### MCP Tool (`src/giljo_mcp/tools/backup.py`)
- [ ] `async def backup_database(tenant_key: str) -> dict`
- [ ] Tool registration in `src/giljo_mcp/tools/__init__.py`
- [ ] Calls `database_backup.create_backup(tenant_key=tenant_key)`
- [ ] Returns `{success: bool, backup_path: str, metadata: dict}` on success
- [ ] Returns `{success: False, error: str}` on failure
- [ ] Validates `tenant_key` parameter (not None, not empty, is string)
- [ ] Handles ConnectionError, PermissionError, ImportError gracefully
- [ ] Logs errors with `logger.error()` or `logger.exception()`

### API Endpoint (`api/endpoints/backup.py`)
- [ ] `@router.post("/api/backup/database")`
- [ ] Requires authentication (JWT token)
- [ ] Extracts `tenant_key` from authenticated user
- [ ] Calls `backup_database` MCP tool or utility
- [ ] Returns 200 OK with JSON: `{success, backup_path, metadata, message}`
- [ ] Returns 401 for unauthenticated requests
- [ ] Returns 403 for inactive users
- [ ] Returns 500 for database/filesystem errors
- [ ] Includes helpful error messages in `detail` field

### Database Backup Utility (`src/giljo_mcp/database_backup.py`)
- [ ] `async def create_backup(tenant_key: str) -> dict`
- [ ] Filters all queries by `tenant_key`
- [ ] Backs up tables: users, projects, agents, messages, tasks
- [ ] Creates backup in `docs/archive/database_backups/YYYY-MM-DD_HH-MM-SS/`
- [ ] Generates metadata: timestamp, tenant_key, tables, record_counts
- [ ] Returns structured result with backup_path and metadata
- [ ] Handles empty databases (zero records)
- [ ] Does not lock database (uses transactions appropriately)

### Endpoint Registration (`api/app.py`)
- [ ] `from api.endpoints import backup`
- [ ] `app.include_router(backup.router, tags=["backup", "admin"])`

## Next Steps for Implementation Agent

1. **Review Tests**: Read test files to understand expected behavior
2. **Create Database Backup Utility**: Implement `src/giljo_mcp/database_backup.py`
3. **Create MCP Tool**: Implement `src/giljo_mcp/tools/backup.py`
4. **Create API Endpoint**: Implement `api/endpoints/backup.py`
5. **Register Components**: Update `__init__.py` and `app.py`
6. **Run Tests**: Execute test suite and fix failures iteratively
7. **Achieve Coverage**: Ensure >90% code coverage
8. **Commit Implementation**: Commit working code with passing tests

## Testing Methodology: TDD Benefits

By writing tests **first**, we've achieved:

1. **Clear Requirements**: Tests document exactly what the code should do
2. **Design Validation**: Function signatures and interfaces defined upfront
3. **Regression Prevention**: Tests catch bugs during implementation
4. **Confidence**: When tests pass, we know implementation is correct
5. **Documentation**: Tests serve as usage examples for future developers

## Quality Assurance Checklist

Before declaring implementation complete:

- [ ] All 106 tests passing
- [ ] Code coverage > 90%
- [ ] Multi-tenant isolation verified in all tests
- [ ] Performance targets met (<5s small, <30s large)
- [ ] Authentication enforced on API endpoint
- [ ] Error messages are clear and helpful
- [ ] OpenAPI documentation generated correctly
- [ ] No database locking (concurrent operations work)
- [ ] Unicode and edge cases handled gracefully
- [ ] Logging implemented for debugging

## Contact

**Test Author**: Backend Integration Tester Agent
**Date**: 2025-10-24
**Commit**: cf7232e (test: Add comprehensive TDD tests for database backup functionality)

---

**Remember**: These tests define the contract. Implementation must satisfy all assertions without modifying tests (unless requirements change).
