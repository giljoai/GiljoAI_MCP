# Performance Tuning Guide - mcp_context_index

**Handover 0018**: Context Management System
**Target**: Sub-100ms search on 10,000+ chunks
**Database**: PostgreSQL 18

---

## Quick Reference

### Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Simple search (10K chunks) | < 100ms | Yes |
| Complex search (10K chunks) | < 200ms | Yes |
| Document reconstruction | < 50ms | No |
| Index build time | < 30s per 10K chunks | No |

### Critical Settings

```ini
# PostgreSQL Configuration (postgresql.conf)
maintenance_work_mem = 256MB
shared_buffers = 256MB
work_mem = 16MB
effective_cache_size = 1GB
random_page_cost = 1.1  # For SSD storage
```

---

## Index Optimization

### 1. GIN Index Health Check

```sql
-- Check GIN index size and usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE tablename = 'mcp_context_index'
  AND indexname = 'idx_mcp_context_searchable_gin';

-- Expected results for healthy index:
-- scans: > 1000 (frequently used)
-- size: Roughly 20-30% of table size
```

### 2. Rebuild Index if Degraded

```sql
-- Rebuild index online (no downtime)
REINDEX INDEX CONCURRENTLY idx_mcp_context_searchable_gin;

-- Rebuild all indexes for table
REINDEX TABLE CONCURRENTLY mcp_context_index;

-- Update statistics after rebuild
ANALYZE mcp_context_index;
```

### 3. Monitor Index Bloat

```sql
-- Check for index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'mcp_context_index'
ORDER BY pg_relation_size(indexrelid) DESC;

-- If index_size growing but scans not increasing = potential bloat
-- Solution: REINDEX CONCURRENTLY
```

---

## Query Optimization

### 1. Query Plan Analysis

```sql
-- Analyze actual query performance
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT c.*, ts_rank(c.searchable_vector, query) AS rank
FROM mcp_context_index c,
     plainto_tsquery('english', 'database migration') query
WHERE c.tenant_key = 'tk_abc123...'
  AND c.searchable_vector @@ query
ORDER BY rank DESC
LIMIT 10;
```

**Good Plan Indicators**:
- ✅ "Bitmap Index Scan on idx_mcp_context_searchable_gin"
- ✅ "Bitmap Heap Scan" (recheck)
- ✅ Execution time < 100ms
- ✅ Low "Heap Blocks: lossy" count

**Bad Plan Indicators**:
- ❌ "Seq Scan on mcp_context_index"
- ❌ Execution time > 200ms
- ❌ High "Heap Blocks: lossy" count (increase work_mem)

### 2. Optimize Relevance Ranking

```sql
-- Fast ranking: ts_rank()
SELECT *, ts_rank(searchable_vector, query) AS rank
FROM mcp_context_index,
     plainto_tsquery('english', 'database') query
WHERE tenant_key = 'tk_abc'
  AND searchable_vector @@ query
ORDER BY rank DESC
LIMIT 10;
-- Typical time: 20-50ms

-- Accurate ranking: ts_rank_cd()
SELECT *, ts_rank_cd(searchable_vector, query, 32) AS rank
FROM mcp_context_index,
     plainto_tsquery('english', 'database') query
WHERE tenant_key = 'tk_abc'
  AND searchable_vector @@ query
ORDER BY rank DESC
LIMIT 10;
-- Typical time: 50-100ms

-- Recommendation: Use ts_rank() for real-time searches
--                 Use ts_rank_cd() for batch/background processing
```

### 3. Reduce Work_mem Spills

```sql
-- Check for work_mem spills
SELECT
    query,
    calls,
    total_time,
    mean_time,
    temp_blks_written  -- Non-zero = work_mem too small
FROM pg_stat_statements
WHERE query LIKE '%mcp_context_index%'
  AND temp_blks_written > 0
ORDER BY temp_blks_written DESC;

-- If seeing spills, increase work_mem:
SET work_mem = '32MB';  -- Per-session
-- Or in postgresql.conf for global change
```

