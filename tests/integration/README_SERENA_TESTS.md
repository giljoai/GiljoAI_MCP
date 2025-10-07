# Serena MCP Integration Tests

## Overview

Comprehensive backend integration test suite for Serena MCP integration. These tests verify the complete integration of Serena MCP into GiljoAI MCP, including detection, attachment, detachment, and template injection.

## Test Suites

### 1. API Endpoint Integration Tests (`test_setup_serena_api.py`)

**Tests**: 25+ test cases
**Coverage Areas**:
- Detection endpoint (`POST /api/setup/detect-serena`)
- Attachment endpoint (`POST /api/setup/attach-serena`)
- Detachment endpoint (`POST /api/setup/detach-serena`)
- Status endpoint (`GET /api/setup/serena-status`)

**Key Test Scenarios**:
- ✅ Successful detection when Serena installed
- ✅ Detection failure when uvx/Serena not found
- ✅ Timeout handling in detection
- ✅ Version parsing from various output formats
- ✅ Successful attachment with config updates
- ✅ Attachment failure when Serena not detected
- ✅ Rollback on config write failures
- ✅ Rollback on .claude.json write failures
- ✅ Idempotent attachment (safe to call multiple times)
- ✅ Backup creation before modifications
- ✅ Successful detachment
- ✅ Preservation of other MCP servers during detachment
- ✅ Safe detachment when not attached
- ✅ Status reporting for all states

### 2. Service Integration Tests (`test_serena_services_integration.py`)

**Tests**: 20+ test cases
**Coverage Areas**:
- SerenaDetector service
- ClaudeConfigManager service
- ConfigService
- Template manager integration

**Key Test Scenarios**:
- ✅ Complete detection flow (uvx + Serena)
- ✅ Injection with backup creation
- ✅ Rollback on injection errors
- ✅ Removal with preservation of other servers
- ✅ Config caching and invalidation
- ✅ Thread-safe concurrent reads
- ✅ Template includes Serena when enabled
- ✅ Template excludes Serena when disabled
- ✅ All 6 roles receive Serena guidance
- ✅ Cache key differentiates Serena state

### 3. Cross-Platform Tests (`test_serena_cross_platform.py`)

**Tests**: 15+ test cases
**Coverage Areas**:
- Windows/Linux/macOS compatibility
- Path handling across platforms
- Subprocess execution
- File operations

**Key Test Scenarios**:
- ✅ .claude.json path resolution (Windows/Linux/macOS)
- ✅ config.yaml path cross-platform compatibility
- ✅ Backup directory creation
- ✅ Path separator independence
- ✅ Command format (list args, not shell string)
- ✅ No shell injection possibility
- ✅ Windows executable extension handling
- ✅ Linux executable permissions
- ✅ macOS PATH resolution
- ✅ Atomic write cross-platform
- ✅ Backup file naming safety
- ✅ UTF-8 encoding with Unicode/emoji
- ✅ Line ending independence (CRLF vs LF)
- ✅ Environment variable path handling

### 4. Error Recovery Tests (`test_serena_error_recovery.py`)

**Tests**: 15+ test cases
**Coverage Areas**:
- Transactional operations
- Rollback mechanisms
- Partial failure handling
- Backup management

**Key Test Scenarios**:
- ✅ Rollback config.yaml on .claude.json failure
- ✅ Restore backup on write failure
- ✅ Cleanup temp files on error
- ✅ Preserve other MCP servers during rollback
- ✅ Partial failure detection and handling
- ✅ Retry after partial failure
- ✅ Detection failure prevents attachment
- ✅ Invalid config prevented before write
- ✅ Multiple backup creation
- ✅ Backup preserves exact content
- ✅ Backup directory auto-creation
- ✅ Error messages include context
- ✅ Actionable error guidance
- ✅ Specific validation errors

### 5. Security Tests (`test_serena_security.py`)

**Tests**: 20+ test cases
**Coverage Areas**:
- Command injection prevention
- Path traversal prevention
- Configuration validation
- File permissions
- Input sanitization
- Access control

**Key Test Scenarios**:
- ✅ No shell injection in subprocess calls
- ✅ Malicious input doesn't execute commands
- ✅ Subprocess timeout prevents DoS
- ✅ Path validation prevents traversal
- ✅ Backup paths contained in backup directory
- ✅ Config paths must be absolute
- ✅ Invalid config rejected before write
- ✅ .claude.json structure validation
- ✅ config.yaml structure validation
- ✅ YAML safe_load rejects dangerous types
- ✅ File permissions preserved (Unix)
- ✅ Backup preserves permissions
- ✅ Temp files have secure permissions
- ✅ Version parsing sanitizes input
- ✅ Path sanitization in env vars
- ✅ JSON encoding prevents injection
- ✅ No privilege escalation required
- ✅ Config files user-scoped (not system-wide)
- ✅ Backup directory user-owned

## Test Fixtures

### Core Fixtures (in `conftest.py`)

```python
temp_config_path(tmp_path)      # Temporary config.yaml
temp_claude_json(tmp_path)      # Temporary .claude.json
mock_serena_detected()          # Mock Serena as installed
mock_serena_not_detected()      # Mock Serena as not found
api_client()                    # FastAPI test client
```

