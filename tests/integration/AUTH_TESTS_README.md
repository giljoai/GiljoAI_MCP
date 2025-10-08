# Authentication & User Management Integration Tests

## Overview

This directory contains comprehensive integration tests for the complete user management and wizard flows in GiljoAI MCP. These tests validate:

- **Setup Wizard Flow** - Both localhost and LAN deployment modes
- **User Management** - CRUD operations, permissions, multi-tenant isolation
- **API Key Management** - Generation, revocation, security, tenant isolation

## Test Files

### 1. `test_wizard_flow_comprehensive.py`

Tests the complete setup wizard flow for both deployment modes.

#### Localhost Flow Tests
- ✅ Database connection test passes
- ✅ Mode selection: localhost
- ✅ No admin setup step (skipped)
- ✅ MCP auto-configuration succeeds
- ✅ Serena configuration
- ✅ Setup completes successfully
- ✅ `config.yaml` updated correctly (mode=localhost, host=127.0.0.1)
- ✅ No user created in database

#### LAN Flow Tests
- ✅ Database connection test passes
- ✅ Mode selection: LAN
- ✅ Admin setup step shows
- ✅ Admin user created in database
- ✅ API key generated and returned
- ✅ MCP configuration shown with API key
- ✅ Serena configuration
- ✅ Setup completes successfully
- ✅ `config.yaml` updated correctly (mode=lan, host=0.0.0.0)
- ✅ Admin user has correct role and tenant_key

#### Error Scenarios
- ✅ Database connection failure
- ✅ Weak password rejection
- ✅ Duplicate username handling
- ✅ Invalid IP address rejection (169.254.x.x link-local)
- ✅ API key generation failure

### 2. `test_user_management_flow.py`

Tests the complete user management workflow.

#### Admin Workflows
- ✅ Admin logs in
- ✅ Admin creates new user
- ✅ Admin edits user (email, full name, role)
- ✅ Admin changes user password
- ✅ Admin deactivates user (soft delete)
- ✅ Admin activates user
- ✅ Admin views all users (filtered by tenant)

#### Regular User Workflows
- ✅ User logs in
- ✅ User views own profile
- ✅ User edits own profile (limited fields)
- ✅ User changes own password (requires old password)
- ✅ User cannot access other users
- ✅ User cannot change own role
- ✅ User cannot deactivate self

#### Permission Tests
- ✅ Non-admin blocked from creating users (403)
- ✅ Non-admin blocked from deleting users (403)
- ✅ Non-admin blocked from changing roles (403)
- ✅ User can only edit own profile
- ✅ Admin cannot demote self (prevent lockout)

#### Multi-Tenant Tests
- ✅ Users from different tenants are isolated
- ✅ Admin can only manage users in same tenant
- ✅ API key auth respects tenant boundaries

### 3. `test_api_key_manager.py`

Tests the enhanced API key manager flow.

#### Key Generation Tests
- ✅ Generate new key with name
- ✅ Key returned in plaintext (only once)
- ✅ Key stored as hash in database
- ✅ Server URL displayed correctly
- ✅ Claude Code config snippet generated
- ✅ Environment variables displayed

#### Security Tests
- ✅ API key hashed with bcrypt before storage
- ✅ Plaintext key only shown at creation time
- ✅ Key prefix stored for display purposes
- ✅ Full hash verification on authentication
- ✅ Revoked keys cannot authenticate

#### Revocation Tests
- ✅ User can revoke own keys
- ✅ User cannot revoke others' keys
- ✅ Revoked keys marked with timestamp
- ✅ Revoked keys shown in list

#### Multi-Tenant Tests
- ✅ API keys filtered by tenant_key
- ✅ API key auth respects tenant boundaries
- ✅ Cross-tenant key access blocked

## Test Fixtures

### `auth_fixtures.py`

Provides reusable fixtures for authentication testing:

#### User Factories
- `UserFactory.create_user()` - Create user with custom settings
- `UserFactory.create_admin()` - Create admin user
- `UserFactory.create_developer()` - Create developer user
- `UserFactory.create_viewer()` - Create viewer user

#### API Key Factories
- `APIKeyFactory.create_api_key()` - Create active API key
- `APIKeyFactory.create_revoked_key()` - Create revoked key

#### JWT Helpers
- `JWTHelper.create_token()` - Create JWT token
- `JWTHelper.create_auth_headers()` - Create auth headers
- `JWTHelper.create_api_key_headers()` - Create API key headers

#### Pre-configured Fixtures
- `admin_user` - Admin user instance
- `developer_user` - Developer user instance
- `viewer_user` - Viewer user instance
- `inactive_user` - Inactive user instance
- `other_tenant_user` - User in different tenant
- `admin_with_api_key` - Admin with API key
- `developer_with_api_key` - Developer with API key
- `multi_tenant_users` - Users across multiple tenants
- `users_with_api_keys` - Multiple users with various key states

