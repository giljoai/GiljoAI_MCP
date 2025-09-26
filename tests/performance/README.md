# GiljoAI MCP Performance Testing Suite

A comprehensive performance testing framework for validating production-ready scalability with 100+ concurrent agents.

## 🎯 Overview

This performance testing suite validates that the GiljoAI MCP system meets all production requirements for commercial deployment, including:

- **100+ concurrent agents** operating simultaneously
- **10,000+ messages per minute** throughput
- **Sub-100ms latency** for critical operations
- **Complete tenant isolation** under load
- **50K+ token vision documents** processing
- **WebSocket capacity** for real-time communication

## 📁 Test Suite Structure

```
tests/performance/
├── test_concurrent_agents.py      # Agent scalability tests (100+ agents)
├── test_message_queue_load.py     # Message throughput & saturation tests
├── test_websocket_stress.py       # WebSocket connection stress tests
├── test_multi_tenant_load.py      # Multi-tenant isolation tests
├── test_vision_chunking_load.py   # Vision document processing tests
├── test_database_benchmarks.py    # Database performance benchmarks
├── load_test_runner.py            # Orchestrates all performance tests
├── performance_dashboard.py       # Real-time monitoring dashboard
├── generate_ci_report.py          # CI/CD integration & reporting
├── ci_performance_config.yml      # GitHub Actions workflow
└── README.md                      # This documentation
```

## 🚀 Quick Start

### 1. Run Individual Test Modules

```bash
# Test agent scalability (CRITICAL)
pytest tests/performance/test_concurrent_agents.py::TestConcurrentAgents::test_concurrent_agent_spawning_100_production_requirement -v

# Test message queue throughput
pytest tests/performance/test_message_queue_load.py::TestMessageQueueLoad::test_message_saturation_1000_messages -v

# Test WebSocket capacity
pytest tests/performance/test_websocket_stress.py::TestWebSocketStress::test_concurrent_websocket_connections_100_production_requirement -v

# Test database performance
pytest tests/performance/test_database_benchmarks.py -v

# Test vision document processing
pytest tests/performance/test_vision_chunking_load.py::TestVisionChunkingLoad::test_large_document_chunking_50k_tokens -v

# Test multi-tenant isolation
pytest tests/performance/test_multi_tenant_load.py -v
```

### 2. Run Complete Performance Suite

```bash
cd tests/performance
python load_test_runner.py
```

This generates:

- `performance_test_report.json` - Detailed test results
- `performance_summary.csv` - Spreadsheet-friendly summary
- `performance_dashboard.html` - Visual dashboard

### 3. Real-time Performance Monitoring

```bash
cd tests/performance
python performance_dashboard.py
```

Creates a live HTML dashboard with real-time metrics and alerts.

## 📊 Test Categories

### 🤖 Agent Scalability Tests (`test_concurrent_agents.py`)

**Production Requirement:** 100+ concurrent agents

- **Baseline Tests:** 10, 50 agents for performance baseline
- **Production Test:** Exactly 100 agents (CRITICAL requirement)
- **Stress Test:** 150 agents to identify system limits
- **Lifecycle Tests:** Agent handoffs and context switching under load

**Key Metrics:**

- Agent creation latency < 100ms
- 100 agents spawn in < 30 seconds
- 95%+ success rate required

### 📨 Message Queue Load Tests (`test_message_queue_load.py`)

**Production Requirement:** 10,000+ messages per minute

- **Single Message Latency:** < 100ms per message
- **Broadcast Performance:** Message delivery to 100+ agents
- **Saturation Tests:** 1,000 and 10,000 message floods
- **Acknowledgment Performance:** Message confirmation arrays
- **Priority Handling:** High/normal priority message processing

**Key Metrics:**

- Message send latency < 100ms
- Throughput ≥ 10,000 messages/minute
- Zero message loss under load

### 🌐 WebSocket Stress Tests (`test_websocket_stress.py`)

**Production Requirement:** 100+ concurrent WebSocket connections

- **Connection Latency:** Individual connection establishment time
- **Concurrent Connections:** 10, 50, 100 connection tests
- **Connection Stability:** Sustained connections under load
- **Message Latency:** Real-time message delivery
- **Reconnection Capability:** Network interruption recovery

**Key Metrics:**

- 100 concurrent connections supported
- Connection latency < 1 second
- 80%+ connection success rate

### 🏢 Multi-Tenant Load Tests (`test_multi_tenant_load.py`)

**Production Requirement:** Complete tenant isolation under load

