# Load Testing Guide for GiljoAI MCP

Comprehensive load testing framework using Locust to validate system capacity, identify bottlenecks, and establish performance baselines.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Load Test Scenarios](#load-test-scenarios)
- [Usage Examples](#usage-examples)
- [Interpreting Results](#interpreting-results)
- [Troubleshooting](#troubleshooting)
- [Tips & Best Practices](#tips--best-practices)

---

## Overview

This load testing framework provides:

- **5 comprehensive scenarios**: Normal load, peak load, stress test, spike test, soak test
- **Realistic user workflows**: Simulates actual user journeys through the application
- **WebSocket testing**: Tests concurrent WebSocket connection scaling
- **Automated reporting**: Generates HTML, CSV, and markdown reports
- **Capacity validation**: Identifies system limits and bottlenecks

**Framework Components:**

```
tests/load/
├── locustfile.py                      # Main load test configuration
├── scenarios/
│   ├── websocket_load.py              # WebSocket stress testing
│   └── user_workflows.py              # Realistic user journey tests
├── run_load_tests.py                  # Test orchestrator & report generator
├── results/                           # Generated reports (created on first run)
└── README.md                          # This file
```

---

## Prerequisites

### System Requirements

- **Python**: 3.11+
- **Locust**: Load testing framework
- **Running Application**: GiljoAI MCP server must be running
- **PostgreSQL**: Database must be accessible

### Installation

1. **Install Locust:**

```bash
pip install locust
```

2. **Verify Installation:**

```bash
locust --version
# Should output: locust 2.x.x
```

3. **Install WebSocket Support (for WebSocket tests):**

```bash
pip install websocket-client
```

---

## Quick Start

### Step 1: Start the Application

```bash
# Start GiljoAI MCP
python startup.py

# Verify it's running
curl http://localhost:7272/api/health
```

### Step 2: Run Quick Test (Verify Setup)

```bash
# Quick 1-minute test with 5 users
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 5 -r 1 -t 1m
```

If this succeeds, you're ready to run full load tests!

### Step 3: Run All Scenarios

```bash
# Run all 5 scenarios with automated reporting
python tests/load/run_load_tests.py --all
```

This will run:
1. Normal Load (10 users, 5 min)
2. Peak Load (50 users, 5 min)
3. Stress Test (100 users, 2 min)
4. Spike Test (0→100→0 rapid)
5. Soak Test (20 users, 30 min)

**Total Duration**: ~50 minutes

---

## Load Test Scenarios

### 1. Normal Load (10 users, 5 minutes)

**Purpose**: Validate typical daily usage

**Target Metrics**:
- RPS: 10-20 requests/second
- P95 Response Time: <100ms
- Failure Rate: <1%

**Run Command**:
```bash
python tests/load/run_load_tests.py --scenario normal_load
```

---

### 2. Peak Load (50 users, 5 minutes)

**Purpose**: Test peak hour capacity

**Target Metrics**:
- RPS: 50-100 requests/second
- P95 Response Time: <200ms
- Failure Rate: <2%

**Run Command**:
```bash
python tests/load/run_load_tests.py --scenario peak_load
```

---

### 3. Stress Test (100 users, 2 minutes)

**Purpose**: Push system to limits

**Target Metrics**:
- RPS: 100-200 requests/second
- P95 Response Time: <500ms
- Failure Rate: <5%

**Run Command**:
```bash
python tests/load/run_load_tests.py --scenario stress_test
```

---

### 4. Spike Test (0→100→0 rapid)

**Purpose**: Test rapid scaling behavior

**Target Metrics**:
- Connection establishment: <1000ms
- System recovery: Full within 30s
- No crashes or deadlocks

**Run Command**:
```bash
python tests/load/run_load_tests.py --scenario spike_test
```

---

### 5. Soak Test (20 users, 30 minutes)

**Purpose**: Detect memory leaks and resource exhaustion

**Target Metrics**:
- Memory growth: <10% over 30 minutes
- CPU usage: Stable
- No connection leaks

**Run Command**:
```bash
python tests/load/run_load_tests.py --scenario soak_test
```

---

## Usage Examples

### Interactive Web UI

Launch Locust web interface for manual testing:

```bash
# Start Locust web UI
locust -f tests/load/locustfile.py --host=http://localhost:7272

# Open browser to http://localhost:8089
# Enter user count and spawn rate
# Click "Start swarming"
```

### Headless (Automated) Testing

Run without web UI:

```bash
# Basic headless test
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 10 -r 2 -t 5m

# With HTML report
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 50 -r 10 -t 5m \
       --html results/report.html
```

### Tag-Based Testing

Run specific test groups:

```bash
# Run only normal_load tagged tests
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 10 -r 2 -t 5m --tags normal_load

# Run peak_load tests
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 50 -r 10 -t 5m --tags peak_load
```

### Custom Scenarios

Run with custom parameters:

```bash
# Custom user count and duration
python tests/load/run_load_tests.py --scenario stress_test \
       --users 75 --spawn-rate 15 --duration 10m

# Test against different host
python tests/load/run_load_tests.py --all \
       --host http://192.168.1.100:7272
```

### WebSocket Testing

Test WebSocket connections specifically:

```bash
# WebSocket load test
locust -f tests/load/scenarios/websocket_load.py \
       --host=http://localhost:7272 \
       --headless -u 50 -r 10 -t 5m
```

### User Workflow Testing

Test specific user journeys:

```bash
# User workflow scenarios
locust -f tests/load/scenarios/user_workflows.py \
       --host=http://localhost:7272 \
       --headless -u 20 -r 5 -t 10m
```

---

## Interpreting Results

### Key Metrics

#### 1. Requests Per Second (RPS)

**What it measures**: System throughput

**Good**:
- Normal Load: 10-20 RPS
- Peak Load: 50-100 RPS
- Stress Test: 100-200 RPS

**Warning Signs**:
- RPS dropping during test → System overloaded
- RPS much lower than expected → Bottleneck

#### 2. Response Time Percentiles

**What it measures**: Latency distribution

**Good**:
- P50 (median): <50ms
- P95: <200ms
- P99: <500ms

**Warning Signs**:
- P95 > 500ms → Slow operations
- P99 > 1000ms → Critical performance issues
- Growing over time → Memory leak or resource exhaustion

#### 3. Failure Rate

**What it measures**: Error percentage

**Good**:
- Normal Load: <1%
- Peak Load: <2%
- Stress Test: <5%

**Warning Signs**:
- >5% failures → System instability
- Growing over time → Resource exhaustion
- Sudden spike → System crash or deadlock

#### 4. Concurrent Users

**What it measures**: User capacity

**Good**: System handles target users with acceptable performance

**Warning Signs**:
- Failures at low user counts → Critical issues
- Performance degradation before target → Insufficient capacity

---

### HTML Report Sections

The generated HTML reports contain:

1. **Summary Statistics**
   - Total requests, failures, RPS
   - Response time distribution

2. **Charts**
   - Response time over time
   - Users over time
   - RPS over time

3. **Request Statistics**
   - Per-endpoint metrics
   - Success/failure counts
   - Response time percentiles

4. **Failure Details**
   - Error messages
   - Failure frequencies

---

### CSV Data Files

CSV files provide raw data for deeper analysis:

- `*_stats.csv`: Request statistics
- `*_stats_history.csv`: Time-series data
- `*_failures.csv`: Failure details
- `*_exceptions.csv`: Exception tracking

**Analysis Examples**:

```bash
# View top slowest endpoints
sort -t',' -k8 -rn results/stress_test_*_stats.csv | head -10

# Count total failures
wc -l results/stress_test_*_failures.csv
```

---

## Troubleshooting

### Connection Refused

**Symptom**: `Connection refused` errors

**Causes**:
- Application not running
- Wrong host/port
- Firewall blocking

**Solutions**:
```bash
# Verify application is running
curl http://localhost:7272/api/health

# Check if port is listening
netstat -an | grep 7272

# Test from load testing machine
curl http://<target-host>:7272/api/health
```

---

### High Failure Rate

**Symptom**: >5% request failures

**Causes**:
- Database connection pool exhausted
- Rate limiting triggered
- System overload

**Solutions**:
1. Check application logs: `tail -f logs/giljo_mcp.log`
2. Monitor database connections
3. Review rate limiting settings
4. Reduce concurrent users

---

### Slow Response Times

**Symptom**: P95 > 500ms, P99 > 1000ms

**Causes**:
- Slow database queries
- CPU bottleneck
- Memory pressure
- Network latency

**Solutions**:
1. Profile slow endpoints
2. Review database query performance
3. Monitor CPU and memory usage
4. Check network latency: `ping <target-host>`

---

### Locust Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'locust'`

**Solution**:
```bash
# Install Locust
pip install locust

# Verify installation
pip show locust
```

---

### WebSocket Connection Failures

**Symptom**: WebSocket tests fail

**Causes**:
- WebSocket endpoint not available
- Authentication issues
- Protocol mismatch (ws vs wss)

**Solutions**:
```bash
# Install websocket client
pip install websocket-client

# Test WebSocket manually
python -c "import websocket; ws = websocket.create_connection('ws://localhost:7272/ws'); print('Connected')"
```

---

## Tips & Best Practices

### 1. Warm-Up Period

**Why**: Cold start affects initial metrics

**How**: Run small test first
```bash
# Warm-up test (1 user, 1 minute)
locust -f tests/load/locustfile.py --host=http://localhost:7272 \
       --headless -u 1 -r 1 -t 1m
```

---

### 2. Monitor System Resources

**Tools**:
```bash
# Monitor CPU and memory
htop

# Monitor database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Monitor disk I/O
iostat -x 5
```

---

### 3. Cool Down Between Tests

**Why**: Allow system to recover

**How**: Wait 30-60 seconds between scenarios
```bash
# Automated cool down (done by run_load_tests.py)
# Manual cool down
sleep 30
```

---

### 4. Use Realistic Data

**Why**: Production-like data reveals real bottlenecks

**How**:
- Create test products/projects
- Use realistic data volumes
- Test with actual file sizes

---

### 5. Run on Isolated Environment

**Why**: Avoid interference from other processes

**Best**:
- Dedicated test server
- Similar specs to production
- Isolated network

**Avoid**:
- Development machine
- Shared resources
- Wi-Fi networks

---

### 6. Baseline Before Optimizing

**Process**:
1. Run load tests (establish baseline)
2. Document current performance
3. Make optimization
4. Run load tests again
5. Compare to baseline

---

### 7. Document Hardware Specs

**Include**:
- CPU cores and speed
- RAM available
- Disk type (SSD/HDD)
- Network bandwidth

**Why**: Results are hardware-dependent

---

### 8. Incremental Load Testing

**Start Small**:
```bash
# 5 users
locust --headless -u 5 -r 1 -t 2m ...

# 10 users (if 5 succeeds)
locust --headless -u 10 -r 2 -t 2m ...

# 25 users (if 10 succeeds)
locust --headless -u 25 -r 5 -t 2m ...
```

**Why**: Find breaking point gradually

---

## Results Location

All test results are saved in `tests/load/results/`:

```
tests/load/results/
├── normal_load_20251111_143022.html       # Visual report
├── normal_load_20251111_143022.json       # Test metadata
├── normal_load_20251111_143022_stats.csv  # Statistics
├── normal_load_20251111_143022.log        # Locust logs
├── summary_20251111_145530.md             # Aggregate summary
└── ...
```

---

## Next Steps After Load Testing

### 1. Capacity Planning

Document findings:
- Maximum verified capacity
- Resource utilization at peak
- Scaling recommendations

### 2. Optimization Backlog

Create issues for:
- Identified bottlenecks
- Slow endpoints
- Resource inefficiencies

### 3. Monitoring Setup

Implement monitoring for:
- Response time tracking
- Error rate alerts
- Resource utilization
- Capacity thresholds

### 4. Continuous Testing

Integrate into CI/CD:
- Run load tests on releases
- Track performance trends
- Detect regressions early

---

## Support

**Issues**:
- Review application logs: `logs/giljo_mcp.log`
- Check Locust logs: `tests/load/results/*.log`
- Review test results: `tests/load/results/*.html`

**Documentation**:
- Locust docs: https://docs.locust.io/
- GiljoAI MCP docs: See project README.md

---

**Document Version**: 1.0
**Last Updated**: 2025-11-11
**Author**: Load Testing Framework Setup

---

**Happy Load Testing! 🚀**
