# Vision Context Management System

**GiljoAI MCP - Vision Document Chunking (Handover 0018)**

**Version**: 2.0.0
**Date**: 2025-10-18
**Last Updated**: 2026-03-18
**Status**: Production Ready

---

## Quick Links

- **[Context Tools API](../api/context_tools.md)** - How agents retrieve context via `fetch_context`
- **[Orchestrator Context Flow](../architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md)** - How context flows through the orchestrator

---

- [Overview](#overview)
- [Architecture](#architecture)
- [VisionDocumentChunker](#visiondocumentchunker)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [Performance Characteristics](#performance-characteristics)
- [Multi-Tenant Isolation](#multi-tenant-isolation)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Context Management System provides vision document chunking with accurate token counting
via tiktoken (cl100k_base encoding). Large vision documents are split into semantically
meaningful chunks stored in PostgreSQL, enabling the orchestrator to deliver focused context
to agents within Claude Code CLI's 25K ingest limit.

### Key Features

- **Accurate Token Counting**: Uses tiktoken (cl100k_base encoding) for precise token measurement
- **Semantic Chunking**: Respects document structure (headers, paragraphs, code blocks) via EnhancedChunker
- **Full-Text Search**: PostgreSQL full-text search with GIN indexes for sub-100ms chunk retrieval
- **Multi-Tenant Isolation**: Complete tenant separation via tenant_key

### Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Search Performance | < 100ms | < 50ms |
| Chunk Size | 5000 tokens | ~5000 tokens |
| Multi-Tenant Isolation | 100% | 100% |

## Architecture

The system's active component is the **VisionDocumentChunker**, which splits vision documents
into indexed chunks stored in PostgreSQL:

```
Vision Document --> VisionDocumentChunker --> mcp_context_index (PostgreSQL)
                                                     |
                                              Agent tools query
                                              chunks via context
                                              repository
```

### Flow

1. **Chunking Phase**: Vision document uploaded -> VisionDocumentChunker splits into chunks with metadata
2. **Storage Phase**: Chunks stored in `mcp_context_index` table with keywords and token counts
3. **Retrieval Phase**: Agent context tools (`get_vision_document`) query chunks via ContextRepository

## VisionDocumentChunker

**Location**: `src/giljo_mcp/context_management/chunker.py`

**Purpose**: Split large vision documents into semantic chunks with accurate token counting.

**Key Features**:
- Tiktoken-based token counting (cl100k_base encoding)
- Semantic boundary detection via EnhancedChunker
- Keyword extraction using term frequency
- Automatic summary generation (SUMI)
- Target chunk size: 5000 tokens

**Example**:
```python
from giljo_mcp.context_management import VisionDocumentChunker

chunker = VisionDocumentChunker(target_chunk_size=5000)

# Chunk a vision document
chunks = chunker.chunk_document(
    content=vision_text,
    product_id="prod-123"
)

# Each chunk contains:
# - content: The actual chunk text
# - tokens: Accurate token count via tiktoken
# - keywords: Extracted keywords (max 10)
# - summary: Auto-generated summary (max 200 chars)
# - chunk_number: Sequential number
# - total_chunks: Total chunks in document
```

**Chunking Algorithm**:
1. Initialize tiktoken encoder (cl100k_base)
2. Use EnhancedChunker to identify semantic boundaries
3. Create chunks respecting boundaries and target size
4. Count tokens accurately with tiktoken
5. Extract keywords via term frequency analysis
6. Generate summary from chunk content
7. Return enriched chunks with all metadata

## Database Schema

Chunks are stored in the `mcp_context_index` table:

- `chunk_id`: UUID primary key
- `tenant_key`: Multi-tenant isolation
- `product_id`: Product association
- `content`: Full chunk text
- `keywords`: JSONB array of keywords (GIN indexed)
- `token_count`: Accurate token count
- `chunk_order`: Sequential ordering
- `summary`: Auto-generated summary
- `created_at`: Timestamp

```sql
-- Verify GIN index exists on keywords
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'mcp_context_index'
  AND indexname LIKE '%keywords%';
```

## Configuration

### Target Chunk Size

Configure the target chunk size when initializing the chunker:

```python
# Default: 5000 tokens
chunker = VisionDocumentChunker()

# Custom chunk size
chunker = VisionDocumentChunker(target_chunk_size=3000)
```

**Recommendations**:
- Small documents (< 10K tokens): 2000-3000 tokens per chunk
- Medium documents (10K-50K tokens): 5000 tokens per chunk (default)
- Large documents (> 50K tokens): 7000-10000 tokens per chunk

### Database Configuration

The system uses PostgreSQL full-text search. Ensure adequate `shared_buffers` (256MB+) for optimal GIN index performance.

## Performance Characteristics

### Chunking Performance

| Document Size | Chunks Created | Processing Time | Performance |
|---------------|----------------|-----------------|-------------|
| 10,000 tokens | 2 chunks | < 500ms | Excellent |
| 50,000 tokens | 10 chunks | < 2s | Very Good |
| 100,000 tokens | 20 chunks | < 5s | Good |
| 200,000 tokens | 40 chunks | < 10s | Acceptable |

### Search Performance

| Index Size | Query Type | Average Response Time |
|------------|------------|----------------------|
| 100 chunks | Keyword | 10-20ms |
| 1,000 chunks | Keyword | 20-40ms |
| 10,000 chunks | Keyword | 30-50ms |
| 100,000 chunks | Keyword | 40-80ms |

**Target**: < 100ms (Achieved: < 50ms average)

### Memory Usage

| Operation | Memory Impact | Peak Usage |
|-----------|--------------|------------|
| Chunk 50K token document | Temporary spike | +20MB |
| Store 100 chunks | Minimal | +5MB |

### Optimization Recommendations

1. **Chunk Size**: Use 5000 tokens for optimal balance of granularity and performance
2. **Search Limit**: Limit search results to 20-50 chunks maximum
3. **Database**: Ensure PostgreSQL has adequate shared_buffers (256MB+)

## Multi-Tenant Isolation

The system enforces complete multi-tenant isolation at every level:

### Database Level

All operations filter by `tenant_key`:

```python
# All queries automatically include tenant_key
chunks = context_repo.search_chunks(
    session=session,
    tenant_key="tk_tenant_a",
    product_id="prod-123",
    query="search term"
)
# Returns ONLY chunks belonging to Tenant A
```

### Repository Level

The ContextRepository enforces tenant isolation in all database operations:

```python
results = context_repo.search_chunks(
    session=session,
    tenant_key=tenant_key,  # Required parameter
    product_id=product_id,
    query=query
)
```

### Verification

Run the multi-tenant isolation tests:

```bash
pytest tests/integration/test_context_api.py::TestMultiTenantIsolation -v
```

**Expected Result**: 100% isolation, zero cross-tenant data leakage

## Usage Examples

### Example 1: Processing a New Product Vision

```python
from giljo_mcp.context_management import VisionDocumentChunker

chunker = VisionDocumentChunker()

# Load vision document
with open('product_vision.md', 'r') as f:
    vision_content = f.read()

# Chunk the document
chunks = chunker.chunk_document(
    content=vision_content,
    product_id="prod-new-product"
)

print(f"Created {len(chunks)} chunks")
print(f"Total tokens: {sum(c.tokens for c in chunks)}")
```

### Example 2: Searching Chunks

```python
from giljo_mcp.repositories import ContextRepository

context_repo = ContextRepository()

# Search for security-related chunks
results = context_repo.search_chunks(
    session=session,
    tenant_key="tk_acme_corp",
    product_id="prod-new-product",
    query="security authentication authorization",
    limit=10
)
```

## Best Practices

### Chunking Strategy

**DO**:
- Use default 5000 token chunks for most cases
- Allow semantic boundary detection (EnhancedChunker)
- Process vision documents once and cache chunks
- Use force_rechunk=true only when vision changes

**DON'T**:
- Create chunks that are too small (< 1000 tokens)
- Create chunks that are too large (> 10000 tokens)
- Rechunk unnecessarily (wastes processing time)
- Ignore semantic boundaries

### Production Deployment

**DO**:
- Monitor chunk creation and storage
- Set up database indexes properly
- Use connection pooling

**DON'T**:
- Skip database index verification
- Ignore slow query logs
- Forget multi-tenant isolation testing

## Troubleshooting

### Issue: Chunking Takes Too Long

**Symptoms**: Vision document chunking exceeds 10 seconds

**Solutions**:
1. Check document size: `len(content)` should be < 500,000 characters
2. Verify tiktoken is installed: `pip show tiktoken`
3. Consider increasing chunk size to reduce chunk count

### Issue: Search Returns No Results

**Symptoms**: Context search returns empty array

**Solutions**:
1. Verify product has been chunked: Check `Product.chunked` flag
2. Verify tenant_key matches
3. Try broader search terms
4. Check database indexes: `\d+ mcp_context_index` in psql

### Issue: Multi-Tenant Data Leakage

**Symptoms**: Seeing data from other tenants

**Solutions**:
1. Verify tenant_key is passed correctly in all API calls
2. Check database queries include tenant_key filter
3. Review ContextRepository implementation
4. Run isolation tests

### Issue: High Memory Usage

**Symptoms**: Memory usage spikes during chunking

**Solutions**:
1. Process very large documents in batches
2. Increase chunk size to reduce chunk count
3. Monitor Python process memory limits

## Related Documentation

- [Context Tools API](../api/context_tools.md) - Agent context retrieval tools
- [Orchestrator Context Flow](../architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md) - Context flow architecture
- [Database Schema](../handovers/0017_HANDOVER_20251014_DATABASE_SCHEMA_ENHANCEMENT.md) - Database design

## Changelog

### Version 2.0.0 (2026-03-18)

- Removed dead references to DynamicContextLoader, ContextSummarizer, ContextManagementSystem (code deleted)
- Removed dead API endpoint documentation (endpoints never registered)
- Removed token reduction strategy/budgets sections (dead concepts)
- Focused document on the surviving VisionDocumentChunker and database schema

### Version 1.0.0 (2025-10-18)

Initial production release:
- VisionDocumentChunker with tiktoken integration
- 80 comprehensive tests (37 unit, 43 integration)
- Complete multi-tenant isolation
