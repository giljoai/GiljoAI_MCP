# GiljoAI MCP Baseline Performance Benchmarks (Handover 0129b)

**Created**: 2025-11-12
**Handover**: 0129b - Performance Benchmarks
**Purpose**: Establish baseline performance metrics for regression testing

---

## Overview

This suite creates **baseline performance metrics** for GiljoAI MCP to enable performance regression testing. It focuses on measuring individual operation timing rather than load/stress testing.

**Key Difference from Load Tests:**
- **Baseline Benchmarks (0129b)**: Measure single-operation latency for regression testing
- **Load/Stress Tests (0129d)**: Test 100+ concurrent operations and system limits

---

## Files Created

### Benchmark Test Files

1. **`test_database_performance.py`** (~300 lines)
   - Simple SELECT queries
   - Complex JOIN queries
   - INSERT/UPDATE operations
   - Multi-operation transactions
   - Connection pool timing

2. **`test_api_performance.py`** (~300 lines)
   - GET (single resource)
   - GET (list of resources)
   - POST/PUT (create/update)
   - DELETE operations
   - Complex endpoint operations

3. **`test_websocket_performance.py`** (~250 lines)
   - Connection establishment
   - Message round-trip latency (ping-pong)
   - One-way message send
   - Channel subscription
   - Broadcast to multiple clients

### Report Generator

4. **`benchmark_report_generator.py`** (~400 lines)
   - Runs all benchmarks
   - Generates reports in multiple formats
   - Creates baseline documentation

---

## Target Performance Metrics

### Database Operations

| Operation | Target | Acceptable | Warning |
|-----------|--------|------------|---------|
| Simple SELECT | <10ms | <20ms | >20ms |
| Complex JOIN | <50ms | <100ms | >100ms |
| INSERT/UPDATE | <20ms | <50ms | >50ms |
| Transaction | <30ms | <75ms | >75ms |
| Connection Pool | <5ms | <10ms | >10ms |

### API Endpoints

| Endpoint Type | Target | Acceptable | Warning |
|---------------|--------|------------|---------|
| GET (single) | <50ms | <100ms | >100ms |
| GET (list) | <100ms | <200ms | >200ms |
| POST/PUT | <100ms | <200ms | >200ms |
| DELETE | <50ms | <100ms | >100ms |
| Complex operations | <200ms | <500ms | >500ms |

### WebSocket Operations

| Operation | Target | Acceptable | Warning |
|-----------|--------|------------|---------|
| Message latency | <50ms | <100ms | >100ms |
| Connection setup | <100ms | <200ms | >200ms |
| Broadcast (10 clients) | <100ms | <200ms | >200ms |
| Broadcast (50 clients) | <500ms | <1000ms | >1000ms |

---

## Usage

### Prerequisites

1. **PostgreSQL Running**
   ```bash
   # Verify PostgreSQL is running
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT 1;"
   ```

2. **Application Server Running**
   ```bash
   # Start the application server
   python startup.py
   ```

3. **Dependencies Installed**
   ```bash
   pip install pytest pytest-asyncio httpx websockets psutil
   ```

### Run Individual Benchmark Suites

```bash
# Database benchmarks (no server needed, just PostgreSQL)
pytest tests/performance/test_database_performance.py -v -s

# API benchmarks (requires running server)
pytest tests/performance/test_api_performance.py -v -s

# WebSocket benchmarks (requires running server with WebSocket support)
pytest tests/performance/test_websocket_performance.py -v -s
```

### Run All Benchmarks and Generate Report

```bash
# Generate Markdown report (default)
python tests/performance/benchmark_report_generator.py

# Generate JSON report
python tests/performance/benchmark_report_generator.py --format json --output baseline.json

# Generate HTML report
python tests/performance/benchmark_report_generator.py --format html --output baseline.html

# Skip tests, just generate template report
python tests/performance/benchmark_report_generator.py --skip-tests
```

### Output Locations

- **Markdown**: `docs/performance_baseline.md` (default)
- **JSON**: `performance_baseline.json`
- **HTML**: `performance_baseline.html`

---

## Interpreting Results

### Status Indicators

- ✅ **PASS**: Mean latency < Target
- ⚠️ **WARNING**: Mean latency between Target and Acceptable
- ❌ **FAIL**: Mean latency > Acceptable

### Key Metrics Explained

- **Mean**: Average latency across all iterations
- **Median**: Middle value (50th percentile)
- **P95**: 95th percentile (95% of requests faster than this)
- **P99**: 99th percentile (99% of requests faster than this)
- **Min/Max**: Best and worst case latencies

### Example Output

```
=== Database Performance Report ===

simple_select: ✅ PASS
  Mean:   8.45ms (target: <10ms)
  Median: 7.89ms
  P95:    12.34ms
  P99:    15.67ms
  Min:    5.23ms
  Max:    18.90ms
```

---

## Execution Notes

**This handover was completed remotely (code writing only):**

### Completed (Code Writing)
- Created all benchmark test files
- Wrote benchmark functions with statistics
- Implemented report generator
- Created documentation

