# Monitoring Setup Guide

**Last Updated**: October 8, 2025
**Version**: 2.0.0
**Audience**: System administrators and DevOps teams

---

## Table of Contents

1. [Overview](#overview)
2. [Key Metrics](#key-metrics)
3. [Logging Configuration](#logging-configuration)
4. [Performance Benchmarks](#performance-benchmarks)
5. [Alert Thresholds](#alert-thresholds)
6. [Dashboard Setup](#dashboard-setup)
7. [Monitoring Tools](#monitoring-tools)

---

## Overview

This guide provides comprehensive monitoring setup for the GiljoAI MCP Orchestrator v2.0 production deployment. Effective monitoring ensures early detection of issues, performance optimization, and reliable operations.

### Monitoring Goals

- **Availability**: Ensure 99.9% uptime
- **Performance**: Maintain sub-100ms query response times
- **Capacity**: Prevent resource exhaustion
- **Security**: Detect unauthorized access attempts
- **User Experience**: Monitor agent success rates and token efficiency

### Monitoring Architecture

```
┌─────────────────────────────────────────┐
│         GiljoAI MCP Application         │
├─────────────────────────────────────────┤
│  API Server    │  Database  │ Frontend │
│  (Metrics)     │  (Stats)   │  (Logs)  │
└────────┬───────┴──────┬─────┴──────┬────┘
         │              │            │
         ▼              ▼            ▼
┌─────────────────────────────────────────┐
│        Metrics Collection Layer         │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Prometheus│ │PostgreSQL│ │ Fluentd │ │
│  │  Metrics │ │   Stats  │ │  Logs   │ │
│  └──────────┘ └──────────┘ └─────────┘ │
└────────┬───────────────┬────────────┬───┘
         │               │            │
         ▼               ▼            ▼
┌─────────────────────────────────────────┐
│       Visualization & Alerting          │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ Grafana  │ │AlertMgr  │ │ Kibana  │ │
│  │Dashboard │ │ Alerts   │ │LogSearch│ │
│  └──────────┘ └──────────┘ └─────────┘ │
└─────────────────────────────────────────┘
```

---

## Key Metrics

### 1. Token Usage Metrics

**Why Monitor:**
- Core value proposition of v2.0 is 60% token reduction
- Verify role-based filtering effectiveness
- Detect configuration issues

**Metrics to Track:**

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|----------------|
| `orchestrator_token_count` | Avg tokens per orchestrator context load | 15,000-20,000 | > 25,000 |
| `worker_token_count` | Avg tokens per worker context load | 6,000-8,000 | > 12,000 |
| `token_reduction_percentage` | Actual reduction from filtering | 55-65% | < 50% |
| `context_load_failures` | Failed context loading attempts | 0 | > 5/hour |

**How to Collect:**

```python
# Add to src/giljo_mcp/tools/product.py

import prometheus_client as prom

# Define metrics
CONTEXT_TOKENS = prom.Histogram(
    'giljo_context_tokens',
    'Tokens loaded per context request',
    ['role']
)

TOKEN_REDUCTION = prom.Gauge(
    'giljo_token_reduction_percentage',
    'Token reduction from filtering'
)

@mcp_tool
async def get_product_config(project_id: str, filtered: bool = True, agent_name: str = None):
    # ... existing code ...

    # Track metrics
    role = detect_role(agent_name)
    token_count = len(json.dumps(filtered_config).split())  # Rough estimate
    CONTEXT_TOKENS.labels(role=role).observe(token_count)

    if filtered:
        full_token_count = len(json.dumps(product.config_data).split())
        reduction = ((full_token_count - token_count) / full_token_count) * 100
        TOKEN_REDUCTION.set(reduction)

    return filtered_config
```

**Prometheus Query:**

```promql
# Average tokens by role (last 1 hour)
avg by (role) (giljo_context_tokens_sum / giljo_context_tokens_count)

# Token reduction percentage
giljo_token_reduction_percentage
```

---

### 2. Context Loading Time

**Why Monitor:**
- Target: < 2 seconds for orchestrator, < 1 second for workers
- Performance regression detection
- GIN index effectiveness

**Metrics to Track:**

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|----------------|
| `context_load_duration_orchestrator` | Time to load full context | < 2s | > 3s |
| `context_load_duration_worker` | Time to load filtered context | < 1s | > 2s |
| `gin_index_scan_time` | GIN index query time | < 100ms | > 200ms |
| `context_load_p95` | 95th percentile load time | < 2.5s | > 5s |

**How to Collect:**

```python
# Add to src/giljo_mcp/tools/product.py

import time
from prometheus_client import Histogram

CONTEXT_LOAD_TIME = Histogram(
    'giljo_context_load_duration_seconds',
    'Context loading duration',
    ['role', 'filtered'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

@mcp_tool
async def get_product_config(project_id: str, filtered: bool = True, agent_name: str = None):
    start_time = time.time()

    # ... existing code ...

    duration = time.time() - start_time
    role = detect_role(agent_name)
    CONTEXT_LOAD_TIME.labels(role=role, filtered=str(filtered)).observe(duration)

    return filtered_config
```

**Prometheus Query:**

```promql
# 95th percentile context load time
histogram_quantile(0.95,
  rate(giljo_context_load_duration_seconds_bucket[5m]))

# Average by role
avg by (role) (rate(giljo_context_load_duration_seconds_sum[5m]) /
               rate(giljo_context_load_duration_seconds_count[5m]))
```

---

### 3. GIN Index Performance

**Why Monitor:**
- Critical for fast config_data queries
- Detect index degradation
- Validate migration success

**Metrics to Track:**

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|----------------|
| `gin_index_scans` | Number of GIN index scans | N/A | Decreasing trend |
| `gin_tuples_read` | Tuples read by index | N/A | Increasing trend |
| `gin_index_size` | Index size in MB | < 100MB | > 500MB |
| `sequential_scans` | Seq scans on products table | 0 | > 10/hour |

**How to Collect:**

```sql
-- PostgreSQL query for GIN index stats
-- Run periodically (via cron/scheduled task) and export to metrics

SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE indexname = 'idx_product_config_data_gin';
```

**Export to Prometheus:**

```python
# Add to scripts/export_db_metrics.py

import psycopg2
from prometheus_client import Gauge, start_http_server

GIN_INDEX_SCANS = Gauge('giljo_gin_index_scans_total', 'GIN index scan count')
GIN_TUPLES_READ = Gauge('giljo_gin_tuples_read_total', 'Tuples read by GIN index')
GIN_INDEX_SIZE = Gauge('giljo_gin_index_size_bytes', 'GIN index size in bytes')

def collect_gin_metrics():
    conn = psycopg2.connect("dbname=giljo_mcp user=postgres")
    cur = conn.cursor()

    cur.execute("""
        SELECT idx_scan, idx_tup_read, pg_relation_size(indexrelid)
        FROM pg_stat_user_indexes
        WHERE indexname = 'idx_product_config_data_gin'
    """)

    scans, tuples, size = cur.fetchone()
    GIN_INDEX_SCANS.set(scans)
    GIN_TUPLES_READ.set(tuples)
    GIN_INDEX_SIZE.set(size)

    cur.close()
    conn.close()

if __name__ == '__main__':
    start_http_server(8001)  # Prometheus scrape endpoint
    while True:
        collect_gin_metrics()
        time.sleep(60)  # Collect every minute
```

**Prometheus Query:**

```promql
# GIN index scan rate
rate(giljo_gin_index_scans_total[5m])

# Index size growth
delta(giljo_gin_index_size_bytes[1h])
```

---

### 4. API Response Time

**Why Monitor:**
- User experience indicator
- Performance regression detection
- Capacity planning

**Metrics to Track:**

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|----------------|
| `api_request_duration_p50` | Median response time | < 100ms | > 500ms |
| `api_request_duration_p95` | 95th percentile | < 500ms | > 2s |
| `api_request_duration_p99` | 99th percentile | < 1s | > 5s |
| `api_error_rate` | 5xx error rate | < 0.1% | > 1% |

**How to Collect:**

```python
# Add to api/middleware/metrics.py

from fastapi import Request
from prometheus_client import Histogram, Counter
import time

REQUEST_DURATION = Histogram(
    'giljo_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint', 'status'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

REQUEST_COUNT = Counter(
    'giljo_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).observe(duration)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    return response

# Register in api/app.py:
# app.middleware("http")(metrics_middleware)
```

**Prometheus Query:**

```promql
# 95th percentile response time by endpoint
histogram_quantile(0.95,
  rate(giljo_api_request_duration_seconds_bucket[5m]))

# Error rate
sum(rate(giljo_api_requests_total{status=~"5.."}[5m])) /
sum(rate(giljo_api_requests_total[5m]))
```

---

### 5. PostgreSQL Metrics

**Why Monitor:**
- Database health
- Capacity planning
- Query performance

**Metrics to Track:**

| Metric | Description | Target | Alert Threshold |
|--------|-------------|--------|----------------|
| `db_connections_active` | Active connections | < 50 | > 80 |
| `db_transactions_per_second` | Transaction rate | N/A | Sudden drop |
| `db_cache_hit_ratio` | Cache effectiveness | > 95% | < 90% |
| `db_deadlocks` | Deadlock count | 0 | > 0 |
| `db_table_bloat` | Table bloat percentage | < 20% | > 50% |

**How to Collect:**

```sql
-- PostgreSQL monitoring queries
-- Run via postgres_exporter or custom script

-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Cache hit ratio
SELECT
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio
FROM pg_statio_user_tables;

-- Table bloat
SELECT
  schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                 pg_relation_size(schemaname||'.'||tablename)) AS bloat
FROM pg_tables
WHERE tablename = 'products';
```

**Prometheus Exporter:**

Use [postgres_exporter](https://github.com/prometheus-community/postgres_exporter):

```bash
# Install postgres_exporter
wget https://github.com/prometheus-community/postgres_exporter/releases/download/v0.15.0/postgres_exporter-0.15.0.linux-amd64.tar.gz
tar -xzf postgres_exporter-0.15.0.linux-amd64.tar.gz
cd postgres_exporter-0.15.0.linux-amd64

# Configure
export DATA_SOURCE_NAME="postgresql://postgres:password@localhost:5432/giljo_mcp?sslmode=disable"

# Run
./postgres_exporter

# Add to prometheus.yml:
# scrape_configs:
#   - job_name: 'postgresql'
#     static_configs:
#       - targets: ['localhost:9187']
```

---

## Logging Configuration

### Application Logging

**Configure structured JSON logging:**

```yaml
# config.yaml
logging:
  level: INFO
  format: json  # Structured logging
  file: /var/log/giljo-mcp/api.log
  max_size_mb: 100
  backup_count: 10
  rotate_on_startup: false

  # Log categories
  categories:
    api: INFO
    database: WARNING
    orchestrator: INFO
    context_manager: INFO
    mcp_tools: DEBUG

  # Performance logging
  performance:
    slow_query_threshold: 1000  # ms
    slow_request_threshold: 2000  # ms
    log_request_body: false  # Privacy
    log_response_body: false
```

**Python logging setup:**

```python
# src/giljo_mcp/logging_config.py

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def setup_logging(config):
    handler = logging.handlers.RotatingFileHandler(
        config['file'],
        maxBytes=config['max_size_mb'] * 1024 * 1024,
        backupCount=config['backup_count']
    )
    handler.setFormatter(JSONFormatter())

    logging.basicConfig(
        level=getattr(logging, config['level']),
        handlers=[handler]
    )
```

### Important Log Events

**Events to log:**

```python
# Context loading
logger.info("Context loaded",
    extra={
        'project_id': project_id,
        'agent_name': agent_name,
        'role': role,
        'filtered': filtered,
        'token_count': token_count,
        'duration_ms': duration * 1000
    }
)

# Slow queries
logger.warning("Slow database query",
    extra={
        'query': query_name,
        'duration_ms': duration * 1000,
        'table': 'products',
        'operation': 'SELECT'
    }
)

# Authentication failures
logger.warning("Authentication failed",
    extra={
        'ip_address': request.client.host,
        'endpoint': request.url.path,
        'reason': 'invalid_api_key'
    }
)

# Migration events
logger.info("Migration started",
    extra={
        'migration': 'add_config_data',
        'from_revision': '11b1e4318444',
        'to_revision': '8406a7a6dcc5'
    }
)
```

### Log Aggregation

**Using Fluentd (recommended):**

```conf
# /etc/fluentd/fluent.conf

<source>
  @type tail
  path /var/log/giljo-mcp/api.log
  pos_file /var/log/fluentd/giljo-api.log.pos
  tag giljo.api
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S
  </parse>
</source>

<filter giljo.**>
  @type record_transformer
  <record>
    hostname "#{Socket.gethostname}"
    service giljo-mcp
    environment production
  </record>
</filter>

<match giljo.**>
  @type elasticsearch
  host localhost
  port 9200
  index_name giljo-logs
  type_name _doc
  logstash_format true
  logstash_prefix giljo
  <buffer>
    flush_interval 10s
  </buffer>
</match>
```

---

## Performance Benchmarks

### Expected Performance Targets

**v2.0 Baseline Performance:**

| Operation | Target | Acceptable | Unacceptable |
|-----------|--------|------------|--------------|
| Orchestrator context load | < 2s | < 3s | > 5s |
| Worker context load | < 1s | < 2s | > 3s |
| GIN index query | < 100ms | < 200ms | > 500ms |
| API health check | < 50ms | < 100ms | > 500ms |
| API product list | < 200ms | < 500ms | > 2s |
| Database connection | < 10ms | < 50ms | > 200ms |
| WebSocket message | < 100ms | < 250ms | > 1s |

### Performance Testing

**Automated performance tests:**

```python
# tests/performance/test_orchestrator_v2_performance.py

import pytest
import time
from src.giljo_mcp.tools.product import get_product_config

@pytest.mark.performance
async def test_orchestrator_context_load_time():
    """Verify orchestrator context loads within 2 seconds"""
    start = time.time()
    config = await get_product_config(
        project_id='test-project',
        filtered=False
    )
    duration = time.time() - start

    assert duration < 2.0, f"Context load too slow: {duration:.2f}s"
    assert len(config['config']) >= 13, "Incomplete config loaded"

@pytest.mark.performance
async def test_worker_context_load_time():
    """Verify worker context loads within 1 second"""
    start = time.time()
    config = await get_product_config(
        project_id='test-project',
        filtered=True,
        agent_name='implementer-test'
    )
    duration = time.time() - start

    assert duration < 1.0, f"Worker context load too slow: {duration:.2f}s"
    assert len(config['config']) < 13, "Filtering not applied"

@pytest.mark.performance
def test_gin_index_query_time(db_connection):
    """Verify GIN index queries are sub-100ms"""
    import psycopg2

    conn = psycopg2.connect("dbname=giljo_mcp user=postgres")
    cur = conn.cursor()

    start = time.time()
    cur.execute("""
        SELECT * FROM products
        WHERE config_data @> '{"database_type": "postgresql"}'
    """)
    results = cur.fetchall()
    duration = (time.time() - start) * 1000  # Convert to ms

    cur.close()
    conn.close()

    assert duration < 100, f"GIN index query too slow: {duration:.2f}ms"
    assert len(results) > 0, "No results found"
```

**Run performance tests:**

```bash
# Run performance test suite
pytest tests/performance/ -m performance -v

# With benchmarking
pytest tests/performance/ -m performance --benchmark-only

# Generate performance report
pytest tests/performance/ -m performance --html=performance_report.html
```

---

## Alert Thresholds

### Critical Alerts (Immediate Response)

```yaml
# Prometheus alert rules
# /etc/prometheus/alerts.d/giljo-critical.yml

groups:
  - name: giljo_critical
    interval: 30s
    rules:
      - alert: APIServerDown
        expr: up{job="giljo-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "GiljoAI API server is down"
          description: "API server has been down for 1 minute"

      - alert: DatabaseDown
        expr: up{job="postgresql"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL database is down"
          description: "Database has been down for 1 minute"

      - alert: HighErrorRate
        expr: |
          sum(rate(giljo_api_requests_total{status=~"5.."}[5m])) /
          sum(rate(giljo_api_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High API error rate (>5%)"
          description: "Error rate: {{ $value | humanizePercentage }}"

      - alert: DatabaseConnectionsExhausted
        expr: |
          sum(pg_stat_database_numbackends{datname="giljo_mcp"}) /
          pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connections near limit (>80%)"
          description: "Connections: {{ $value | humanize }}"
```

### Warning Alerts (Review Within 1 Hour)

```yaml
# /etc/prometheus/alerts.d/giljo-warnings.yml

groups:
  - name: giljo_warnings
    interval: 1m
    rules:
      - alert: SlowContextLoading
        expr: |
          histogram_quantile(0.95,
            rate(giljo_context_load_duration_seconds_bucket[5m])
          ) > 3
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Context loading slow (p95 > 3s)"
          description: "95th percentile: {{ $value }}s"

      - alert: TokenReductionLow
        expr: giljo_token_reduction_percentage < 50
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Token reduction below target (<50%)"
          description: "Current reduction: {{ $value }}%"

      - alert: GINIndexNotUsed
        expr: |
          rate(pg_stat_user_tables_seq_scan{relname="products"}[5m]) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Sequential scans on products table"
          description: "GIN index may not be used"

      - alert: HighMemoryUsage
        expr: |
          process_resident_memory_bytes{job="giljo-api"} /
          node_memory_MemTotal_bytes > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage (>80%)"
          description: "Memory: {{ $value | humanizePercentage }}"
```

### Info Alerts (Review Daily)

```yaml
# /etc/prometheus/alerts.d/giljo-info.yml

groups:
  - name: giljo_info
    interval: 5m
    rules:
      - alert: HighRequestLatency
        expr: |
          histogram_quantile(0.99,
            rate(giljo_api_request_duration_seconds_bucket[5m])
          ) > 2
        for: 30m
        labels:
          severity: info
        annotations:
          summary: "High request latency (p99 > 2s)"
          description: "99th percentile: {{ $value }}s"

      - alert: DatabaseCacheHitRatioLow
        expr: |
          sum(pg_stat_database_blks_hit) /
          (sum(pg_stat_database_blks_hit) + sum(pg_stat_database_blks_read)) < 0.9
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "Database cache hit ratio low (<90%)"
          description: "Cache hit ratio: {{ $value | humanizePercentage }}"
```

---

## Dashboard Setup

### Grafana Dashboard - Orchestrator v2.0

**Dashboard JSON:**

```json
{
  "dashboard": {
    "title": "GiljoAI MCP Orchestrator v2.0",
    "tags": ["giljo", "orchestrator", "v2.0"],
    "timezone": "browser",
    "rows": [
      {
        "title": "Overview",
        "panels": [
          {
            "title": "API Requests/sec",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(giljo_api_requests_total[5m])"
              }
            ]
          },
          {
            "title": "Error Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "sum(rate(giljo_api_requests_total{status=~\"5..\"}[5m])) / sum(rate(giljo_api_requests_total[5m]))"
              }
            ]
          },
          {
            "title": "Active Database Connections",
            "type": "graph",
            "targets": [
              {
                "expr": "pg_stat_database_numbackends{datname=\"giljo_mcp\"}"
              }
            ]
          }
        ]
      },
      {
        "title": "Orchestrator v2.0 Metrics",
        "panels": [
          {
            "title": "Token Usage by Role",
            "type": "graph",
            "targets": [
              {
                "expr": "avg by (role) (giljo_context_tokens_sum / giljo_context_tokens_count)",
                "legendFormat": "{{ role }}"
              }
            ]
          },
          {
            "title": "Token Reduction %",
            "type": "stat",
            "targets": [
              {
                "expr": "giljo_token_reduction_percentage"
              }
            ],
            "thresholds": "50,60"
          },
          {
            "title": "Context Load Time (p95)",
            "type": "graph",
            "targets": [
              {
                "expr": "histogram_quantile(0.95, rate(giljo_context_load_duration_seconds_bucket[5m]))",
                "legendFormat": "p95"
              }
            ]
          }
        ]
      },
      {
        "title": "Database Performance",
        "panels": [
          {
            "title": "GIN Index Scans",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(giljo_gin_index_scans_total[5m])"
              }
            ]
          },
          {
            "title": "GIN Index Size",
            "type": "stat",
            "targets": [
              {
                "expr": "giljo_gin_index_size_bytes"
              }
            ],
            "unit": "bytes"
          },
          {
            "title": "Query Duration",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(pg_stat_statements_mean_exec_time[5m])"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**Dashboard Import:**

```bash
# Import dashboard via Grafana API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @giljo_orchestrator_v2_dashboard.json
```

---

## Monitoring Tools

### Recommended Stack

**1. Prometheus (Metrics Collection)**

```bash
# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar -xzf prometheus-2.45.0.linux-amd64.tar.gz
cd prometheus-2.45.0.linux-amd64

# Configure prometheus.yml
cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'giljo-api'
    static_configs:
      - targets: ['localhost:7272']

  - job_name: 'postgresql'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
EOF

# Run Prometheus
./prometheus --config.file=prometheus.yml
```

**2. Grafana (Visualization)**

```bash
# Install Grafana
sudo apt-get install -y grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Access: http://localhost:3000
# Default: admin/admin
```

**3. AlertManager (Alerting)**

```bash
# Install AlertManager
wget https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.linux-amd64.tar.gz
tar -xzf alertmanager-0.26.0.linux-amd64.tar.gz
cd alertmanager-0.26.0.linux-amd64

# Configure alertmanager.yml
cat > alertmanager.yml << 'EOF'
route:
  receiver: 'email'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10m
  repeat_interval: 12h

receivers:
  - name: 'email'
    email_configs:
      - to: 'alerts@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'password'
EOF

# Run AlertManager
./alertmanager --config.file=alertmanager.yml
```

**4. ELK Stack (Log Analysis)**

```bash
# Install Elasticsearch
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.10.0-linux-x86_64.tar.gz
tar -xzf elasticsearch-8.10.0-linux-x86_64.tar.gz
cd elasticsearch-8.10.0
./bin/elasticsearch

# Install Kibana
wget https://artifacts.elastic.co/downloads/kibana/kibana-8.10.0-linux-x86_64.tar.gz
tar -xzf kibana-8.10.0-linux-x86_64.tar.gz
cd kibana-8.10.0-linux-x86_64
./bin/kibana

# Access Kibana: http://localhost:5601
```

---

## Summary

This monitoring setup ensures comprehensive observability for GiljoAI MCP Orchestrator v2.0:

- **Token Usage**: Track 60% reduction effectiveness
- **Performance**: Monitor context loading and GIN index performance
- **Availability**: Alert on service outages
- **Database**: Monitor PostgreSQL health and query performance
- **Visualization**: Grafana dashboards for real-time insights

**Next Steps:**
1. Deploy monitoring stack (Prometheus, Grafana, AlertManager)
2. Configure alert rules and notification channels
3. Import Grafana dashboards
4. Set up log aggregation (Fluentd + Elasticsearch)
5. Test alerts and dashboards
6. Document monitoring runbooks

**Related Documentation:**
- [Production Deployment Checklist](PRODUCTION_DEPLOYMENT_CHECKLIST.md)
- [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
- [Technical Architecture](../TECHNICAL_ARCHITECTURE.md)

---

**Document Status**: Production Ready
**Next Review**: After first month of production monitoring

---

_Last Updated: October 8, 2025_
_Version: 2.0.0_
