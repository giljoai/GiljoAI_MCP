# Server Mode Testing - Quick Start Guide

**Purpose:** Validate GiljoAI MCP server mode deployment for network accessibility

**Status:** 🟢 Test infrastructure created, ready for execution

---

## What's Been Created

### 1. Strategy Documents
- ✅ **SERVER_MODE_TESTING_STRATEGY.md** - Complete testing strategy (comprehensive)
- ✅ **SERVER_MODE_TESTING_SUMMARY.md** - Executive summary (quick reference)

### 2. Test Files
- ✅ **test_network_connectivity.py** - Network accessibility tests
- ✅ **test_server_mode_auth.py** - API key authentication tests

### 3. Test Categories Covered

| Category | File | Status | Priority |
|----------|------|--------|----------|
| Network Connectivity | test_network_connectivity.py | ✅ Ready | CRITICAL |
| API Authentication | test_server_mode_auth.py | ✅ Ready | CRITICAL |
| Remote Workflows | ⏳ To be created | Week 2 | HIGH |
| Performance (Network) | ⏳ To be created | Week 2-3 | HIGH |
| Database Network | ⏳ To be created | Week 3 | MEDIUM |

---

## Quick Start - Running Server Mode Tests

### Step 1: Install Dependencies

```bash
# Core testing dependencies
pip install pytest pytest-asyncio httpx websockets

# Optional network utilities (recommended)
pip install netifaces psutil
```

### Step 2: Configure Server for Network Access

Edit `config.yaml`:

```yaml
installation:
  mode: server  # Enable server mode

services:
  api:
    host: 0.0.0.0  # Bind to all network interfaces (NOT localhost)
    port: 7272

  websocket:
    port: 6003

database:
  type: postgresql
  host: localhost
  port: 5432
  # ... other settings
```

### Step 3: Start the Server

```bash
# Start API server
python api/run_api.py

# Or use the startup script
./start_giljo.bat  # Windows
./start_giljo.sh   # Linux/Mac
```

### Step 4: Run Network Connectivity Tests

```bash
# Run all network connectivity tests
pytest tests/integration/test_network_connectivity.py -v

# Run specific test
pytest tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_api_accessible_from_localhost -v

# Run with detailed output
pytest tests/integration/test_network_connectivity.py -v -s
```

**Expected Output:**
```
tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_api_accessible_from_localhost PASSED
tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_api_accessible_from_lan_ip PASSED
tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_websocket_accessible_from_localhost PASSED
tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_websocket_accessible_from_lan_ip PASSED
tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_network_latency_measurements PASSED
tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_concurrent_api_requests PASSED
```

### Step 5: Run Authentication Tests

```bash
# Run all server mode auth tests
pytest tests/integration/test_server_mode_auth.py -v

# Run with marks
pytest tests/integration/test_server_mode_auth.py -m "server_mode" -v
```

**Note:** Some tests will be skipped if API keys are not configured. See "Configuring API Keys" section below.

---

## Test Results Interpretation

### ✅ PASSING - What It Means

```
test_api_accessible_from_localhost PASSED
```
**Meaning:** API server is running and accessible via localhost
**Action:** None - test passed

```
test_api_accessible_from_lan_ip PASSED
```
**Meaning:** API server is accessible via network interface (LAN IP)
**Action:** None - server mode networking is working correctly

### ⚠️ SKIPPED - What It Means

```
test_api_accessible_from_lan_ip SKIPPED (Could not determine LAN IP address)
```
**Meaning:** Network utility `netifaces` not installed
**Action:** Install with `pip install netifaces` OR manually configure LAN IP in test

```
test_api_key_required_for_protected_endpoints SKIPPED (Valid API key not configured)
```
**Meaning:** API keys not set up for testing
**Action:** See "Configuring API Keys" section below

### ❌ FAILED - What It Means

```
test_api_accessible_from_lan_ip FAILED
AssertionError: Cannot connect to API at 192.168.1.100:7272
```
**Meaning:** API server not accessible via network interface
**Possible Causes:**
1. Server not bound to `0.0.0.0` (check config.yaml)
2. Firewall blocking connections
3. Server not running
4. Wrong port configuration