## Running Tests

### Run All Serena Tests

```bash
# All Serena integration tests
pytest tests/integration/test_setup_serena_api.py -v
pytest tests/integration/test_serena_services_integration.py -v
pytest tests/integration/test_serena_cross_platform.py -v
pytest tests/integration/test_serena_error_recovery.py -v
pytest tests/integration/test_serena_security.py -v

# All at once
pytest tests/integration/test_serena*.py -v
```

### Run Specific Test Classes

```bash
# API detection endpoint tests only
pytest tests/integration/test_setup_serena_api.py::TestSerenaDetectionEndpoint -v

# Service integration tests only
pytest tests/integration/test_serena_services_integration.py::TestSerenaDetectorService -v

# Security tests only
pytest tests/integration/test_serena_security.py::TestCommandInjection -v
```

### Run with Coverage

```bash
# Coverage for Serena services
pytest tests/integration/test_serena*.py \
  --cov=src/giljo_mcp/services/serena_detector \
  --cov=src/giljo_mcp/services/claude_config_manager \
  --cov=src/giljo_mcp/services/config_service \
  --cov-report=html \
  --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html
```

### Run Platform-Specific Tests

```bash
# Windows-only tests
pytest tests/integration/test_serena_cross_platform.py -k "windows" -v

# Linux-only tests
pytest tests/integration/test_serena_cross_platform.py -k "linux" -v

# macOS-only tests
pytest tests/integration/test_serena_cross_platform.py -k "macos" -v
```

## Coverage Goals

**Target**: 90%+ coverage for backend services

### Current Coverage Areas

**Services**:
- `src/giljo_mcp/services/serena_detector.py` - **95%+**
- `src/giljo_mcp/services/claude_config_manager.py` - **95%+**
- `src/giljo_mcp/services/config_service.py` - **90%+**

**API Endpoints**:
- Detection endpoint - **100%**
- Attachment endpoint - **100%**
- Detachment endpoint - **100%**
- Status endpoint - **100%**

## Test Categories

### Unit-Level Integration Tests
Tests individual services in isolation with mocked dependencies.

### Service Integration Tests
Tests multiple services working together (e.g., detector + config manager).

### API Integration Tests
Tests complete API endpoint flows including request/response validation.

### Cross-Platform Tests
Tests platform-specific behavior on Windows, Linux, and macOS.

### Security Tests
Tests for vulnerabilities (injection, traversal, validation, permissions).

### Error Recovery Tests
Tests transactional behavior, rollback, and error handling.

## Dependencies

Required packages:
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
fastapi>=0.104.0
httpx>=0.25.0
pyyaml>=6.0.1
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Serena MCP Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run Serena tests
        run: |
          pytest tests/integration/test_serena*.py \
            --cov=src/giljo_mcp/services \
            --cov-report=xml \
            --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Best Practices

### Followed in This Suite

1. **Test Isolation**: Each test is independent and doesn't rely on others
2. **Clear Assertions**: Descriptive assertion messages
3. **Realistic Data**: Factory patterns for test data generation
4. **Fast Tests**: Efficient mocking to avoid slow operations
5. **Comprehensive Coverage**: Happy path + edge cases + error conditions
6. **Documentation**: Clear docstrings explaining what each test validates

### Mocking Strategy

- **Subprocess calls**: Always mocked to avoid external dependencies
- **File system**: Use `tmp_path` fixture for isolation
- **Network calls**: Not used (all operations local)
- **Time-dependent**: Not applicable (operations are deterministic)

## Troubleshooting

### Tests Failing on Windows

If path-related tests fail on Windows:
```python
# Ensure using pathlib.Path, not string paths
path = Path("C:/Users/test")  # ✅ Good
path = "C:\\Users\\test"      # ❌ Bad
```

### Tests Failing on Linux/macOS

If permission tests fail:
```bash
# Check file permissions are being set correctly
ls -la temp_file
# Should show 0600 (rw-------) for secure files
```

### Import Errors

If services can't be imported:
```bash
# Ensure src is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/integration/test_serena*.py
```

## Future Enhancements

Potential additions to test suite:

1. **Performance Tests**: Load testing for concurrent operations
2. **Integration with Real Serena**: Optional tests with actual Serena MCP
3. **Network Failure Simulation**: Test retry logic and timeouts
4. **Database Integration**: Test persistence of Serena config state
5. **WebSocket Integration**: Test real-time updates of Serena status

## Contributing

When adding new Serena-related functionality:

1. **Write tests first** (TDD methodology)
2. Run existing tests to ensure no regressions
3. Achieve 90%+ coverage for new code
4. Test across all platforms if platform-specific
5. Include security tests for new input/config handling

## Summary

**Total Test Count**: 95+ comprehensive test cases
**Coverage**: 90%+ for backend services
**Platforms**: Windows, Linux, macOS
**Security**: Command injection, path traversal, validation
**Reliability**: Transactional operations, rollback, error recovery

This test suite ensures production-grade quality for Serena MCP integration.