---

## Table Maintenance

### 1. Vacuum Strategy

```sql
-- Manual vacuum (recommended weekly)
VACUUM ANALYZE mcp_context_index;

-- Check last vacuum time
SELECT
    schemaname,
    tablename,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_dead_tup
FROM pg_stat_user_tables
WHERE tablename = 'mcp_context_index';

-- If n_dead_tup > 10% of total rows: Run VACUUM
-- If last_analyze > 1 week ago: Run ANALYZE
```

### 2. Autovacuum Tuning

```sql
-- Check autovacuum settings
SELECT
    name,
    setting,
    unit,
    context
FROM pg_settings
WHERE name LIKE 'autovacuum%';

-- Recommended settings for high-write tables:
ALTER TABLE mcp_context_index
SET (
    autovacuum_vacuum_scale_factor = 0.1,  -- Vacuum at 10% dead tuples
    autovacuum_analyze_scale_factor = 0.05,  -- Analyze at 5% changes
    autovacuum_vacuum_cost_delay = 10  -- ms delay between pages
);
```

### 3. Table Bloat Check

```sql
-- Check table bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_tuple_percent
FROM pg_stat_user_tables
WHERE tablename = 'mcp_context_index';

-- If dead_tuple_percent > 10%: Run VACUUM
-- If dead_tuple_percent > 20%: Run VACUUM FULL (requires exclusive lock)
```

---

## PostgreSQL Configuration

### 1. Memory Settings

```ini
# postgresql.conf

# Shared memory for all connections
shared_buffers = 256MB  # 25% of RAM (max 8GB recommended)

# Memory for maintenance operations (REINDEX, CREATE INDEX)
maintenance_work_mem = 256MB  # Increase for faster index builds

# Memory per sort/hash operation
work_mem = 16MB  # Increase if seeing temp_blks_written

# Query planner's estimate of OS cache
effective_cache_size = 1GB  # 75% of RAM
```

### 2. Planner Settings

```ini
# Cost settings for SSD storage
random_page_cost = 1.1  # Default 4.0 is for HDD
seq_page_cost = 1.0

# Enable parallel query execution
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# Enable JIT compilation (PostgreSQL 11+)
jit = on
jit_above_cost = 100000
```

### 3. Full-Text Search Settings

```sql
-- Check current full-text search configurations
SHOW default_text_search_config;

-- List available configurations
SELECT cfgname FROM pg_ts_config;

-- Set default for session
SET default_text_search_config = 'english';

-- Set globally
ALTER DATABASE giljo_mcp SET default_text_search_config = 'english';
```

---

## Monitoring Queries

### 1. Real-Time Performance

```sql
-- Monitor active queries on mcp_context_index
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    query_start,
    state,
    wait_event_type,
    wait_event,
    LEFT(query, 100) as query_preview
FROM pg_stat_activity
WHERE query LIKE '%mcp_context_index%'
  AND state = 'active'
ORDER BY query_start;
```

### 2. Slow Query Log

```sql
-- Enable slow query logging (postgresql.conf)
-- log_min_duration_statement = 100  # Log queries > 100ms

-- View slow queries from pg_stat_statements
SELECT
    LEFT(query, 100) as query_preview,
    calls,
    ROUND(total_time::numeric, 2) as total_ms,
    ROUND(mean_time::numeric, 2) as mean_ms,
    ROUND(stddev_time::numeric, 2) as stddev_ms,
    ROUND((100 * total_time / sum(total_time) OVER ())::numeric, 2) AS percentage
FROM pg_stat_statements
WHERE query LIKE '%mcp_context_index%'
ORDER BY mean_time DESC
LIMIT 20;

-- Requires: CREATE EXTENSION pg_stat_statements;
```

### 3. Cache Hit Ratio