### Remaining (Local Execution)
- Start PostgreSQL database
- Start application server
- Run benchmarks locally
- Generate actual performance data
- Review and commit baseline report

**Why?** Remote sessions lack access to PostgreSQL or the running application. Benchmarks must be executed in your local environment to generate meaningful metrics.

---

## Integration with 0129 Phase

This is **Handover 0129b** (one of four sub-tasks in the 0129 Integration Testing phase):

1. **0129a**: Fix Broken Test Suite (P0 - BLOCKER) - MUST MERGE FIRST
2. **0129b**: Performance Benchmarks (P1) - THIS HANDOVER ✅
3. **0129c**: Security & OWASP Testing (P1)
4. **0129d**: Load Testing Configuration (P2)

### Merge Order

1. Merge 0129a FIRST (test suite must work)
2. Merge 0129b, 0129c, 0129d in ANY order
3. Test locally after each merge

---

## Local Testing Workflow

After merging this branch:

```bash
# 1. Merge branch
git checkout main
git merge /claude-project-0129b

# 2. Verify PostgreSQL is running
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT 1;"

# 3. Start application server
python startup.py

# 4. In another terminal, run benchmarks
pytest tests/performance/test_database_performance.py -v -s
pytest tests/performance/test_api_performance.py -v -s
pytest tests/performance/test_websocket_performance.py -v -s

# 5. Generate comprehensive report
python tests/performance/benchmark_report_generator.py

# 6. Review baseline report
cat docs/performance_baseline.md

# 7. Commit baseline report
git add docs/performance_baseline.md
git commit -m "Add performance baseline report from 0129b"
```

---

## Expected Baseline Results

Based on typical FastAPI/PostgreSQL performance on standard hardware:

### Database
- Simple SELECT: 5-15ms ✅
- Complex JOIN: 20-80ms ✅
- INSERT/UPDATE: 10-30ms ✅
- Transaction: 15-50ms ✅

### API
- GET single: 30-80ms ✅
- GET list: 50-150ms ✅
- POST/PUT: 50-150ms ✅
- Complex: 100-300ms ✅

### WebSocket
- Message latency: 20-60ms ✅
- Connection: 50-150ms ✅
- Broadcast (10): 50-150ms ✅

**Note**: Your actual results will vary based on:
- Hardware (CPU, RAM, SSD vs HDD)
- Database configuration
- System load
- Network latency (if remote database)

---

## Performance Regression Testing

### Establishing Baseline

1. **First Run**: Run benchmarks on clean system
2. **Save Baseline**: Save JSON output for comparison
3. **Document**: Record hardware specs and configuration

```bash
# Save baseline
python tests/performance/benchmark_report_generator.py --format json --output baseline_v1.0.0.json
```

### Detecting Regressions

After code changes:

```bash
# Run new benchmarks
python tests/performance/benchmark_report_generator.py --format json --output baseline_v1.1.0.json

# Compare (manual review or use diff tools)
diff baseline_v1.0.0.json baseline_v1.1.0.json
```

### Acceptable Degradation

- **<5% slower**: Acceptable variation
- **5-15% slower**: Review changes, investigate
- **>15% slower**: Performance regression, must fix

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  performance:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: giljo_mcp
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx websockets

      - name: Start application
        run: |
          python startup.py &
          sleep 10  # Wait for server to start

      - name: Run performance benchmarks
        run: |
          python tests/performance/benchmark_report_generator.py --format json

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: performance_baseline.json
```

---

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -l

# Check database exists
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"
```

### Application Server Issues

```bash
# Check if server is running
curl http://localhost:8000/health

# Check logs
python startup.py  # Should show startup logs
```

### WebSocket Connection Issues

```bash
# Test WebSocket endpoint
# (requires wscat or similar tool)
wscat -c ws://localhost:8000/ws
```

### Slow Performance

If benchmarks are slower than expected:

1. **Check system load**: `top` or Task Manager
2. **Check disk I/O**: Slow disk can impact database performance
3. **Check PostgreSQL settings**: Connection pool size, shared_buffers
4. **Close other applications**: Ensure system has resources available

---

## Next Steps After Baseline Established

1. **Document Hardware Specs**: Add to performance_baseline.md
2. **Set Up Monitoring**: Use baseline for production alerts
3. **Regular Testing**: Run benchmarks monthly or after major changes
4. **Optimize**: Address any metrics exceeding targets
5. **Update Targets**: Adjust targets based on production requirements

---

## Related Handovers

- **0129**: Parent handover (Integration Testing & Performance)
- **0129a**: Fix Broken Test Suite (prerequisite)
- **0129c**: Security & OWASP Testing (parallel)
- **0129d**: Load Testing Configuration (builds on this)

---

## Questions?

- Review `handovers/0129b_performance_benchmarks.md` for detailed specification
- Check `handovers/0129_integration_testing_performance.md` for context
- See existing `tests/performance/README.md` for load/stress testing

---

**Status**: Code Complete, Pending Local Execution
**Next Action**: Merge branch and run benchmarks locally
**Expected Duration**: 30-60 minutes to run all benchmarks locally