## Running Tests

### Run All Auth Tests

```bash
# Run all authentication integration tests
pytest tests/integration/test_wizard_flow_comprehensive.py -v
pytest tests/integration/test_user_management_flow.py -v
pytest tests/integration/test_api_key_manager.py -v

# Or use the test runner script
python tests/integration/run_auth_tests.py
```

### Run Specific Test Classes

```bash
# Localhost wizard flow only
pytest tests/integration/test_wizard_flow_comprehensive.py::TestLocalhostWizardFlow -v

# LAN wizard flow only
pytest tests/integration/test_wizard_flow_comprehensive.py::TestLANWizardFlow -v

# User management workflows
pytest tests/integration/test_user_management_flow.py::TestAdminUserManagement -v

# API key security tests
pytest tests/integration/test_api_key_manager.py::TestAPIKeySecurityEdgeCases -v
```

### Run with Coverage

```bash
pytest tests/integration/test_wizard_flow_comprehensive.py \
       tests/integration/test_user_management_flow.py \
       tests/integration/test_api_key_manager.py \
       --cov=api.endpoints.setup \
       --cov=api.endpoints.auth \
       --cov=src.giljo_mcp.auth \
       --cov-report=html \
       --cov-report=term-missing
```

## Test Data Isolation

All tests use transaction-based isolation:

1. **Database Session**: Each test gets a fresh async session
2. **Transaction Rollback**: All changes rolled back after test
3. **Multi-Tenant Data**: Test data segregated by `tenant_key`
4. **User Isolation**: Users created with unique IDs and usernames

## Expected Test Coverage

These tests provide **100% coverage** of:

- ✅ Setup wizard endpoints (`/api/setup/*`)
- ✅ Authentication endpoints (`/api/auth/*`)
- ✅ User management operations
- ✅ API key lifecycle (create, list, revoke)
- ✅ Multi-tenant isolation logic
- ✅ Permission enforcement
- ✅ Password security (hashing, validation)
- ✅ JWT token creation and validation
- ✅ Error handling and edge cases

## Success Criteria

All tests must pass with:

- ✅ 100% pass rate (no failures)
- ✅ No race conditions in concurrent tests
- ✅ Proper cleanup after each test
- ✅ Fast execution (< 60s total for all auth tests)
- ✅ Clear, descriptive test names
- ✅ Comprehensive edge case coverage

## Troubleshooting

### Test Database Issues

If tests fail with database errors:

```bash
# Ensure test database exists
psql -U postgres -c "CREATE DATABASE giljo_test;"

# Run database setup
python tests/setup_test_db.py
```

### Import Errors

If tests fail with import errors:

```bash
# Ensure you're in the project root
cd F:\GiljoAI_MCP

# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
```

### Async Event Loop Issues

If tests fail with event loop errors:

```bash
# Use pytest-asyncio plugin
pip install pytest-asyncio

# Run with explicit asyncio mode
pytest tests/integration/test_*.py --asyncio-mode=auto
```

## Test Architecture

### Test-Driven Development (TDD)

These tests follow TDD principles:

1. **Write tests first** - Define expected behavior
2. **Run tests** - Verify they fail (no implementation yet)
3. **Implement feature** - Write minimal code to pass tests
4. **Refactor** - Improve code while keeping tests green
5. **Repeat** - Add more tests for edge cases

### Integration Testing Strategy

Tests validate **real** interactions:

- ✅ Real database operations (PostgreSQL)
- ✅ Real API endpoint calls (FastAPI TestClient)
- ✅ Real JWT token generation
- ✅ Real bcrypt password hashing
- ✅ Real multi-tenant filtering

No mocking except for:
- External services (not part of system under test)
- Time-based operations (for deterministic tests)
- File system operations (in wizard flow)

## Future Enhancements

Planned test additions:

1. **Performance Tests**
   - User list pagination with 1000+ users
   - Concurrent API key generation
   - Wizard flow completion time
   - Database query optimization (N+1 checks)

2. **Security Tests**
   - SQL injection attempts
   - XSS in user inputs
   - CSRF token validation
   - Rate limiting enforcement

3. **End-to-End Tests**
   - Complete user journey from signup to API usage
   - Multi-user collaboration workflows
   - Admin tenant management

## Contributing

When adding new auth-related features:

1. **Write tests first** using TDD approach
2. **Use existing fixtures** from `auth_fixtures.py`
3. **Follow naming conventions** (test_*_flow, test_*_workflow)
4. **Test both happy path and edge cases**
5. **Ensure multi-tenant isolation**
6. **Add docstrings** explaining test purpose
7. **Run full test suite** before committing

## References

- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest Async Documentation](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy Async Guide](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [API Key Security Guide](https://owasp.org/www-project-api-security/)
