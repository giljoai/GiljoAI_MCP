# Context Management API Guide

**GiljoAI MCP - Context Management System API Reference**

**Version**: 1.0.0
**Base URL**: `http://localhost:7272/api/v1/context`
**Authentication**: X-Tenant-Key header required

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Chunk Vision Document](#chunk-vision-document)
  - [Search Context](#search-context)
  - [Load Context for Agent](#load-context-for-agent)
  - [Get Token Statistics](#get-token-statistics)
  - [Health Check](#health-check)
- [Request/Response Schemas](#requestresponse-schemas)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Common Use Cases](#common-use-cases)
- [Code Examples](#code-examples)

## Overview

The Context Management API provides endpoints for vision document chunking, indexing,
search, and dynamic context loading. All endpoints enforce multi-tenant isolation
via the `X-Tenant-Key` header.

### Quick Reference

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/products/{id}/chunk-vision` | POST | Chunk and index vision document | Yes |
| `/search` | GET | Search context by keywords | Yes |
| `/load-for-agent` | POST | Load context for specific agent | Yes |
| `/products/{id}/token-stats` | GET | Get context prioritization statistics | Yes |
| `/health` | GET | System health check | Yes |

## Authentication

All endpoints require the `X-Tenant-Key` header for multi-tenant isolation:

```bash
curl -X GET http://localhost:7272/api/v1/context/health \
  -H "X-Tenant-Key: tk_your_tenant_key"
```

The tenant key is obtained during product creation and must be included in every request.

## Endpoints

### Chunk Vision Document

**Endpoint**: `POST /api/v1/context/products/{product_id}/chunk-vision`

**Purpose**: Process a vision document by chunking it into semantic sections and indexing
for efficient retrieval.

**Path Parameters**:
- `product_id` (string, required): The product ID whose vision document to chunk

**Request Body**:
```json
{
  "force_rechunk": false
}
```

**Request Body Schema**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| force_rechunk | boolean | No | false | Force rechunking even if already chunked |

**Response**: `ChunkVisionResponse`

**Success Response (200)**:
```json
{
  "success": true,
  "product_id": "prod-abc-123",
  "chunks_created": 12,
  "total_tokens": 58432,
  "original_size": 234567,
  "reduction_percentage": null,
  "message": "Vision document chunked and indexed successfully"
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether operation succeeded |
| product_id | string | Product ID processed |
| chunks_created | integer | Number of chunks created |
| total_tokens | integer | Total tokens across all chunks |
| original_size | integer | Original document size in characters |
| reduction_percentage | float | null | Context prioritization percentage (if applicable) |
| message | string | null | Success or error message |

**Error Responses**:
- `404 Not Found`: Product not found or no vision document available
- `500 Internal Server Error`: Processing failed

**Example - Curl**:
```bash
curl -X POST http://localhost:7272/api/v1/context/products/prod-abc-123/chunk-vision \
  -H "X-Tenant-Key: tk_acme_corp" \
  -H "Content-Type: application/json" \
  -d '{
    "force_rechunk": false
  }'
```

**Example - Python**:
```python
import requests

response = requests.post(
    'http://localhost:7272/api/v1/context/products/prod-abc-123/chunk-vision',
    headers={
        'X-Tenant-Key': 'tk_acme_corp',
        'Content-Type': 'application/json'
    },
    json={'force_rechunk': False}
)

data = response.json()
print(f"Created {data['chunks_created']} chunks with {data['total_tokens']} tokens")
```

**Example - JavaScript**:
```javascript
const response = await fetch(
  'http://localhost:7272/api/v1/context/products/prod-abc-123/chunk-vision',
  {
    method: 'POST',
    headers: {
      'X-Tenant-Key': 'tk_acme_corp',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ force_rechunk: false })
  }
);

const data = await response.json();
console.log(`Created ${data.chunks_created} chunks`);
```

**Notes**:
- Vision document must exist in `Product.vision_document` or `Product.vision_path`
- Chunking uses tiktoken (cl100k_base) for accurate token counting
- Default chunk size: 5000 tokens
- Chunks respect semantic boundaries (headers, paragraphs)
- If already chunked and `force_rechunk=false`, returns success=false with message
- Multi-tenant isolation enforced via tenant_key

---

### Search Context

**Endpoint**: `GET /api/v1/context/search`

**Purpose**: Search indexed context chunks by keywords using PostgreSQL full-text search.

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | - | Search query (keywords) |
| product_id | string | No | null | Filter by product ID |
| limit | integer | No | 10 | Maximum chunks to return |

**Response**: `SearchContextResponse`

**Success Response (200)**:
```json
{
  "query": "authentication security jwt",
  "chunks": [
    {
      "chunk_id": "ck_123abc",
      "content": "# Authentication System\n\nThe system uses JWT tokens...",
      "tokens": 457,
      "chunk_number": 3,
      "relevance_score": 0.85
    },
    {
      "chunk_id": "ck_456def",
      "content": "## Security Requirements\n\nAll endpoints require...",
      "tokens": 392,
      "chunk_number": 5,
      "relevance_score": 0.72
    }
  ],
  "total_chunks": 2,
  "total_tokens": 849
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| query | string | Search query used |
| chunks | array | Array of matching chunks |
| total_chunks | integer | Number of chunks returned |
| total_tokens | integer | Total tokens across all returned chunks |

**Chunk Object Schema**:
| Field | Type | Description |
|-------|------|-------------|
| chunk_id | string | Unique chunk identifier |
| content | string | Chunk content |
| tokens | integer | Token count |
| chunk_number | integer | Sequential chunk number |
| relevance_score | float | null | Relevance score (0-1) if scored |

**Example - Curl**:
```bash
curl -X GET "http://localhost:7272/api/v1/context/search?query=authentication%20security&product_id=prod-abc-123&limit=5" \
  -H "X-Tenant-Key: tk_acme_corp"
```

**Example - Python**:
```python
import requests

response = requests.get(
    'http://localhost:7272/api/v1/context/search',
    headers={'X-Tenant-Key': 'tk_acme_corp'},
    params={
        'query': 'authentication security jwt',
        'product_id': 'prod-abc-123',
        'limit': 5
    }
)

data = response.json()
for chunk in data['chunks']:
    print(f"Chunk {chunk['chunk_number']}: {chunk['tokens']} tokens")
    print(f"Relevance: {chunk.get('relevance_score', 'N/A')}")
```

**Example - JavaScript**:
```javascript
const params = new URLSearchParams({
  query: 'authentication security jwt',
  product_id: 'prod-abc-123',
  limit: 5
});

const response = await fetch(
  `http://localhost:7272/api/v1/context/search?${params}`,
  {
    headers: { 'X-Tenant-Key': 'tk_acme_corp' }
  }
);

const data = await response.json();
data.chunks.forEach(chunk => {
  console.log(`Chunk ${chunk.chunk_number}: ${chunk.content.substring(0, 100)}...`);
});
```

**Notes**:
- Uses PostgreSQL full-text search with GIN indexes
- Performance: < 50ms for 10,000+ chunks
- If product_id omitted, searches across all products for tenant
- Empty query returns no results (use specific keywords)
- Results sorted by PostgreSQL relevance ranking

---

### Load Context for Agent

**Endpoint**: `POST /api/v1/context/load-for-agent`

**Purpose**: Load relevant context chunks for a specific agent based on role and mission.

**Request Body**:
```json
{
  "agent_type": "backend",
  "mission": "Implement user authentication with JWT tokens",
  "product_id": "prod-abc-123",
  "max_tokens": 8000
}
```

**Request Body Schema**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| agent_type | string | Yes | - | Agent role (backend, frontend, database, etc.) |
| mission | string | Yes | - | Agent mission or query for context selection |
| product_id | string | Yes | - | Product ID |
| max_tokens | integer | No | 10000 | Maximum tokens to load |

**Response**: `LoadContextResponse`

**Success Response (200)**:
```json
{
  "agent_type": "backend",
  "chunks": [
    {
      "chunk_id": "ck_123abc",
      "content": "# Authentication System\n\n...",
      "tokens": 1245,
      "chunk_number": 3,
      "relevance_score": 0.89
    },
    {
      "chunk_id": "ck_789ghi",
      "content": "## API Endpoints\n\n...",
      "tokens": 987,
      "chunk_number": 7,
      "relevance_score": 0.76
    }
  ],
  "total_chunks": 2,
  "total_tokens": 2232,
  "average_relevance": 0.825,
  "reduction_percentage": null
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| agent_type | string | Agent role requested |
| chunks | array | Selected chunks with relevance scores |
| total_chunks | integer | Number of chunks returned |
| total_tokens | integer | Total tokens (guaranteed <= max_tokens) |
| average_relevance | float | Average relevance score across chunks |
| reduction_percentage | float | null | Context prioritization if tracked |

**Example - Curl**:
```bash
curl -X POST http://localhost:7272/api/v1/context/load-for-agent \
  -H "X-Tenant-Key: tk_acme_corp" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "backend",
    "mission": "Implement user authentication with JWT tokens and refresh token support",
    "product_id": "prod-abc-123",
    "max_tokens": 8000
  }'
```

**Example - Python**:
```python
import requests

response = requests.post(
    'http://localhost:7272/api/v1/context/load-for-agent',
    headers={
        'X-Tenant-Key': 'tk_acme_corp',
        'Content-Type': 'application/json'
    },
    json={
        'agent_type': 'backend',
        'mission': 'Implement user authentication with JWT tokens',
        'product_id': 'prod-abc-123',
        'max_tokens': 8000
    }
)

data = response.json()
print(f"Loaded {data['total_chunks']} chunks ({data['total_tokens']} tokens)")
print(f"Average relevance: {data['average_relevance']:.2f}")

for chunk in data['chunks']:
    print(f"\nChunk {chunk['chunk_number']} (relevance: {chunk['relevance_score']:.2f})")
    print(chunk['content'][:200])
```

**Example - JavaScript**:
```javascript
const response = await fetch(
  'http://localhost:7272/api/v1/context/load-for-agent',
  {
    method: 'POST',
    headers: {
      'X-Tenant-Key': 'tk_acme_corp',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      agent_type: 'backend',
      mission: 'Implement user authentication with JWT tokens',
      product_id: 'prod-abc-123',
      max_tokens: 8000
    })
  }
);

const data = await response.json();
console.log(`Loaded ${data.total_chunks} chunks with avg relevance ${data.average_relevance.toFixed(2)}`);
```

**Notes**:
- Chunks sorted by relevance score (highest first)
- Role-based weighting applied (see Role Patterns below)
- Total tokens guaranteed <= max_tokens
- Relevance scoring: 0.0 (not relevant) to 1.0 (highly relevant)
- Aim for average_relevance > 0.5 for good results

**Role Patterns**:
```javascript
{
  "architect": ["architecture", "design", "structure", "pattern"],
  "implementer": ["implementation", "code", "function", "class"],
  "tester": ["testing", "test", "quality", "validation"],
  "analyzer": ["analysis", "requirements", "specification"],
  "orchestrator": ["mission", "vision", "goal", "objective"]
}
```

---

### Get Token Statistics

**Endpoint**: `GET /api/v1/context/products/{product_id}/token-stats`

**Purpose**: Get context prioritization statistics for a product.

**Path Parameters**:
- `product_id` (string, required): Product ID

**Response**: `TokenStatsResponse`

**Success Response (200)**:
```json
{
  "product_id": "prod-abc-123",
  "original_tokens": 58432,
  "condensed_tokens": 58432,
  "reduction_percentage": 0.0,
  "chunks_count": 12
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| product_id | string | Product ID |
| original_tokens | integer | Total tokens in all chunks |
| condensed_tokens | integer | Condensed tokens (if summarization used) |
| reduction_percentage | float | Context prioritization percentage |
| chunks_count | integer | Total number of chunks |

**Error Responses**:
- `404 Not Found`: No chunks found for this product

**Example - Curl**:
```bash
curl -X GET http://localhost:7272/api/v1/context/products/prod-abc-123/token-stats \
  -H "X-Tenant-Key: tk_acme_corp"
```

**Example - Python**:
```python
import requests

response = requests.get(
    'http://localhost:7272/api/v1/context/products/prod-abc-123/token-stats',
    headers={'X-Tenant-Key': 'tk_acme_corp'}
)

data = response.json()
print(f"Product: {data['product_id']}")
print(f"Chunks: {data['chunks_count']}")
print(f"Total Tokens: {data['original_tokens']:,}")
if data['reduction_percentage'] > 0:
    print(f"Reduction: {data['reduction_percentage']:.1f}%")
```

**Notes**:
- Returns total token count across all chunks
- reduction_percentage will be 0.0 unless condensed missions are tracked
- Use this to monitor document size and chunking effectiveness

---

### Health Check

**Endpoint**: `GET /api/v1/context/health`

**Purpose**: Check context management system health and performance.

**Response**: `HealthCheckResponse`

**Success Response (200)**:
```json
{
  "status": "healthy",
  "chunk_count": 1247,
  "search_performance_ms": 12.34,
  "message": "Context management system operational"
}
```

**Response Schema**:
| Field | Type | Description |
|-------|------|-------------|
| status | string | System status (healthy, degraded) |
| chunk_count | integer | Total chunks for tenant |
| search_performance_ms | float | null | Recent search performance in ms |
| message | string | null | Status message |

**Example - Curl**:
```bash
curl -X GET http://localhost:7272/api/v1/context/health \
  -H "X-Tenant-Key: tk_acme_corp"
```

**Example - Python**:
```python
import requests

response = requests.get(
    'http://localhost:7272/api/v1/context/health',
    headers={'X-Tenant-Key': 'tk_acme_corp'}
)

data = response.json()
print(f"Status: {data['status']}")
print(f"Chunks: {data['chunk_count']}")
if data['search_performance_ms']:
    print(f"Search Performance: {data['search_performance_ms']:.2f}ms")
```

**Notes**:
- Use for monitoring and alerting
- Check search_performance_ms regularly (should be < 100ms)
- Status "degraded" indicates issues

## Request/Response Schemas

### Common Headers

All requests should include:

```
X-Tenant-Key: tk_your_tenant_key
Content-Type: application/json (for POST requests)
```

### Pagination

Currently, pagination is handled via the `limit` parameter. Future versions may add
offset-based or cursor-based pagination.

### Rate Limiting

No rate limiting currently implemented. Consider implementing client-side throttling
for bulk operations.

## Error Handling

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 200 | OK | Request successful |
| 404 | Not Found | Product/chunks not found |
| 422 | Unprocessable Entity | Invalid request parameters |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Database not available |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**Product Not Found**:
```json
{
  "detail": "Product not found"
}
```

**No Vision Document**:
```json
{
  "detail": "No vision document available for this product"
}
```

**Missing Required Field**:
```json
{
  "detail": [
    {
      "loc": ["body", "agent_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Error Handling Best Practices

```python
import requests

try:
    response = requests.post(
        'http://localhost:7272/api/v1/context/load-for-agent',
        headers={'X-Tenant-Key': 'tk_acme_corp', 'Content-Type': 'application/json'},
        json={
            'agent_type': 'backend',
            'mission': 'Implement auth',
            'product_id': 'prod-123',
            'max_tokens': 8000
        },
        timeout=30
    )

    response.raise_for_status()  # Raises HTTPError for 4xx/5xx

    data = response.json()
    print(f"Success: Loaded {data['total_chunks']} chunks")

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Product not found or not chunked yet")
    elif e.response.status_code == 422:
        print(f"Invalid request: {e.response.json()}")
    else:
        print(f"HTTP error: {e}")

except requests.exceptions.Timeout:
    print("Request timed out")

except requests.exceptions.ConnectionError:
    print("Could not connect to server")

except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

### 1. Chunking Documents

**Best Practice**: Chunk once, use many times
```python
# DO: Chunk once when product is created/updated
response = requests.post(
    f'/api/v1/context/products/{product_id}/chunk-vision',
    headers=headers,
    json={'force_rechunk': False}
)

# DON'T: Rechunk on every request
# This wastes processing time and resources
```

### 2. Search Queries

**Best Practice**: Use specific, multi-keyword queries
```python
# DO: Specific query with multiple relevant keywords
query = "user authentication jwt token password hashing bcrypt"

# DON'T: Generic single-word query
query = "auth"
```

### 3. Error Handling

**Best Practice**: Handle all error cases
```python
# DO: Comprehensive error handling
try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    return response.json()
except requests.exceptions.HTTPError as e:
    # Handle specific HTTP errors
    logger.error(f"HTTP error: {e.response.status_code}")
except requests.exceptions.Timeout:
    # Handle timeouts
    logger.error("Request timed out")
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

### 4. Multi-Tenant Isolation

**Best Practice**: Always include tenant key
```python
# DO: Include tenant key in every request
headers = {'X-Tenant-Key': tenant_key}
response = requests.get(url, headers=headers)

# DON'T: Forget tenant key
response = requests.get(url)  # Will fail or use wrong tenant
```

## Common Use Cases

### Use Case 1: Process New Product Vision

```python
import requests

def process_product_vision(product_id, tenant_key):
    """Chunk and index a new product's vision document"""

    url = f'http://localhost:7272/api/v1/context/products/{product_id}/chunk-vision'
    headers = {
        'X-Tenant-Key': tenant_key,
        'Content-Type': 'application/json'
    }

    response = requests.post(
        url,
        headers=headers,
        json={'force_rechunk': False}
    )

    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print(f"✓ Created {data['chunks_created']} chunks")
            print(f"✓ Total tokens: {data['total_tokens']:,}")
            return True
        else:
            print(f"✗ {data['message']}")
            return False
    else:
        print(f"✗ Error: {response.status_code}")
        return False

# Usage
process_product_vision('prod-new-app', 'tk_acme_corp')
```

### Use Case 2: Search for Specific Topics

```python
import requests

def search_topics(product_id, tenant_key, topics, max_results=10):
    """Search for specific topics in vision document"""

    query = ' '.join(topics)

    url = 'http://localhost:7272/api/v1/context/search'
    headers = {'X-Tenant-Key': tenant_key}
    params = {
        'query': query,
        'product_id': product_id,
        'limit': max_results
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['total_chunks']} chunks matching: {query}")

        for chunk in data['chunks']:
            print(f"\n--- Chunk {chunk['chunk_number']} ({chunk['tokens']} tokens) ---")
            print(chunk['content'][:300])
            if chunk.get('relevance_score'):
                print(f"Relevance: {chunk['relevance_score']:.2f}")

        return data['chunks']
    else:
        print(f"Search failed: {response.status_code}")
        return []

# Usage
search_topics(
    'prod-abc-123',
    'tk_acme_corp',
    ['authentication', 'security', 'jwt', 'authorization']
)
```

## Code Examples

### Complete Python Client

```python
import requests
from typing import List, Dict, Optional

class ContextManagementClient:
    """Python client for Context Management API"""

    def __init__(self, base_url: str, tenant_key: str):
        self.base_url = base_url.rstrip('/')
        self.tenant_key = tenant_key
        self.headers = {
            'X-Tenant-Key': tenant_key,
            'Content-Type': 'application/json'
        }

    def chunk_vision(self, product_id: str, force_rechunk: bool = False) -> Dict:
        """Chunk and index vision document"""
        url = f"{self.base_url}/products/{product_id}/chunk-vision"
        response = requests.post(
            url,
            headers=self.headers,
            json={'force_rechunk': force_rechunk},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def search(self, query: str, product_id: Optional[str] = None,
               limit: int = 10) -> Dict:
        """Search context by keywords"""
        url = f"{self.base_url}/search"
        params = {'query': query, 'limit': limit}
        if product_id:
            params['product_id'] = product_id

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def load_for_agent(self, agent_type: str, mission: str,
                       product_id: str, max_tokens: int = 10000) -> Dict:
        """Load context for specific agent"""
        url = f"{self.base_url}/load-for-agent"
        response = requests.post(
            url,
            headers=self.headers,
            json={
                'agent_type': agent_type,
                'mission': mission,
                'product_id': product_id,
                'max_tokens': max_tokens
            },
            timeout=15
        )
        response.raise_for_status()
        return response.json()

    def get_token_stats(self, product_id: str) -> Dict:
        """Get context prioritization statistics"""
        url = f"{self.base_url}/products/{product_id}/token-stats"
        response = requests.get(url, headers=self.headers, timeout=5)
        response.raise_for_status()
        return response.json()

    def health_check(self) -> Dict:
        """Check system health"""
        url = f"{self.base_url}/health"
        response = requests.get(url, headers=self.headers, timeout=5)
        response.raise_for_status()
        return response.json()

# Usage
client = ContextManagementClient(
    'http://localhost:7272/api/v1/context',
    'tk_acme_corp'
)

# Chunk vision document
result = client.chunk_vision('prod-abc-123')
print(f"Created {result['chunks_created']} chunks")

# Search for authentication topics
search_results = client.search('authentication security jwt', product_id='prod-abc-123')
print(f"Found {search_results['total_chunks']} relevant chunks")

# Load context for backend agent
context = client.load_for_agent(
    'backend',
    'Implement user authentication',
    'prod-abc-123',
    max_tokens=8000
)
print(f"Loaded {context['total_chunks']} chunks ({context['total_tokens']} tokens)")
```

### JavaScript/TypeScript Client

```typescript
interface ChunkVisionResponse {
  success: boolean;
  product_id: string;
  chunks_created: number;
  total_tokens: number;
  original_size: number;
  message?: string;
}

interface SearchResponse {
  query: string;
  chunks: Array<{
    chunk_id: string;
    content: string;
    tokens: number;
    chunk_number: number;
    relevance_score?: number;
  }>;
  total_chunks: number;
  total_tokens: number;
}

class ContextManagementClient {
  private baseUrl: string;
  private tenantKey: string;

  constructor(baseUrl: string, tenantKey: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.tenantKey = tenantKey;
  }

  private get headers() {
    return {
      'X-Tenant-Key': this.tenantKey,
      'Content-Type': 'application/json'
    };
  }

  async chunkVision(productId: string, forceRechunk = false): Promise<ChunkVisionResponse> {
    const response = await fetch(
      `${this.baseUrl}/products/${productId}/chunk-vision`,
      {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ force_rechunk: forceRechunk })
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async search(query: string, productId?: string, limit = 10): Promise<SearchResponse> {
    const params = new URLSearchParams({
      query,
      limit: limit.toString()
    });

    if (productId) {
      params.append('product_id', productId);
    }

    const response = await fetch(
      `${this.baseUrl}/search?${params}`,
      { headers: this.headers }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async loadForAgent(
    agentType: string,
    mission: string,
    productId: string,
    maxTokens = 10000
  ) {
    const response = await fetch(
      `${this.baseUrl}/load-for-agent`,
      {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          agent_type: agentType,
          mission,
          product_id: productId,
          max_tokens: maxTokens
        })
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }
}

// Usage
const client = new ContextManagementClient(
  'http://localhost:7272/api/v1/context',
  'tk_acme_corp'
);

// Chunk vision document
const result = await client.chunkVision('prod-abc-123');
console.log(`Created ${result.chunks_created} chunks`);

// Load context for agent
const context = await client.loadForAgent(
  'backend',
  'Implement user authentication',
  'prod-abc-123',
  8000
);
console.log(`Loaded ${context.total_chunks} chunks`);
```

## Summary

The Context Management API provides five endpoints for complete vision document processing:

1. **Chunk Vision**: Process and index documents
2. **Search Context**: Find relevant chunks by keywords
3. **Load for Agent**: Get role-based context
4. **Chunk Stats**: Vision document chunking statistics
5. **Health Check**: System status

All endpoints enforce multi-tenant isolation via `X-Tenant-Key` header and provide
production-grade error handling and performance.

For implementation examples, see:
- [Context Integration Guide](../CONTEXT_INTEGRATION_GUIDE.md)
- [Test Suite](../../tests/integration/test_context_api.py)
- [Python Examples](../../examples/context_usage.py) (if available)

For performance details, see:
- [Context Performance Report](../CONTEXT_PERFORMANCE_REPORT.md)
