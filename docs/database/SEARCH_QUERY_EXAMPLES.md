# PostgreSQL Full-Text Search Query Examples

**Handover 0018**: Context Management System
**Database**: PostgreSQL 18
**Purpose**: Production-ready search query patterns for mcp_context_index

---

## Table of Contents

1. [Basic Search Patterns](#basic-search-patterns)
2. [Advanced Search Techniques](#advanced-search-techniques)
3. [Multi-Tenant Queries](#multi-tenant-queries)
4. [Performance Optimization](#performance-optimization)
5. [Common Patterns by Use Case](#common-patterns-by-use-case)

---

## Basic Search Patterns

### 1. Simple Keyword Search

```sql
-- Search for chunks containing "database"
SELECT
    chunk_id,
    content_preview,
    ts_rank(searchable_vector, query) AS rank
FROM
    mcp_context_index,
    plainto_tsquery('english', 'database') AS query
WHERE
    tenant_key = 'tk_abc123...'
    AND searchable_vector @@ query
ORDER BY rank DESC
LIMIT 10;
```

**Python/SQLAlchemy**:
```python
from sqlalchemy import func

query = func.plainto_tsquery('english', 'database')

results = await session.execute(
    select(MCPContextIndex)
    .filter(
        MCPContextIndex.tenant_key == tenant_key,
        MCPContextIndex.searchable_vector.op('@@')(query)
    )
    .order_by(
        func.ts_rank(MCPContextIndex.searchable_vector, query).desc()
    )
    .limit(10)
)
```

### 2. Multi-Word Search (AND Logic)

```sql
-- Search for chunks containing ALL words: "database" AND "migration"
SELECT *
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ plainto_tsquery('english', 'database migration');
```

**Python/SQLAlchemy**:
```python
query = func.plainto_tsquery('english', 'database migration')
# Automatically uses AND logic between words
```

### 3. Phrase Search

```sql
-- Search for exact phrase "database schema"
SELECT *
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ phraseto_tsquery('english', 'database schema');
```

**Python/SQLAlchemy**:
```python
query = func.phraseto_tsquery('english', 'database schema')
# Matches exact phrase with proper word order
```

### 4. OR Search

```sql
-- Search for chunks containing "postgres" OR "mysql"
SELECT *
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ to_tsquery('english', 'postgres | mysql');
```

**Python/SQLAlchemy**:
```python
query = func.to_tsquery('english', 'postgres | mysql')
# Use pipe (|) for OR logic
```

### 5. NOT Search

```sql
-- Search for "database" but NOT "mysql"
SELECT *
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ to_tsquery('english', 'database & !mysql');
```

**Python/SQLAlchemy**:
```python
query = func.to_tsquery('english', 'database & !mysql')
# Use exclamation (!) for negation
```

---

## Advanced Search Techniques

### 1. Weighted Search (Relevance Tuning)

```sql
-- Search with custom weight priorities
-- A = 1.0, B = 0.4, C = 0.2, D = 0.1
SELECT
    chunk_id,
    content_preview,
    ts_rank_cd(searchable_vector, query, 32) AS rank
FROM
    mcp_context_index,
    plainto_tsquery('english', 'authentication security') AS query
WHERE
    tenant_key = 'tk_abc123...'
    AND searchable_vector @@ query
ORDER BY rank DESC;
```

**Ranking Functions**:
- `ts_rank()`: Simple ranking (faster)
- `ts_rank_cd()`: Cover density ranking (more accurate, slower)

**Normalization Options** (4th parameter):
- `0`: Default (no normalization)
- `1`: Divide by 1 + log(document length)
- `2`: Divide by document length
- `4`: Divide by mean harmonic distance between extents
- `8`: Divide by number of unique words
- `16`: Divide by 1 + log(number of unique words)
- `32`: Divide by itself + 1 (recommended for our use case)

### 2. Proximity Search

```sql
-- Find "database" within 5 words of "schema"
SELECT *
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ to_tsquery('english', 'database <5> schema');
```

### 3. Prefix Matching

```sql
-- Find words starting with "auth" (auth, authentication, authorize, etc.)
SELECT *
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ to_tsquery('english', 'auth:*');
```

**Python/SQLAlchemy**:
```python
query = func.to_tsquery('english', 'auth:*')
# Matches all words starting with "auth"
```

### 4. Highlighting Search Results

```sql
-- Highlight matching words in content
SELECT
    chunk_id,
    ts_headline(
        'english',
        content,
        query,
        'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=25'
    ) AS highlighted_content
FROM
    mcp_context_index,
    plainto_tsquery('english', 'database migration') AS query
WHERE
    tenant_key = 'tk_abc123...'
    AND searchable_vector @@ query;
```

**Python/SQLAlchemy**:
```python
from sqlalchemy import func

query = func.plainto_tsquery('english', 'database migration')

headline = func.ts_headline(
    'english',
    MCPContextIndex.content,
    query,
    'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=25'
)

results = await session.execute(
    select(MCPContextIndex.chunk_id, headline.label('highlighted'))
    .filter(
        MCPContextIndex.tenant_key == tenant_key,
        MCPContextIndex.searchable_vector.op('@@')(query)
    )
)
```

### 5. Faceted Search (Search + Filter)

```sql
-- Search with type filter
SELECT
    chunk_type,
    COUNT(*) as count,
    AVG(ts_rank(searchable_vector, query)) as avg_relevance
FROM
    mcp_context_index,
    plainto_tsquery('english', 'api endpoint') AS query
WHERE
    tenant_key = 'tk_abc123...'
    AND product_id = 'prod_xyz...'
    AND searchable_vector @@ query
GROUP BY chunk_type
ORDER BY avg_relevance DESC;
```

---

## Multi-Tenant Queries

### 1. Tenant-Isolated Product Search

```sql
-- CORRECT: Multi-tenant isolated search
SELECT *
FROM mcp_context_index
WHERE tenant_key = :tenant_key  -- SECURITY CRITICAL
  AND product_id = :product_id
  AND searchable_vector @@ plainto_tsquery('english', :search_query)
ORDER BY ts_rank(searchable_vector, plainto_tsquery('english', :search_query)) DESC;
```

### 2. Cross-Product Search (Same Tenant)

```sql
-- Search across all products for a tenant
SELECT
    product_id,
    chunk_id,
    content_preview,
    ts_rank(searchable_vector, query) AS rank
FROM
    mcp_context_index,
    plainto_tsquery('english', 'authentication') AS query
WHERE
    tenant_key = :tenant_key  -- SECURITY CRITICAL
    AND searchable_vector @@ query
ORDER BY rank DESC
LIMIT 20;
```

### 3. Multi-Tenant Analytics (Admin Only)

```sql
-- Count search results by tenant (admin dashboard)
SELECT
    tenant_key,
    COUNT(*) as chunk_count,
    AVG(token_count) as avg_tokens
FROM mcp_context_index
WHERE searchable_vector @@ plainto_tsquery('english', 'database')
GROUP BY tenant_key
ORDER BY chunk_count DESC;

-- WARNING: Only use in admin contexts where cross-tenant visibility is authorized
```

---

## Performance Optimization

### 1. Use Covering Indexes

```sql
-- Query that uses only indexed columns (faster)
SELECT chunk_id, product_id, tenant_key
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ plainto_tsquery('english', 'database');
-- No table heap scan needed - index-only scan
```

### 2. Limit Early

```sql
-- Apply LIMIT before expensive operations
SELECT
    chunk_id,
    ts_headline('english', content, query) AS highlighted
FROM (
    SELECT chunk_id, content
    FROM mcp_context_index,
         plainto_tsquery('english', 'database') AS query
    WHERE tenant_key = 'tk_abc123...'
      AND searchable_vector @@ query
    ORDER BY ts_rank(searchable_vector, query) DESC
    LIMIT 10  -- Limit BEFORE ts_headline (expensive operation)
) limited_results,
plainto_tsquery('english', 'database') AS query;
```

### 3. Pre-compiled Queries (Prepared Statements)

```python
# Use SQLAlchemy compiled queries for better performance
from sqlalchemy import select

# Compile query once
search_stmt = (
    select(MCPContextIndex)
    .filter(
        MCPContextIndex.tenant_key == bindparam('tenant_key'),
        MCPContextIndex.searchable_vector.op('@@')(
            func.plainto_tsquery('english', bindparam('search_query'))
        )
    )
    .order_by(
        func.ts_rank(
            MCPContextIndex.searchable_vector,
            func.plainto_tsquery('english', bindparam('search_query'))
        ).desc()
    )
    .limit(bindparam('limit'))
)

# Execute multiple times with different parameters
result1 = await session.execute(
    search_stmt,
    {"tenant_key": "tk_abc", "search_query": "database", "limit": 10}
)

result2 = await session.execute(
    search_stmt,
    {"tenant_key": "tk_xyz", "search_query": "api", "limit": 20}
)
```

### 4. Explain Analyze

```sql
-- Always check query plans in development
EXPLAIN ANALYZE
SELECT *
FROM mcp_context_index
WHERE tenant_key = 'tk_abc123...'
  AND searchable_vector @@ plainto_tsquery('english', 'database')
ORDER BY ts_rank(searchable_vector, plainto_tsquery('english', 'database')) DESC
LIMIT 10;

-- Look for:
-- - "Bitmap Index Scan on idx_mcp_context_searchable_gin" (GOOD)
-- - "Seq Scan" (BAD - missing index or poor statistics)
-- - Execution time < 100ms (TARGET)
```

---

## Common Patterns by Use Case

### Use Case 1: Agent Context Loading

**Scenario**: Load relevant chunks for database agent mission

```python
async def load_database_agent_context(
    session: AsyncSession,
    tenant_key: str,
    product_id: str,
    mission_keywords: List[str]
) -> List[MCPContextIndex]:
    """Load context for database agent"""

    # Build search query from mission keywords
    search_text = ' '.join(mission_keywords)
    query = func.plainto_tsquery('english', search_text)

    results = await session.execute(
        select(MCPContextIndex)
        .filter(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.product_id == product_id,
            MCPContextIndex.chunk_type.in_(['content', 'code']),  # Prefer code examples
            MCPContextIndex.searchable_vector.op('@@')(query)
        )
        .order_by(
            func.ts_rank_cd(MCPContextIndex.searchable_vector, query, 32).desc()
        )
        .limit(15)  # Max 15 chunks for database agent
    )

    return results.scalars().all()
```

### Use Case 2: Autocomplete Search

**Scenario**: Real-time search suggestions

```sql
-- Fast autocomplete using prefix matching
SELECT DISTINCT
    LEFT(content, 100) as preview
FROM mcp_context_index
WHERE tenant_key = :tenant_key
  AND searchable_vector @@ to_tsquery('english', :prefix || ':*')
LIMIT 5;

-- Example: prefix = 'auth' returns chunks with "authentication", "authorize", etc.
```

### Use Case 3: Similar Chunks

**Scenario**: Find chunks similar to a given chunk

```python
async def find_similar_chunks(
    session: AsyncSession,
    tenant_key: str,
    source_chunk_id: str,
    limit: int = 5
) -> List[MCPContextIndex]:
    """Find chunks similar to source chunk"""

    # Get source chunk keywords
    source = await session.get(MCPContextIndex, source_chunk_id)

    # Build query from source keywords
    search_text = ' | '.join(source.keywords)  # OR query
    query = func.to_tsquery('english', search_text)

    results = await session.execute(
        select(MCPContextIndex)
        .filter(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.product_id == source.product_id,
            MCPContextIndex.chunk_id != source_chunk_id,  # Exclude source
            MCPContextIndex.searchable_vector.op('@@')(query)
        )
        .order_by(
            func.ts_rank(MCPContextIndex.searchable_vector, query).desc()
        )
        .limit(limit)
    )

    return results.scalars().all()
```

### Use Case 4: Section-Based Search

**Scenario**: Search within specific document section

```sql
-- Search within "Architecture" section
SELECT *
FROM mcp_context_index
WHERE tenant_key = :tenant_key
  AND product_id = :product_id
  AND section_name ILIKE '%architecture%'
  AND searchable_vector @@ plainto_tsquery('english', :search_query)
ORDER BY chunk_order ASC;
```

### Use Case 5: Recent Content Search

**Scenario**: Search only recently added chunks

```sql
-- Search chunks from last 7 days
SELECT *
FROM mcp_context_index
WHERE tenant_key = :tenant_key
  AND created_at > NOW() - INTERVAL '7 days'
  AND searchable_vector @@ plainto_tsquery('english', :search_query)
ORDER BY created_at DESC, ts_rank(searchable_vector, plainto_tsquery('english', :search_query)) DESC;
```

---

## Query Performance Benchmarks

### Expected Performance

| Chunks | Operation | Target Time | Notes |
|--------|-----------|-------------|-------|
| 100 | Simple search | < 10ms | Hot cache |
| 1,000 | Simple search | < 50ms | Warm cache |
| 10,000 | Simple search | < 100ms | Cold cache |
| 100,000 | Simple search | < 200ms | May need partitioning |

### Performance Testing

```python
import time
from typing import List

async def benchmark_search(
    session: AsyncSession,
    tenant_key: str,
    queries: List[str],
    iterations: int = 100
):
    """Benchmark search performance"""

    results = []

    for query_text in queries:
        times = []

        for _ in range(iterations):
            start = time.perf_counter()

            query = func.plainto_tsquery('english', query_text)
            await session.execute(
                select(MCPContextIndex)
                .filter(
                    MCPContextIndex.tenant_key == tenant_key,
                    MCPContextIndex.searchable_vector.op('@@')(query)
                )
                .limit(10)
            )

            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        results.append({
            'query': query_text,
            'avg_ms': avg_time,
            'min_ms': min_time,
            'max_ms': max_time,
            'iterations': iterations
        })

        print(f"Query: '{query_text}'")
        print(f"  Avg: {avg_time:.2f}ms | Min: {min_time:.2f}ms | Max: {max_time:.2f}ms")

    return results
```

---

## Troubleshooting

### Query Not Using Index

**Symptom**: EXPLAIN shows "Seq Scan" instead of "Bitmap Index Scan"

**Solutions**:
1. Check index exists: `\d mcp_context_index`
2. Update statistics: `ANALYZE mcp_context_index;`
3. Rebuild index: `REINDEX INDEX CONCURRENTLY idx_mcp_context_searchable_gin;`
4. Check query syntax: Ensure using `@@` operator
5. Verify tenant_key filter is present

### Slow Queries

**Symptom**: Queries taking > 100ms

**Solutions**:
1. Check table size: `SELECT COUNT(*) FROM mcp_context_index;`
2. Check index size: `SELECT pg_size_pretty(pg_indexes_size('mcp_context_index'));`
3. Increase `maintenance_work_mem` for index operations
4. Consider table partitioning for > 100K rows
5. Use `ts_rank()` instead of `ts_rank_cd()` if speed is critical

### Incorrect Search Results

**Symptom**: Missing expected results or too many irrelevant results

**Solutions**:
1. Check language configuration: Ensure using 'english' consistently
2. Try different query types: `plainto_tsquery()` vs `to_tsquery()`
3. Review stemming: "database" finds "databases", "databasing"
4. Consider `simple` configuration for technical terms
5. Check content actually in searchable_vector: `SELECT searchable_vector FROM mcp_context_index WHERE chunk_id = '...'`

---

## References

- [PostgreSQL Full-Text Search Documentation](https://www.postgresql.org/docs/current/textsearch.html)
- [GIN Index Performance](https://www.postgresql.org/docs/current/textsearch-indexes.html)
- [Text Search Functions](https://www.postgresql.org/docs/current/functions-textsearch.html)

---

**Last Updated**: 2025-10-18
**Handover**: 0018
**Database Expert**: Production-ready search patterns
