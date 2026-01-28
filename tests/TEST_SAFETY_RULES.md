# Test Safety Rules

## CRITICAL: Production Database Protection

**NEVER** connect tests to the production database `giljo_mcp`.

**ALWAYS** use `giljo_mcp_test` for testing.

---

## Enforcement Layers

### Layer 1: Code Guards (test_db_helper.py)
```python
from tests.helpers.test_db_helper import validate_database_name

# This will RAISE RuntimeError if you try to use production DB:
validate_database_name("giljo_mcp")  # FAILS!
validate_database_name("giljo_mcp_test")  # OK
```

### Layer 2: Pytest Hook (conftest.py)
The `pytest_configure()` hook checks `DATABASE_URL` environment variable and warns if it points to production.

### Layer 3: Fixture Defaults (base_fixtures.py)
All standard fixtures (`db_manager`, `db_session`) default to `giljo_mcp_test`.

---

## How to Write Safe Tests

### CORRECT - Use fixtures from conftest.py:
```python
async def test_something(db_session):
    # db_session is automatically connected to giljo_mcp_test
    result = await db_session.execute(...)
```

### CORRECT - Use PostgreSQLTestHelper:
```python
from tests.helpers.test_db_helper import PostgreSQLTestHelper

url = PostgreSQLTestHelper.get_test_db_url()  # Always returns test DB
```

### WRONG - Never do this:
```python
# DANGEROUS! This could hit production!
conn = psycopg2.connect(database="giljo_mcp")  # NO!
conn = asyncpg.connect("postgresql://localhost/giljo_mcp")  # NO!
```

---

## Test Markers

Use markers to categorize tests (defined in pyproject.toml):

```python
@pytest.mark.slow
def test_heavy_operation():
    ...

@pytest.mark.integration
def test_with_real_db():
    ...

@pytest.mark.smoke
def test_critical_path():
    ...
```

Run specific categories:
```bash
pytest -m "not slow"        # Skip slow tests
pytest -m integration       # Only integration tests
pytest -m "smoke"           # Only smoke tests
```

---

## Files That Define Test Behavior

| File | Purpose |
|------|---------|
| `pyproject.toml` | Main pytest config (markers, paths, coverage) |
| `pytest_no_coverage.ini` | Alternative config without coverage |
| `tests/conftest.py` | Shared fixtures and pytest hooks |
| `tests/helpers/test_db_helper.py` | Database connection helpers with safety |
| `tests/fixtures/base_fixtures.py` | Base test data fixtures |
| `tests/pytest_postgresql_plugin.py` | PostgreSQL-specific pytest plugin |

---

## Adding New Safety Rules

1. **For database rules**: Add to `test_db_helper.py`
2. **For test collection rules**: Add hook to `conftest.py`
3. **For new markers**: Add to `pyproject.toml` under `[tool.pytest.ini_options]`
4. **For coverage rules**: Add to `[tool.coverage.run]` in `pyproject.toml`
