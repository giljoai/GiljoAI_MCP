# One-Time Download Token System - Test Design Document

**Author**: Backend Integration Tester Agent
**Date**: 2025-11-04
**Status**: TDD - Tests Written Before Implementation
**Architecture**: Multi-tenant, secure, one-time use token system

---

## Executive Summary

This document outlines a comprehensive test-driven development (TDD) approach for implementing a one-time download token system for GiljoAI MCP. The system addresses security, multi-tenant isolation, and user experience concerns while maintaining the 97% token efficiency gains achieved in Handover 0094.

**Test Coverage**: 89 tests across 8 test classes
**Coverage Goal**: 95%+ with focus on critical security paths
**Multi-Tenant Isolation**: Zero cross-tenant leakage (CRITICAL)

---

## Architecture Overview

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Download Token System                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ TokenManager │───▶│ FileStaging  │───▶│   Download   │  │
│  │              │    │              │    │   Endpoint   │  │
│  │ - Generate   │    │ - Create ZIP │    │ - Validate   │  │
│  │ - Validate   │    │ - Stage files│    │ - Serve file │  │
│  │ - Mark used  │    │ - Metadata   │    │ - Cleanup    │  │
│  │ - Cleanup    │    │ - Cleanup    │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         └────────────────────┴────────────────────┘          │
│                              │                                │
│                    ┌─────────▼─────────┐                     │
│                    │   PostgreSQL      │                     │
│                    │  download_tokens  │                     │
│                    └───────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
CREATE TABLE download_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token UUID NOT NULL UNIQUE,
    tenant_key VARCHAR(255) NOT NULL,
    download_type VARCHAR(50) NOT NULL,  -- 'slash_commands' | 'agent_templates'
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    downloaded_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,

    -- Multi-tenant isolation (CRITICAL)
    INDEX idx_tenant_token (tenant_key, token),
    INDEX idx_expires_at (expires_at) WHERE is_used = FALSE
);
```

### File Staging Structure

```
temp/
├── {tenant_key_1}/
│   ├── {token_1}/
│   │   ├── download.zip
│   │   └── metadata.json
│   └── {token_2}/
│       ├── download.zip
│       └── metadata.json
└── {tenant_key_2}/
    └── {token_3}/
        ├── download.zip
        └── metadata.json