- **Dual Tenant Performance:** 2 tenants with concurrent load
- **Five Tenant Stress:** 5 tenants × 20 agents each
- **Data Isolation Verification:** Cross-tenant security validation
- **Performance Isolation:** One tenant can't impact others
- **Resource Fairness:** Equal resource allocation across tenants

**Key Metrics:**

- Complete data isolation verified
- <25% performance degradation between tenants
- Fair resource allocation

### 📄 Vision Document Tests (`test_vision_chunking_load.py`)

**Production Requirement:** 50K+ token document processing

- **Large Document Processing:** 50K+ token chunking
- **Concurrent Document Handling:** Multiple documents simultaneously
- **Memory Usage Analysis:** Memory efficiency under load
- **Indexing Performance:** Document search and retrieval
- **Chunk Retrieval:** Individual chunk access performance

**Key Metrics:**

- 50K+ tokens processed in < 60 seconds
- Memory usage < 1GB growth
- Chunk retrieval < 10ms

### 💾 Database Benchmarks (`test_database_benchmarks.py`)

**Production Requirement:** Sub-100ms operations

- **Single Record Operations:** Create, read, update latency
- **Bulk Operations:** Batch inserts and updates
- **Query Performance:** Complex queries under load
- **Transaction Performance:** Multi-operation transactions
- **Concurrent Operations:** Database stress with 50+ operations
- **Connection Pool Stress:** 100+ concurrent connections

**Key Metrics:**

- Single operations < 100ms
- Query performance < 500ms
- 95%+ transaction success rate

## 🎛️ Performance Dashboard

The performance dashboard provides real-time monitoring and historical analysis:

### Features:

- **Real-time Metrics:** Live performance data
- **Production Readiness Score:** Overall system health (0-100%)
- **Component Breakdown:** Individual subsystem performance
- **Alert System:** Threshold-based warnings
- **Trend Analysis:** Historical performance data
- **Web Interface:** HTML dashboard for easy viewing

### Usage:

```bash
# Generate static dashboard
python performance_dashboard.py

# Start real-time monitoring
python -c "
from performance_dashboard import PerformanceDashboard, PerformanceMonitor
import asyncio

dashboard = PerformanceDashboard()
monitor = PerformanceMonitor(dashboard)
asyncio.run(monitor.start_monitoring())
"
```

## ⚙️ CI/CD Integration

### GitHub Actions Workflow

The test suite integrates with GitHub Actions for automated performance validation:

```yaml
# .github/workflows/performance.yml
name: Performance Testing Suite
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 2 * * *" # Nightly at 2 AM UTC
```

### Test Levels:

- **Standard:** Core performance tests (30 min)
- **Comprehensive:** Full test suite (90 min)
- **Stress:** Beyond-requirements testing (120 min)

### Automated Reporting:

- Performance score comments on PRs
- Slack notifications for failures
- GitHub Pages dashboard deployment
- Trend analysis and alerts

### Setup CI/CD:

1. Copy `ci_performance_config.yml` to `.github/workflows/performance.yml`
2. Configure secrets: `SLACK_WEBHOOK` (optional)
3. Enable GitHub Pages for dashboard deployment

## 📈 Performance Thresholds

### Critical Thresholds (Production Requirements):

```python
PRODUCTION_THRESHOLDS = {
    "agent_creation_ms": 100,        # Agent spawn latency
    "message_send_ms": 100,          # Message delivery latency
    "websocket_connection_ms": 1000, # WebSocket connection time
    "database_query_ms": 50,         # Database operation latency
    "vision_chunking_ms": 5000,      # Large document processing
    "concurrent_agents": 100,        # Minimum agent capacity
    "messages_per_minute": 10000,    # Minimum message throughput
    "websocket_connections": 100,    # Minimum WebSocket capacity
    "memory_usage_mb": 2000,         # Maximum memory usage
    "cpu_usage_percent": 80          # Maximum CPU usage
}
```

### Scoring System:

- **Agent Scalability:** 30% weight
- **Message Throughput:** 25% weight
- **Database Performance:** 20% weight
- **WebSocket Capacity:** 15% weight
- **Vision Processing:** 10% weight

### Production Readiness Levels:

- **90-100%:** Production Ready ✅
- **75-89%:** Mostly Ready ⚠️
- **50-74%:** Needs Improvement 🔄
- **0-49%:** Not Ready ❌

## 🛠️ Development & Debugging

### Running Tests Locally:

```bash
# Install dependencies
pip install pytest pytest-asyncio psutil websockets

# Run with verbose output
pytest tests/performance/test_concurrent_agents.py -v -s

# Run specific test
pytest tests/performance/test_concurrent_agents.py::TestConcurrentAgents::test_concurrent_agent_spawning_100_production_requirement -v -s

# Run with performance markers
pytest tests/performance/ -m "not slow" -v  # Skip slow tests
pytest tests/performance/ -m "stress" -v    # Only stress tests
```