```sql
-- Check buffer cache hit ratio (should be > 99%)
SELECT
    schemaname,
    tablename,
    heap_blks_read,
    heap_blks_hit,
    ROUND(
        100.0 * heap_blks_hit / NULLIF(heap_blks_hit + heap_blks_read, 0),
        2
    ) AS cache_hit_ratio
FROM pg_statio_user_tables
WHERE tablename = 'mcp_context_index';

-- If ratio < 90%: Increase shared_buffers
-- If ratio < 80%: Serious performance issue - investigate
```

---

## Partitioning Strategy (100K+ Chunks)

### When to Partition

Partition `mcp_context_index` if:
- Total chunks > 100,000
- Search performance degrading
- Want to archive old chunks
- Need per-product isolation

### Partition by Product

```sql
-- Create partitioned table (REQUIRES MIGRATION)
CREATE TABLE mcp_context_index_partitioned (
    LIKE mcp_context_index INCLUDING ALL
) PARTITION BY HASH (product_id);

-- Create 16 partitions
DO $$
BEGIN
    FOR i IN 0..15 LOOP
        EXECUTE format(
            'CREATE TABLE mcp_context_index_p%s PARTITION OF mcp_context_index_partitioned
             FOR VALUES WITH (MODULUS 16, REMAINDER %s)',
            i, i
        );
    END LOOP;
END $$;

-- Migrate data (downtime required)
BEGIN;
INSERT INTO mcp_context_index_partitioned SELECT * FROM mcp_context_index;
ALTER TABLE mcp_context_index RENAME TO mcp_context_index_old;
ALTER TABLE mcp_context_index_partitioned RENAME TO mcp_context_index;
COMMIT;
```

### Partition by Date (Time-Series)

```sql
-- Partition by creation date (monthly)
CREATE TABLE mcp_context_index_partitioned (
    LIKE mcp_context_index INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create partitions for each month
CREATE TABLE mcp_context_index_2025_10 PARTITION OF mcp_context_index_partitioned
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE mcp_context_index_2025_11 PARTITION OF mcp_context_index_partitioned
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- Automate partition creation with pg_partman extension
```

---

## Troubleshooting Checklist

### Slow Searches (> 100ms)

- [ ] Check index exists: `\d mcp_context_index`
- [ ] Check index usage: `EXPLAIN ANALYZE <query>`
- [ ] Update statistics: `ANALYZE mcp_context_index`
- [ ] Check table bloat: See "Table Bloat Check"
- [ ] Check cache hit ratio: Should be > 99%
- [ ] Increase work_mem if seeing temp spills
- [ ] Rebuild GIN index: `REINDEX CONCURRENTLY`
- [ ] Check PostgreSQL logs for errors

### High Memory Usage

- [ ] Check work_mem settings
- [ ] Monitor temp file usage: `pg_stat_database.temp_files`
- [ ] Reduce concurrent connections
- [ ] Increase shared_buffers if RAM available
- [ ] Check for memory leaks in connection pooling

### Index Not Used

- [ ] Verify query uses `@@` operator
- [ ] Check tenant_key filter present (CRITICAL)
- [ ] Run `ANALYZE mcp_context_index`
- [ ] Check `random_page_cost` setting (should be ~1.1 for SSD)
- [ ] Verify query uses `plainto_tsquery()` or `to_tsquery()`
- [ ] Check if table too small (< 1000 rows = sequential scan faster)

---

## Benchmarking Script