```

---

## Test Suite Structure

### 1. Unit Tests: TokenManager (17 tests)

**Responsibility**: Token lifecycle management

| Test Name | Purpose | Priority |
|-----------|---------|----------|
| `test_generate_token_creates_unique_uuid` | Verify UUID uniqueness | HIGH |
| `test_generate_token_stores_metadata` | Database persistence | HIGH |
| `test_validate_token_success` | Valid token passes | HIGH |
| `test_validate_token_not_found` | Non-existent token fails | HIGH |
| `test_validate_token_expired` | Expired token fails | CRITICAL |
| `test_validate_token_already_used` | One-time use enforcement | CRITICAL |
| `test_validate_token_cross_tenant_access_denied` | Multi-tenant isolation | CRITICAL |
| `test_mark_as_used_updates_database` | Usage tracking | HIGH |
| `test_cleanup_expired_tokens` | Background cleanup | MEDIUM |
| `test_concurrent_token_generation_thread_safe` | Race condition prevention | HIGH |
| `test_concurrent_downloads_one_token_fails` | Concurrent access control | CRITICAL |

**Critical Security Tests** (CRITICAL priority):
- Cross-tenant access prevention
- One-time use enforcement
- Expiration validation

### 2. Unit Tests: FileStaging (6 tests)

**Responsibility**: File preparation and cleanup

| Test Name | Purpose | Priority |
|-----------|---------|----------|
| `test_create_staging_directory_structure` | Directory creation | HIGH |
| `test_stage_slash_commands_creates_zip` | Slash command ZIP generation | HIGH |
| `test_stage_agent_templates_creates_zip` | Agent template ZIP generation | HIGH |
| `test_save_metadata_creates_json` | Metadata persistence | MEDIUM |
| `test_cleanup_removes_staging_directory` | Cleanup verification | HIGH |
| `test_directory_traversal_prevention` | Security: Path traversal | CRITICAL |

**Security Focus**:
- Directory traversal attack prevention
- File permission verification
- Cleanup completeness

### 3. Integration Tests: Download Endpoints (8 tests)

**Responsibility**: Full HTTP download flow

| Test Name | Purpose | Priority |
|-----------|---------|----------|
| `test_generate_token_endpoint_success` | Token generation API | HIGH |
| `test_download_with_valid_token_success` | Successful download | HIGH |
| `test_download_with_expired_token_fails` | Expiration enforcement | CRITICAL |
| `test_download_with_used_token_fails` | One-time use enforcement | CRITICAL |
| `test_download_with_invalid_token_fails` | Error handling | HIGH |
| `test_download_cross_tenant_access_denied` | Multi-tenant isolation | CRITICAL |
| `test_download_cleanup_after_success` | Post-download cleanup | HIGH |

**Multi-Tenant Isolation** (CRITICAL):
- Token validation respects tenant_key
- Download endpoint checks tenant ownership
- No cross-tenant token access

### 4. Integration Tests: MCP Tool Integration (4 tests)

**Responsibility**: MCP tool → token → download flow

| Test Name | Purpose | Priority |
|-----------|---------|----------|
| `test_setup_slash_commands_returns_download_url` | Slash command tool | HIGH |
| `test_gil_import_personalagents_returns_download_url` | Personal agents tool | HIGH |
| `test_gil_import_productagents_returns_download_url` | Product agents tool | HIGH |
| `test_token_expires_after_tool_invocation` | Expiration timing | MEDIUM |

**Tool Integration**:
- Tools return download URLs (not file content)
- URLs contain valid tokens
- Tokens work immediately after generation

### 5. End-to-End Tests (3 tests)

**Responsibility**: Complete user workflows

| Test Name | Purpose | Priority |
|-----------|---------|----------|
| `test_ui_button_download_flow` | UI-triggered download | HIGH |
| `test_mcp_slash_command_download_flow` | MCP-triggered download | HIGH |
| `test_concurrent_downloads_different_tenants` | Multi-tenant concurrency | CRITICAL |

**User Scenarios**:
1. User clicks "Download Slash Commands" button
2. User executes `/gil_import_personalagents` command
3. Multiple tenants download simultaneously

### 6. Edge Cases & Error Handling (6 tests)

**Responsibility**: Robustness and error recovery

| Test Name | Purpose | Priority |
|-----------|---------|----------|
| `test_malformed_token_uuid` | Invalid token format | MEDIUM |
| `test_token_generation_database_error` | Database failure handling | HIGH |
| `test_file_staging_disk_full_error` | Disk space handling | MEDIUM |
| `test_cleanup_handles_missing_directory` | Cleanup resilience | LOW |
| `test_rate_limiting_token_generation` | Abuse prevention | MEDIUM |

**Error Scenarios**:
- Malformed tokens
- Database unavailability
- Disk full conditions
- Network timeouts

### 7. Performance Tests (3 tests)

**Responsibility**: System performance benchmarks

| Test Name | Benchmark | Target |
|-----------|-----------|--------|
| `test_token_generation_latency` | Token creation time | <50ms |
| `test_concurrent_token_validation_throughput` | Validation rate | >1000 req/s |
| `test_cleanup_performance` | Cleanup speed | 1000 tokens <1s |

**Performance Goals**:
- Token generation: <50ms (p95)
- Download latency: <200ms (small files)
- Cleanup: 1000 tokens/second

---

## Edge Cases & Security Considerations

### Security Critical (Zero Tolerance)

1. **Multi-Tenant Isolation**
   - **Risk**: Tenant A accesses Tenant B's download token
   - **Prevention**: Token validation ALWAYS checks `tenant_key`
   - **Test Coverage**: 5 tests across multiple layers
   - **Database Constraint**: Partial index on `(tenant_key, token)`

2. **One-Time Use Enforcement**
   - **Risk**: Token reuse after download
   - **Prevention**: Atomic `is_used` flag update
   - **Test Coverage**: Race condition tests with concurrent access
   - **Database**: Transaction-level locking on token update

3. **Token Expiration**
   - **Risk**: Expired token still works
   - **Prevention**: `expires_at` check before serving file
   - **Test Coverage**: Time-based validation tests
   - **Default**: 15 minutes from generation

4. **Directory Traversal**
   - **Risk**: Malicious `tenant_key` or `token` escapes temp directory
   - **Prevention**: Path validation with `Path.resolve()` checks
   - **Test Coverage**: Attack simulation tests
   - **Validation**: Reject `../`, absolute paths, special chars

### High Priority Edge Cases

5. **Concurrent Downloads (Same Token)**
   - **Scenario**: User double-clicks download link
   - **Expected**: First request succeeds, second fails (410 Gone)
   - **Test**: `test_concurrent_downloads_one_token_fails`

6. **Database Transaction Failures**
   - **Scenario**: Database crashes during token generation
   - **Expected**: HTTP 500, no orphaned staging files
   - **Test**: Mock database errors, verify cleanup

7. **Disk Full Errors**
   - **Scenario**: No space left when creating ZIP
   - **Expected**: HTTP 507, graceful error message
   - **Test**: Mock `OSError`, verify response

8. **Orphaned Files (Cleanup Failures)**
   - **Scenario**: Download succeeds but cleanup fails
   - **Expected**: Background job cleans up eventually
   - **Prevention**: Separate cleanup task, retry logic

### Medium Priority Edge Cases

9. **Malformed Tokens**
   - **Examples**: `"not-a-uuid"`, `""`, `null`, `"<script>alert(1)</script>"`
   - **Expected**: HTTP 400 Bad Request
   - **Test**: Input validation tests

10. **Empty Template Lists**
    - **Scenario**: User has no active templates
    - **Expected**: Return empty ZIP or 404 with clear message
    - **Test**: Template query tests

11. **Network Timeouts During Download**
    - **Scenario**: Client disconnects mid-download
    - **Expected**: Token remains valid (not marked as used)
    - **Test**: Connection interrupt simulation

12. **Rate Limiting**
    - **Scenario**: User generates 100 tokens in 1 minute
    - **Expected**: HTTP 429 after threshold (e.g., 20/min)
    - **Test**: Rapid token generation test

### Low Priority Edge Cases

13. **Very Large ZIP Files**
    - **Scenario**: User has 1000 agent templates
    - **Expected**: Streaming download, no memory overflow
    - **Test**: Large file stress test

14. **Unicode Filenames**
    - **Scenario**: Template names contain emoji, Chinese characters
    - **Expected**: ZIP handles UTF-8 correctly
    - **Test**: Unicode content tests

15. **Clock Skew**
    - **Scenario**: Server time changes during token lifetime
    - **Expected**: Use consistent timezone (UTC)
    - **Test**: Timezone validation tests

---

## Test Implementation Plan

### Phase 1: Core Functionality (Week 1)

**Focus**: Token generation and validation

1. Implement `TokenManager` class
2. Write 11 core unit tests (pass/fail/isolation)
3. Create database migration for `download_tokens` table
4. Run tests (all should fail initially - TDD)
5. Implement TokenManager to pass tests

**Deliverables**:
- `src/giljo_mcp/download_tokens.py`
- `tests/test_download_tokens.py` (TokenManager tests passing)
- Database migration `002_download_tokens.sql`

### Phase 2: File Staging (Week 1)

**Focus**: ZIP generation and cleanup

1. Implement `FileStaging` class
2. Write 6 file staging unit tests
3. Implement staging logic
4. Verify cleanup correctness

**Deliverables**:
- `src/giljo_mcp/file_staging.py`
- Tests passing for ZIP creation and cleanup

### Phase 3: API Endpoints (Week 2)

**Focus**: HTTP download flow

1. Create endpoints:
   - `POST /api/download/generate-token`
   - `GET /api/download/file/{token}`
2. Write 8 integration tests
3. Implement endpoints with validation
4. Test multi-tenant isolation thoroughly

**Deliverables**:
- `api/endpoints/downloads.py` (updated with token endpoints)
- Integration tests passing
- API documentation updated

### Phase 4: MCP Tool Integration (Week 2)

**Focus**: Tool → token flow

1. Update MCP tools to return download URLs:
   - `setup_slash_commands()`
   - `gil_import_personalagents()`
   - `gil_import_productagents()`
2. Write 4 integration tests
3. Verify tool responses include valid tokens

**Deliverables**:
- `src/giljo_mcp/tools/tool_accessor.py` (updated)
- MCP tool tests passing

### Phase 5: End-to-End & Performance (Week 3)

**Focus**: Complete workflows and optimization

1. Write 3 end-to-end tests
2. Write 6 edge case tests
3. Write 3 performance tests
4. Optimize based on benchmark results
5. Security audit (penetration testing)

**Deliverables**:
- All 89 tests passing
- Performance benchmarks met
- Security review completed

---

## Fixtures & Test Utilities

### Core Fixtures

```python
@pytest_asyncio.fixture
async def db_session():
    """Transactional database session (rollback after test)"""
    # Provided by base_fixtures.py
    pass

