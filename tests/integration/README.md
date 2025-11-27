# Integration Tests (E2E) - README

## Purpose

Integration tests in this directory validate end-to-end workflows and component interactions in the GiljoAI MCP system. These tests simulate real-world scenarios where multiple components (database, API endpoints, orchestrator, agents) work together.

**Key Difference from Unit Tests**: Integration tests validate **workflows** and **component interactions**, not systematic code coverage. They may only exercise 5-10% of the codebase while still providing valuable validation of critical paths.

## Running Integration Tests

### Without Coverage (Recommended)

Integration tests should be run with the `--no-cov` flag to avoid coverage threshold failures:

```bash
# Run all integration tests (RECOMMENDED)
pytest tests/integration/ --no-cov -v

# Run specific integration test
pytest tests/integration/test_e2e_project_lifecycle.py --no-cov -v

# Run with detailed output
pytest tests/integration/ --no-cov -vv -s
```

### With Coverage (For Analysis Only)

If you need to collect coverage data for analysis (not enforcement):

```bash
# This will collect coverage but may fail on threshold (expected)
pytest tests/integration/ -v --cov-fail-under=0
```

**Note**: Coverage threshold failures are EXPECTED and can be ignored for integration tests.

## Why No Coverage Threshold?

1. **Integration tests measure workflows, not code coverage**: These tests validate that components integrate correctly, which is a different quality metric than unit test coverage.

2. **Low apparent coverage is normal**: A single integration test may only exercise 5-10% of the codebase but still validate a complete user workflow (orchestrator → agents → database → API).

3. **Coverage thresholds are for unit tests**: The 80% coverage threshold is designed for unit/API tests that systematically test individual functions.

4. **Integration tests complement unit tests**: Unit tests provide coverage depth, integration tests provide workflow breadth.

## Test Structure

Integration tests follow this pattern:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_name(
    db_session,
    test_user,
    test_product,
    test_project,
    orchestrator_simulator,
):
    """
    Integration test for [workflow name].

    Validates:
    - Component A integrates with Component B
    - Workflow X completes successfully
    - Database state is consistent
    """
    # Execute workflow steps
    # ...

    # Assertions on workflow success and database state
    assert ...
```

## Available Integration Tests

### test_e2e_project_lifecycle.py

Complete E2E project lifecycle simulation with 9 comprehensive tests:

1. **test_full_lifecycle_staging_to_closeout**: Full orchestrator → agents → closeout pipeline
2. **test_serena_mcp_integration**: Serena symbolic tool integration validation
3. **test_github_toggle_enabled**: GitHub integration enabled scenario
4. **test_github_toggle_disabled**: Manual summary scenario (GitHub disabled)
5. **test_context_priority_settings**: Field priority configuration validation
6. **test_agent_template_manager_enabled_agents**: Active agent discovery
7. **test_agent_template_manager_disabled_agents**: Inactive agent filtering
8. **test_inter_agent_communication**: Message queue validation
9. **test_orchestrator_context_tracking**: Context budget monitoring

## Test Fixtures

Integration tests use shared fixtures from `tests/conftest.py`:

- `db_session`: AsyncSession for database operations
- `test_user`: Test user with multi-tenant isolation
- `test_product`: Test product with product_memory
- `test_project`: Test project linked to user/product
- `orchestrator_job`: MCPAgentJob instance for orchestrator
- `orchestrator_simulator`: OrchestratorSimulator for workflow simulation
- `mock_agent_simulator_factory`: Factory for creating agent simulators
- `test_agent_templates`: Pre-seeded agent templates (5 agents: 3 active, 2 inactive)

## Coverage Configuration

Integration tests are **NOT explicitly exempted** from coverage measurement (unlike smoke tests), but should be run with `--no-cov` to avoid threshold failures.

**Why?**
- Integration tests exercise real database operations and API calls
- They provide actual coverage data (albeit low percentage)
- Running with `--no-cov` is the recommended approach to avoid misleading failures

## Best Practices

1. **Always use --no-cov flag**: This is the intended way to run integration tests
2. **Test real components**: Don't mock database, API endpoints, or core services
3. **Validate end-to-end workflows**: Test the full user journey, not isolated functions
4. **Use realistic test data**: Create test users, products, projects with proper tenant isolation
5. **Verify database state**: Check that database state is consistent after workflow execution
6. **Test multi-tenant isolation**: Ensure tenant_key filtering works correctly
7. **Use descriptive names**: Test names should clearly indicate the workflow being validated

## Integration with CI/CD

In CI/CD pipelines, run integration tests separately from unit tests:

```yaml
# Good CI/CD setup
- name: Run Unit Tests
  run: pytest tests/unit/ tests/api/ --cov=giljo_mcp --cov-fail-under=80