**Action:** Verify server configuration:
```bash
# Check if API is listening on all interfaces
netstat -an | grep 7272  # Linux/Mac
netstat -an | findstr 7272  # Windows

# Should show: 0.0.0.0:7272 or *:7272
```

---

## Configuring API Keys for Testing

### Option 1: Use Environment Variables (Quick)

```bash
# Set test API key
export GILJO_TEST_API_KEY="your_generated_api_key_here"

# Run tests
pytest tests/integration/test_server_mode_auth.py -v
```

### Option 2: Update Fixtures (Recommended)

Edit `tests/integration/test_server_mode_auth.py`:

```python
@pytest.fixture
def valid_api_key(self):
    """Valid API key for testing"""
    # Replace with actual API key
    return "giljo_prod_abc123xyz789"  # Your real API key

@pytest.fixture
def read_only_api_key(self):
    """Read-only API key"""
    return "giljo_readonly_def456"  # Your real read-only key
```

### Option 3: Use Configuration File

Create `tests/server_mode_test_config.yml`:

```yaml
api_keys:
  full_access: "giljo_prod_abc123xyz789"
  read_only: "giljo_readonly_def456"
  tenant1: "giljo_tenant1_ghi789"
  tenant2: "giljo_tenant2_jkl012"
```

Update fixtures to load from file:

```python
@pytest.fixture
def valid_api_key(self):
    import yaml
    config = yaml.safe_load(open("tests/server_mode_test_config.yml"))
    return config["api_keys"]["full_access"]
```

---

## Common Issues and Solutions

### Issue 1: "API server not running on localhost"

**Symptom:**
```
SKIPPED (API server not running on localhost)
```

**Solution:**
```bash
# Start the API server
python api/run_api.py

# Verify it's running
curl http://localhost:7272/health
```

### Issue 2: "Cannot connect to API at LAN IP"

**Symptom:**
```
FAILED - Cannot connect to API at 192.168.1.100:7272
```

**Solution:**
Check server is bound to `0.0.0.0`:

```yaml
# config.yaml
services:
  api:
    host: 0.0.0.0  # NOT localhost or 127.0.0.1
    port: 7272
```

Restart server after config change.

### Issue 3: "WebSocket server not running"

**Symptom:**
```
SKIPPED (WebSocket server not running on localhost)
```

**Solution:**
Verify WebSocket server is enabled:

```yaml
# config.yaml
services:
  websocket:
    enabled: true  # Must be true
    port: 6003
```

### Issue 4: "PostgreSQL not accepting network connections"

**Symptom:**
```
FAILED - Cannot connect to database from remote client
```

**Solution:**
Configure PostgreSQL for network access:

```conf
# postgresql.conf
listen_addresses = '*'  # or specific IP
max_connections = 100

# pg_hba.conf
host    all    all    192.168.0.0/16    scram-sha-256
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql  # Linux
# or restart via Services on Windows
```

---

## Test Markers

Tests are organized with pytest markers:

```python
@pytest.mark.network       # Network connectivity tests
@pytest.mark.server_mode   # Server mode specific tests
@pytest.mark.security      # Security/authentication tests
@pytest.mark.slow          # Long-running tests (>30s)
```

### Run by Marker

```bash
# Run only network tests
pytest -m "network" -v

# Run only security tests
pytest -m "security" -v

# Run server mode tests (excludes localhost-only tests)
pytest -m "server_mode" -v

# Run fast tests only (exclude slow)
pytest -m "not slow" -v
```

---

## Next Steps

### Week 1: Foundation (Current)
✅ Network connectivity tests created
✅ API authentication tests created
⏳ Run tests in actual server mode environment
⏳ Document baseline metrics

### Week 2: Remote Workflows
- [ ] Create `test_remote_api_workflows.py`
- [ ] Test complete orchestration workflows from remote clients
- [ ] Validate project/agent/message operations over network

### Week 3: Performance
- [ ] Create `test_network_performance.py`
- [ ] Test 50+ concurrent remote clients
- [ ] Measure network latency impact
- [ ] Database connection pool testing