### Debug Performance Issues:

```bash
# Run with detailed output
pytest tests/performance/test_concurrent_agents.py -v -s --tb=long

# Profile memory usage
python -m memory_profiler tests/performance/test_concurrent_agents.py

# Monitor system resources
htop  # or top on macOS/Linux
```

### Test Markers:

- `@pytest.mark.slow` - Tests taking >60 seconds
- `@pytest.mark.stress` - Stress tests beyond requirements
- No marker - Standard performance tests

## 📋 Production Validation Checklist

Before production deployment, ensure all tests pass:

### Agent Scalability ✅

- [ ] 100 agents spawn successfully (95%+ success rate)
- [ ] Agent creation latency < 100ms average
- [ ] Context switching performs efficiently
- [ ] Agent handoffs work under load

### Message Throughput ✅

- [ ] 10,000+ messages/minute sustained
- [ ] Message latency < 100ms
- [ ] Broadcast to 100+ agents works
- [ ] Zero message loss under saturation

### WebSocket Capacity ✅

- [ ] 100+ concurrent connections supported
- [ ] Connection latency < 1 second
- [ ] Stable connections under load
- [ ] Reconnection works reliably

### Multi-Tenant Isolation ✅

- [ ] Complete data isolation verified
- [ ] Performance isolation maintained
- [ ] Fair resource allocation
- [ ] Security boundaries enforced

### Vision Processing ✅

- [ ] 50K+ token documents process successfully
- [ ] Reasonable memory usage (<1GB growth)
- [ ] Concurrent document handling works
- [ ] Chunk retrieval is fast (<10ms)

### Database Performance ✅

- [ ] Sub-100ms operation latency
- [ ] Concurrent operations handle properly
- [ ] Transaction reliability high (>95%)
- [ ] Connection pooling scales

### System Health ✅

- [ ] Memory usage reasonable (<2GB)
- [ ] CPU usage manageable (<80%)
- [ ] No memory leaks detected
- [ ] Graceful degradation under stress

## 🔧 Troubleshooting

### Common Issues:

#### Agent Spawning Failures

```bash
# Check database connections
pytest tests/performance/test_database_benchmarks.py::TestDatabaseBenchmarks::test_single_record_operations_latency -v

# Verify orchestrator setup
pytest tests/performance/test_concurrent_agents.py::TestConcurrentAgents::test_single_agent_creation_latency -v
```

#### Message Queue Issues

```bash
# Test message tools
pytest tests/performance/test_message_queue_load.py::TestMessageQueueLoad::test_single_message_latency -v

# Check database message storage
pytest tests/performance/test_database_benchmarks.py -k "message" -v
```

#### WebSocket Connection Problems

```bash
# Verify WebSocket server is running
python -c "import websockets; print('WebSocket client available')"

# Test with lower connection count
pytest tests/performance/test_websocket_stress.py::TestWebSocketStress::test_concurrent_websocket_connections_10 -v
```

#### Memory Issues

```bash
# Monitor memory during tests
python -c "
import psutil
import time
while True:
    mem = psutil.virtual_memory()
    print(f'Memory: {mem.percent:.1f}% used, {mem.available/1024**3:.1f}GB available')
    time.sleep(5)
"
```

### Performance Optimization Tips:

1. **Database Optimization:**

   - Ensure proper indexing on frequently queried fields
   - Use connection pooling
   - Optimize query patterns

2. **Message Queue Optimization:**

   - Implement message batching
   - Use asynchronous processing
   - Consider message prioritization

3. **Agent Management:**

   - Implement agent pooling
   - Optimize context switching
   - Use efficient serialization

4. **Memory Management:**
   - Monitor for memory leaks
   - Implement garbage collection triggers
   - Use memory-efficient data structures

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Asyncio Performance Tips](https://docs.python.org/3/library/asyncio.html)
- [SQLAlchemy Performance](https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html)
- [WebSocket Performance](https://websockets.readthedocs.io/en/stable/)

## 🤝 Contributing

When adding new performance tests:

1. Follow the existing test structure
2. Include both baseline and stress tests
3. Add appropriate pytest markers (`@pytest.mark.slow`, `@pytest.mark.stress`)
4. Update thresholds in `performance_dashboard.py`
5. Add CI integration if needed
6. Document new requirements in this README

## 📄 License

This performance testing suite is part of the GiljoAI MCP project.
