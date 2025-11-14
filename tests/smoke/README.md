# Smoke Tests

## Overview

Smoke tests are **integration workflow validators** that test critical end-to-end paths in the GiljoAI MCP system. They verify that core workflows work correctly, not individual function coverage.

## Purpose

- Validate multi-component integration (API + Database + WebSocket + MCP Tools)
- Test real-world user workflows (project lifecycle, product vision, succession, etc.)
- Ensure critical paths work after major changes
- Quick validation before deployments

## Running Smoke Tests

### Recommended (No Coverage)

Smoke tests should be run **WITHOUT coverage collection** to avoid threshold failures:

```bash
# Run all smoke tests (RECOMMENDED)
pytest tests/smoke/ -m smoke --no-cov -v

# Run specific smoke test
pytest tests/smoke/test_tenant_isolation_smoke.py -m smoke --no-cov -v

# Run smoke tests with detailed output
pytest tests/smoke/ -m smoke --no-cov -vv -s
```

### With Coverage (Not Recommended)

If you need to collect coverage data (for analysis, not enforcement):

```bash
# This will collect coverage but may fail on threshold (expected)
pytest tests/smoke/ -m smoke -v --cov-report=term

# Coverage threshold failures are EXPECTED and can be ignored for smoke tests
```

## Why No Coverage Threshold?

1. **Integration tests measure workflows, not code coverage**: Smoke tests validate that components integrate correctly, which is a different quality metric than unit test coverage.

2. **Low apparent coverage is normal**: A single smoke test may only exercise 5-10% of the codebase but still validate a complete user workflow.

3. **Coverage thresholds are for unit tests**: The 80% coverage threshold is designed for unit/API tests that systematically test individual functions.

4. **Smoke tests complement unit tests**: Unit tests provide coverage depth, smoke tests provide integration breadth.

## Test Structure

Each smoke test follows this pattern:

```python
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_workflow_name_smoke(authenticated_client, db_manager):
    """
    Smoke test for [workflow name].

    Validates:
    - Component A integrates with Component B
    - Workflow X completes successfully
    - Data Y persists correctly
    """
    client, user = authenticated_client

    # Test workflow steps
    # ...

    # Assertions on workflow success
    assert ...
```

## Available Smoke Tests

1. **test_tenant_isolation_smoke.py**: Multi-tenant data isolation
2. **test_project_lifecycle_smoke.py**: Project CRUD workflow
3. **test_succession_smoke.py**: Orchestrator succession workflow
4. **test_product_vision_smoke.py**: Product vision generation workflow
5. **test_settings_smoke.py**: Settings persistence workflow

## Coverage Configuration

Smoke tests are **explicitly exempted** from coverage thresholds in:

- **.coveragerc**: `omit = tests/smoke/*`
- **pyproject.toml**: `[tool.coverage.run] omit = ["tests/smoke/*"]`

This exemption means:
- ✅ Smoke tests can run with `--no-cov` without errors
- ✅ Smoke test files are excluded from coverage reports
- ⚠️ Running with coverage will still measure the codebase (not the tests), which may fail threshold

## Best Practices

1. **Always use --no-cov flag**: This is the intended way to run smoke tests
2. **Keep smoke tests fast**: Aim for <10 seconds per test
3. **Test real workflows**: Don't mock core components (DB, API, etc.)
4. **Validate end-to-end**: Test the full user journey, not isolated functions
5. **Use descriptive names**: Test names should clearly indicate the workflow being validated

## Integration with CI/CD

In CI/CD pipelines, run smoke tests separately from unit tests:

```yaml
# Good CI/CD setup
- name: Run Unit Tests
  run: pytest tests/unit/ tests/api/ --cov=giljo_mcp --cov-fail-under=80

- name: Run Smoke Tests
  run: pytest tests/smoke/ -m smoke --no-cov -v
```

## Questions?

- Smoke tests failing? Check logs for actual errors (not coverage threshold failures)
- Need to add a new smoke test? Follow the pattern in existing tests
- Coverage confusion? Remember: smoke tests validate workflows, not coverage

---

**TL;DR**: Always run smoke tests with `pytest tests/smoke/ -m smoke --no-cov -v`