### Week 4: Advanced
- [ ] SSL/TLS certificate validation tests
- [ ] Load balancer integration tests
- [ ] CI/CD pipeline integration
- [ ] Production deployment validation

---

## Test Coverage Summary

### Current Coverage

| Category | Tests | Coverage |
|----------|-------|----------|
| Network Connectivity | 8 tests | ✅ Good |
| API Authentication | 8 tests | ✅ Good |
| Tenant Isolation | 1 test | ⚠️ Minimal |
| Performance | 0 tests | ❌ Missing |
| Database Network | 0 tests | ❌ Missing |

### Target Coverage (End of Week 4)

| Category | Target | Status |
|----------|--------|--------|
| Network Connectivity | 95% | 🟢 On Track |
| API Authentication | 100% | 🟢 On Track |
| Tenant Isolation | 90% | 🟡 In Progress |
| Performance | 85% | 🔴 Not Started |
| Database Network | 90% | 🔴 Not Started |

---

## Performance Benchmarks

### Network Latency Targets

| Metric | Target | Acceptable | Critical |
|--------|--------|-----------|----------|
| LAN API Latency | < 50ms | < 100ms | < 200ms |
| Remote API Response | < 200ms | < 500ms | < 1000ms |
| WebSocket Connection | < 2s | < 5s | < 10s |
| Concurrent Clients | 50+ | 30+ | 10+ |
| Success Rate | > 95% | > 90% | > 80% |

### How to Measure

```bash
# Run network latency test
pytest tests/integration/test_network_connectivity.py::TestNetworkConnectivity::test_network_latency_measurements -v -s

# Expected output:
# Network Latency Results:
#   Successful: 20/20
#   Min: 15.42ms
#   Max: 48.73ms
#   Avg: 28.65ms  ✓ < 50ms target
#   Median: 27.12ms
```

---

## Continuous Integration (Future)

### GitHub Actions Workflow (Planned)

```yaml
# .github/workflows/server_mode_tests.yml
name: Server Mode Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  server-mode-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run server mode tests
        run: |
          pytest tests/integration/test_network_connectivity.py -v
          pytest tests/integration/test_server_mode_auth.py -v
```

---

## Resources

### Documentation
- **Full Strategy:** `tests/SERVER_MODE_TESTING_STRATEGY.md`
- **Executive Summary:** `tests/SERVER_MODE_TESTING_SUMMARY.md`
- **Project Guide:** `CLAUDE.md`
- **Performance Tests:** `tests/performance/README.md`

### Test Files
- **Network Tests:** `tests/integration/test_network_connectivity.py`
- **Auth Tests:** `tests/integration/test_server_mode_auth.py`
- **Fixtures:** `tests/conftest.py`

### Example Commands

```bash
# Run all server mode tests
pytest tests/integration/test_network_connectivity.py tests/integration/test_server_mode_auth.py -v

# Run with coverage
pytest tests/integration/test_network_connectivity.py --cov=api --cov-report=html

# Run and generate report
pytest tests/integration/ -v --html=server_mode_report.html --self-contained-html
```

---

## Support and Troubleshooting

### Getting Help

1. **Check the logs:**
   ```bash
   # API server logs
   tail -f logs/api.log

   # Application logs
   tail -f logs/giljo_mcp.log
   ```

2. **Verify configuration:**
   ```bash
   # Check current config
   cat config.yaml

   # Verify server is listening
   netstat -tulpn | grep 7272  # Linux
   netstat -an | findstr 7272  # Windows
   ```

3. **Test manually:**
   ```bash
   # Test API endpoint
   curl http://localhost:7272/health

   # Test with API key
   curl -H "X-API-Key: your_key_here" http://localhost:7272/api/v1/projects/
   ```

### Reporting Issues

If tests fail consistently, report with:
- Test name and output
- Server configuration (config.yaml)
- Network environment (localhost vs LAN vs WAN)
- Error logs from API server
- System info (OS, Python version, network setup)

---

**Document Status:** ✅ Complete and ready for use
**Last Updated:** 2025-10-04
**Next Review:** After Week 1 test execution
