# Handover 0730e: API Test Fixes

**Series**: 0730 Service Response Models
**Phase**: 5 of 5 (Extended)
**Priority**: P2
**Estimated Effort**: 4-8 hours
**Agent**: backend-integration-tester
**Created**: 2026-02-09
**Depends On**: 0730d (complete)

## Context

0730d completed services layer validation with 100% pass rate:
- **Services tests**: 531 passed, 32 skipped, 0 failed
- **Unit tests**: 51 passed (verified)
- **Integration tests**: 17 passed (verified)

However, API tests still have **~175 issues** that need the same patterns applied systematically.

## Scope

Fix ~175 API test failures:
- **Failed**: 101 tests
- **Errors**: 74 tests (mostly fixture issues)

All patterns below were validated in 0730d services tests and are ready for systematic application to API tests.

## Patterns to Apply

These patterns were validated in 0730d and should be applied systematically:

### 1. UUID-Based Fixtures

**Problem**: Duplicate key violations when tests run in parallel or fixtures are reused.

**Solution**: Generate unique IDs for every test entity.

```python
from uuid import uuid4

unique_id = str(uuid4())[:8]
user = User(
    id=str(uuid4()),
    username=f"testuser_{unique_id}",
    email=f"test_{unique_id}@example.com",
    org_id=org.id,
    tenant_key=f"tenant_{unique_id}",
    hashed_password="...",
    is_active=True,
)
```

**Key Points**:
- Use `str(uuid4())` for all ID fields
- Use `str(uuid4())[:8]` for human-readable suffixes
- Apply to: usernames, emails, tenant_keys, slugs, names

### 2. org_id NOT NULL (0424j Compliance)

**Problem**: User.org_id is now a required NOT NULL column (migration 0424j).

**Solution**: Always create organization FIRST, then create user with org_id.

```python
# 1. Create organization FIRST
org = Organization(
    id=str(uuid4()),
    tenant_key=f"test_tenant_{unique_id}",
    name=f"Test Org {unique_id}",
    slug=f"test-org-{unique_id}",
    is_active=True,
)
session.add(org)
await session.flush()  # Get org.id assigned

# 2. Then create user with org_id
user = User(
    id=str(uuid4()),
    username=f"testuser_{unique_id}",
    email=f"test_{unique_id}@example.com",
    org_id=org.id,  # Required - NOT NULL constraint
    tenant_key=org.tenant_key,
    hashed_password="...",
    is_active=True,
)
session.add(user)
await session.flush()
```

**Key Points**:
- Organization must be created and flushed BEFORE user
- User.org_id must be set to valid org.id
- User.tenant_key should match org.tenant_key
- Never create User without org_id

### 3. Exception-Based Assertions

**Problem**: Services no longer return `{"success": False, "error": "..."}` dicts.

**Solution**: Use `pytest.raises()` for error cases.

```python
# OLD (dict wrapper pattern - no longer valid)
result = await service.some_method()
assert result["success"] is False
assert "error" in result

# NEW (exception-based pattern - correct)
with pytest.raises(ValidationError) as exc_info:
    await service.some_method()
assert "expected error message" in str(exc_info.value)
```

**Exception Types**:
- `ResourceNotFoundError` - 404 cases
- `ValidationError` - 422 cases (bad input)
- `AlreadyExistsError` - 409 cases (duplicates)
- `AuthorizationError` - 403 cases (permission denied)
- `DatabaseError` - 500 cases (DB issues)

### 4. API URL Versioning

**Problem**: Some tests use `/api/endpoint` instead of `/api/v1/endpoint`.

**Solution**: Always use `/api/v1/` prefix for API endpoints.

```python
# CORRECT
response = await client.get("/api/v1/tasks/")
response = await client.post("/api/v1/users/", json=data)

# INCORRECT
response = await client.get("/api/tasks/")  # Missing /v1/
response = await client.post("/api/users/", json=data)  # Missing /v1/
```

**Key Points**:
- All API endpoints are versioned under `/api/v1/`
- Check all URLs in test files
- Update assertions for URL paths

### 5. authed_client Fixture Usage

**Problem**: Tests manually creating async clients with API key headers.

**Solution**: Use the `authed_client` fixture for authenticated requests.

```python
# OLD (manual authentication)
async def test_something(async_client: AsyncClient, test_user):
    headers = {"X-API-Key": test_user["api_key"]}
    response = await async_client.get("/api/v1/endpoint", headers=headers)

# NEW (authed_client fixture)
async def test_something(authed_client: AsyncClient):
    response = await authed_client.get("/api/v1/endpoint")
    # API key is automatically included in headers
```