@pytest_asyncio.fixture
async def test_user(db_session):
    """Test user with tenant key"""
    user = User(
        id=str(uuid.uuid4()),
        username="testuser",
        email="test@example.com",
        tenant_key=TokenTestData.generate_tenant_key(),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Authentication headers for API requests"""
    # Generate JWT token for test user
    token = create_access_token(test_user.id, test_user.tenant_key)
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def api_client(db_session):
    """Async HTTP client for API testing"""
    from httpx import AsyncClient
    from api.app import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Test Data Generators

```python
class TokenTestData:
    """Reusable test data generation"""

    @staticmethod
    def generate_tenant_key() -> str:
        return f"tk_test_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def generate_token() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def generate_download_metadata(...) -> dict:
        # See implementation in test file
        pass
```

---

## Running Tests

### Run All Download Token Tests

```bash
# Run entire test suite
pytest tests/test_download_tokens.py -v

# Run specific test class
pytest tests/test_download_tokens.py::TestTokenManager -v

# Run with coverage
pytest tests/test_download_tokens.py --cov=src/giljo_mcp/download_tokens --cov-report=html

# Run only critical security tests
pytest tests/test_download_tokens.py -k "cross_tenant or one_time or expired" -v

# Run performance tests (slow)
pytest tests/test_download_tokens.py -m slow -v
```

### Test Markers

```python
@pytest.mark.asyncio         # Async test (required for all async functions)
@pytest.mark.slow            # Performance tests (skip in CI fast mode)
@pytest.mark.integration     # Integration tests (require full stack)
@pytest.mark.security        # Security-critical tests (run on every commit)
```

---

## Success Criteria

### Coverage Metrics

- **Line Coverage**: ≥95% for `download_tokens.py` and `file_staging.py`
- **Branch Coverage**: ≥90% (especially error handling branches)
- **Critical Path Coverage**: 100% (multi-tenant isolation, one-time use)

### Security Validation

- ✅ Zero cross-tenant token access (0 failures in 1000 tests)
- ✅ One-time use enforced (100% success rate)
- ✅ Token expiration respected (no stale token usage)
- ✅ Directory traversal attacks blocked (100% rejection)

### Performance Benchmarks

- ✅ Token generation: <50ms (p95)
- ✅ Token validation: >1000 req/s
- ✅ Download latency: <200ms (1MB file, local)
- ✅ Cleanup: 1000 tokens in <1s

### User Experience

- ✅ Clear error messages for all failure modes
- ✅ Download URLs work immediately after generation
- ✅ No manual cleanup required (automatic)
- ✅ Files cleaned up after successful download

---

## Migration from Current Implementation

### Current State (Handover 0094)

- ✅ Direct download endpoints (no tokens)
- ✅ Public `/api/download/slash-commands.zip`
- ✅ Optional-auth `/api/download/agent-templates.zip`
- ✅ 97% token efficiency gains

### Migration Strategy

**Phase 1: Backward Compatibility**
- Keep existing direct download endpoints
- Add new token-based endpoints in parallel
- Update MCP tools to use tokens (opt-in)

**Phase 2: Gradual Rollout**
- UI buttons use token system (better UX)
- MCP tools switch to tokens (security)
- Monitor usage and performance

**Phase 3: Deprecation**
- Mark direct endpoints as deprecated
- Remove in v4.0 (after 3 months notice)

**Benefits of Token System**:
- Better security (one-time use, expiration)
- Usage tracking (analytics)
- Multi-tenant isolation enforcement
- Cleaner audit trail

---

## Additional Documentation

### For Developers

- **API Spec**: `docs/api/download_tokens_api.md`
- **Security Audit**: `docs/security/download_token_security_review.md`
- **Performance Report**: `tests/performance/download_token_benchmarks.html`

### For Users

- **User Guide**: `docs/user_guides/downloading_files_guide.md`
- **Troubleshooting**: `docs/troubleshooting/download_errors.md`

---

## Handover Checklist

When implementation is complete, verify:

- [ ] All 89 tests passing
- [ ] Coverage ≥95% for core components
- [ ] Security audit completed (zero critical issues)
- [ ] Performance benchmarks met
- [ ] Database migration tested (up and down)
- [ ] API documentation updated
- [ ] User guide written
- [ ] Backward compatibility verified
- [ ] Monitoring/logging added
- [ ] Error handling comprehensive

---

## Questions for Product Owner

Before implementation, clarify:

1. **Token Expiration Time**: 15 minutes acceptable? Configurable?
2. **Rate Limiting**: How many tokens per user per minute?
3. **File Retention**: Clean up immediately or keep for audit (e.g., 24h)?
4. **Analytics**: Track download metrics (count, timing, user agent)?
5. **Backward Compatibility**: When to deprecate direct endpoints?

---

## Appendix: Test Execution Order

For TDD methodology, execute tests in this order:

1. **Unit Tests (TokenManager)** - Foundation
2. **Unit Tests (FileStaging)** - File operations
3. **Integration Tests (Endpoints)** - HTTP layer
4. **Integration Tests (MCP Tools)** - Tool integration
5. **End-to-End Tests** - Complete workflows
6. **Edge Cases** - Error handling
7. **Performance Tests** - Optimization

Each phase should have failing tests BEFORE implementation begins.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Next Review**: After Phase 1 completion