- name: Run Integration Tests
  run: pytest tests/integration/ --no-cov -v

# Bad CI/CD setup (DON'T DO THIS)
- name: Run All Tests
  run: pytest tests/ --cov=giljo_mcp --cov-fail-under=80  # Will fail on integration tests!
```

## Troubleshooting

### Issue: "Coverage failure: total of X is less than fail-under=80.00"

**Solution**: Run integration tests with `--no-cov` flag:
```bash
pytest tests/integration/ --no-cov -v
```

### Issue: Integration tests fail even with `--no-cov`

**Solution**: Check for actual test failures (not coverage issues):
- Look at error messages (authentication, database, etc.)
- Check test setup fixtures in `tests/conftest.py`
- Verify database state (PostgreSQL running, tables created)
- Review API endpoint availability (backend server running)

### Issue: Database connection errors

**Solution**: Ensure PostgreSQL is running and database exists:
```bash
# Windows (Git Bash)
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -l

# Check if giljo_mcp database exists
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"
```

### Issue: Fixture errors (test_user, test_product, etc.)

**Solution**: Check `tests/conftest.py` for fixture implementations. Ensure:
- Database session is properly initialized
- Fixtures use correct async/await patterns
- Multi-tenant isolation (tenant_key) is configured
- Fixtures clean up after tests (no data leakage)

## Expected Results

When running integration tests with `--no-cov`:

✅ **PASS**: 9/9 tests passing (100% success rate)
✅ **TIME**: ~3-6 seconds total execution time
✅ **OUTPUT**: Clean output with no coverage threshold errors
✅ **DATABASE**: Test data isolated by tenant_key, cleaned up after tests

Example output:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.4.2, pluggy-1.6.0
collected 9 items

tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_full_lifecycle_staging_to_closeout PASSED [ 11%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_serena_mcp_integration PASSED [ 22%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_github_toggle_enabled PASSED [ 33%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_github_toggle_disabled PASSED [ 44%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_context_priority_settings PASSED [ 55%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_agent_template_manager_enabled_agents PASSED [ 66%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_agent_template_manager_disabled_agents PASSED [ 77%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_inter_agent_communication PASSED [ 88%]
tests/integration/test_e2e_project_lifecycle.py::TestCompleteProjectLifecycle::test_orchestrator_context_tracking PASSED [100%]

============================== 9 passed in 3.09s ==============================
```

## Questions?

- Integration tests failing? Check logs for actual errors (not coverage threshold failures)
- Need to add a new integration test? Follow the pattern in existing tests (use fixtures, test workflows)
- Coverage confusion? Remember: integration tests validate workflows, not coverage
- Database issues? Verify PostgreSQL running and giljo_mcp database exists
- Multi-tenant isolation? All tests should filter by tenant_key (check test fixtures)

## Related Documentation

- [Testing Guide](../../docs/TESTING.md) - Comprehensive testing strategy
- [Smoke Tests README](../smoke/README.md) - Similar workflow-based testing approach
- [Services Documentation](../../docs/SERVICES.md) - Service layer patterns used in tests
- [Orchestrator Documentation](../../docs/ORCHESTRATOR.md) - Orchestrator workflow details