```python
#!/usr/bin/env python3
"""
Benchmark mcp_context_index search performance
"""

import asyncio
import time
from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def benchmark_search_performance(
    session: AsyncSession,
    tenant_key: str,
    product_id: str
) -> Dict:
    """Run comprehensive performance benchmarks"""

    results = {
        'table_stats': {},
        'index_stats': {},
        'query_performance': [],
        'cache_stats': {}
    }

    # 1. Get table statistics
    table_stats = await session.execute(text("""
        SELECT
            pg_size_pretty(pg_total_relation_size('mcp_context_index')) as total_size,
            pg_size_pretty(pg_relation_size('mcp_context_index')) as table_size,
            pg_size_pretty(pg_indexes_size('mcp_context_index')) as indexes_size,
            (SELECT COUNT(*) FROM mcp_context_index WHERE tenant_key = :tenant_key) as row_count
    """), {"tenant_key": tenant_key})
    results['table_stats'] = dict(table_stats.fetchone()._mapping)

    # 2. Get index statistics
    index_stats = await session.execute(text("""
        SELECT
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_stat_user_indexes
        WHERE tablename = 'mcp_context_index'
        ORDER BY idx_scan DESC
    """))
    results['index_stats'] = [dict(row._mapping) for row in index_stats.fetchall()]

    # 3. Benchmark queries
    test_queries = [
        'database',
        'database migration',
        'api endpoint authentication',
        'schema design optimization'
    ]

    for query_text in test_queries:
        # Warm-up
        await session.execute(text("""
            SELECT chunk_id FROM mcp_context_index
            WHERE tenant_key = :tenant_key
              AND searchable_vector @@ plainto_tsquery('english', :query)
            LIMIT 10
        """), {"tenant_key": tenant_key, "query": query_text})

        # Timed execution
        times = []
        for _ in range(10):
            start = time.perf_counter()

            await session.execute(text("""
                SELECT chunk_id, ts_rank(searchable_vector, query) as rank
                FROM mcp_context_index,
                     plainto_tsquery('english', :query) query
                WHERE tenant_key = :tenant_key
                  AND searchable_vector @@ query
                ORDER BY rank DESC
                LIMIT 10
            """), {"tenant_key": tenant_key, "query": query_text})

            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        results['query_performance'].append({
            'query': query_text,
            'avg_ms': sum(times) / len(times),
            'min_ms': min(times),
            'max_ms': max(times)
        })

    # 4. Cache hit ratio
    cache_stats = await session.execute(text("""
        SELECT
            heap_blks_read,
            heap_blks_hit,
            ROUND(100.0 * heap_blks_hit / NULLIF(heap_blks_hit + heap_blks_read, 0), 2) AS hit_ratio
        FROM pg_statio_user_tables
        WHERE tablename = 'mcp_context_index'
    """))
    results['cache_stats'] = dict(cache_stats.fetchone()._mapping)

    return results

def print_benchmark_results(results: Dict):
    """Pretty-print benchmark results"""

    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK RESULTS")
    print("="*60)

    print("\n📊 Table Statistics:")
    for key, value in results['table_stats'].items():
        print(f"  {key}: {value}")

    print("\n📈 Index Statistics:")
    for idx in results['index_stats']:
        print(f"\n  {idx['indexname']}:")
        print(f"    Scans: {idx['idx_scan']}")
        print(f"    Size: {idx['size']}")

    print("\n⚡ Query Performance:")
    for perf in results['query_performance']:
        status = "✅" if perf['avg_ms'] < 100 else "⚠️" if perf['avg_ms'] < 200 else "❌"
        print(f"\n  {status} '{perf['query']}':")
        print(f"    Avg: {perf['avg_ms']:.2f}ms")
        print(f"    Min: {perf['min_ms']:.2f}ms")
        print(f"    Max: {perf['max_ms']:.2f}ms")

    print("\n💾 Cache Performance:")
    hit_ratio = results['cache_stats']['hit_ratio']
    status = "✅" if hit_ratio > 99 else "⚠️" if hit_ratio > 90 else "❌"
    print(f"  {status} Cache Hit Ratio: {hit_ratio}%")

    print("\n" + "="*60)
```

---

## Performance Targets Summary

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Search time (10K chunks) | < 100ms | > 200ms | > 500ms |
| Cache hit ratio | > 99% | < 95% | < 90% |
| Index scan ratio | > 95% | < 80% | < 50% |
| Dead tuple % | < 5% | > 10% | > 20% |
| Work_mem spills | 0 | > 10/min | > 100/min |

---

**Last Updated**: 2025-10-18
**Handover**: 0018
**Database Expert**: Production performance tuning