**Key Points**:
- `authed_client` fixture automatically includes API key
- Simplifies test code
- Ensures consistent authentication

## Files to Fix

Priority order (by expected error count):

1. **`tests/api/test_agent_jobs_api.py`** - Agent job lifecycle tests
2. **`tests/api/test_projects_api.py`** - Project CRUD tests
3. **`tests/api/test_agent_jobs_messages.py`** - Message handling tests
4. **`tests/api/test_tasks_api.py`** - Task management tests
5. **`tests/api/test_users_api.py`** - User management tests
6. **`tests/api/test_organizations_api.py`** - Organization management tests

## Execution Strategy

### Phase 1: Identify Current Failures
```bash
pytest tests/api/ --tb=line 2>&1 | head -100
```

Review output to understand failure patterns.

### Phase 2: Fix One File at a Time

For each file in priority order:

1. **Apply all 5 patterns systematically**:
   - Add UUID fixtures at top of file
   - Update org creation to come before user creation
   - Replace dict assertions with pytest.raises()
   - Fix API URL paths to include /v1/
   - Use authed_client instead of manual auth

2. **Run tests for that file**:
   ```bash
   pytest tests/api/test_agent_jobs_api.py -v
   ```

3. **Commit after file passes**:
   ```bash
   git add tests/api/test_agent_jobs_api.py
   git commit -m "fix(tests): Update agent_jobs_api tests for exception-based patterns"
   ```

4. **Move to next file**

### Phase 3: Full Validation

After all files are fixed:

```bash
# Run all API tests
pytest tests/api/ -v

# Run full test suite to check for regressions
pytest tests/ --tb=short

# Verify services tests still passing
pytest tests/services/ -v
```

## Success Criteria

- [ ] All API tests passing (0 failed, 0 errors)
- [ ] All pre-commit hooks passing
- [ ] No regressions in services tests (531 passed maintained)
- [ ] Consistent patterns applied across all test files

## Common Issues and Solutions

### Issue: IntegrityError on User Creation

**Symptom**: `NOT NULL constraint failed: users.org_id`

**Solution**: Create organization first, then user with org_id:
```python
org = Organization(id=str(uuid4()), ...)
session.add(org)
await session.flush()
user = User(id=str(uuid4()), org_id=org.id, ...)
```

### Issue: Duplicate Key Violations

**Symptom**: `UNIQUE constraint failed: users.username`

**Solution**: Use UUID-based unique suffixes:
```python
unique_id = str(uuid4())[:8]
username = f"testuser_{unique_id}"
```

### Issue: Multiple Results for Query

**Symptom**: `MultipleResultsFound: Expected one result, got 2`

**Solution**: Add `.limit(1)` to query:
```python
result = await session.execute(
    select(User).where(User.username == username).limit(1)
)
```

### Issue: AssertionError on result["success"]

**Symptom**: `KeyError: 'success'` or `TypeError: 'User' object is not subscriptable`

**Solution**: Replace dict assertions with exception-based:
```python
# OLD
result = await service.method()
assert result["success"] is False

# NEW
with pytest.raises(ValidationError):
    await service.method()
```

### Issue: NULL Check Failures

**Symptom**: Tests comparing `field == None` not working

**Solution**: Use SQLAlchemy `.is_(None)` method:
```python
# OLD
where(User.deleted_at == None)

# NEW
where(User.deleted_at.is_(None))
```

## Dependencies

- **0730d** (complete) - Services layer stable with all patterns validated
- **0424j** migration - User.org_id NOT NULL constraint enforced
- **0730b** - Exception-based service patterns implemented

## Deliverables

1. **All API test files updated** with 5 patterns applied
2. **Commits** with descriptive messages for each file fixed
3. **Update comms_log.json** with completion entry
4. **Update orchestrator_state.json** with 0730e completion

## Validation Checklist

Before marking complete:

- [ ] All API tests passing: `pytest tests/api/ -v`
- [ ] Services tests still passing: `pytest tests/services/ -v`
- [ ] Unit tests still passing: `pytest tests/unit/ -v`
- [ ] Integration tests still passing: `pytest tests/integration/ -v`
- [ ] Pre-commit hooks passing: `pre-commit run --all-files`
- [ ] Documentation updated if patterns changed

## Next Steps

After 0730e completion:
- Merge 0730 series to master
- Consider 0740 comprehensive audit (if requested by orchestrator)
- Archive 0730 series documentation
