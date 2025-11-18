# Context Tools API Reference

## Overview
GiljoAI provides 9 MCP tools for fetching context on-demand. All tools enforce multi-tenant isolation and return structured JSON.

## Authentication
All tools require:
- `product_id` or `project_id` (UUID)
- `tenant_key` (string) - Automatically injected by MCP server

## Tools

### 1. fetch_product_context

Fetch general product information.

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string",
  "include_metadata": false  // Optional
}
```

**Response**:
```json
{
  "product_name": "TinyContacts",
  "product_description": "Minimalist contact manager",
  "project_path": "/path/to/project",
  "core_features": ["Contact CRUD", "Search", "Export"],
  "is_active": true,
  "created_at": "2025-11-17T10:00:00Z"
}
```

### 2. fetch_vision_document

Fetch vision document chunks (paginated).

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string",
  "chunking": "moderate",  // none|light|moderate|heavy
  "offset": 0,             // Optional
  "limit": null            // Optional
}
```

**Response**:
```json
{
  "chunks": [...],
  "metadata": {
    "has_more": false,
    "next_offset": 0,
    "returned_chunks": 4,
    "total_chunks": 4,
    "total_tokens": 12500
  }
}
```

### 3. fetch_tech_stack

Fetch technology stack configuration.

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string",
  "sections": "all"  // required|all
}
```

**Response**:
```json
{
  "programming_languages": ["Python", "TypeScript"],
  "frontend_frameworks": ["Vue 3"],
  "backend_frameworks": ["FastAPI"],
  "databases": ["PostgreSQL"],
  "infrastructure": ["Docker"],
  "dev_tools": ["Git", "VS Code"]
}
```

### 4. fetch_architecture

Fetch architecture configuration.

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string",
  "depth": "overview"  // overview|detailed
}
```

**Response**:
```json
{
  "primary_pattern": "Microservices",
  "design_patterns": "Repository, Factory",
  "api_style": "REST",
  "architecture_notes": "Detailed notes..."
}
```

### 5. fetch_testing_config

Fetch testing strategy and quality standards.

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string"
}
```

**Response**:
```json
{
  "quality_standards": "Code review required, 80% coverage",
  "testing_strategy": "TDD",
  "coverage_target": 80,
  "testing_frameworks": ["pytest", "jest"],
  "test_commands": ["pytest tests/", "npm test"]
}
```

### 6. fetch_360_memory

Fetch sequential project history (paginated).

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string",
  "last_n_projects": 3,  // 1|3|5|10
  "offset": 0,           // Optional
  "limit": null          // Optional
}
```

**Response**:
```json
{
  "history": [
    {
      "sequence": 1,
      "project_name": "Project Alpha",
      "summary": "Implemented user authentication",
      "key_outcomes": [...],
      "git_commits": [...],
      "timestamp": "2025-11-16T10:00:00Z"
    }
  ],
  "metadata": {
    "has_more": false,
    "next_offset": 0,
    "returned_entries": 3,
    "total_entries": 3
  }
}
```

### 7. fetch_git_history

Fetch aggregated git commits.

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string",
  "commits": 25  // 10|25|50|100
}
```

**Response**:
```json
{
  "commits": [
    {
      "hash": "abc123",
      "message": "Add user authentication",
      "author": "dev@example.com",
      "timestamp": "2025-11-16T10:00:00Z"
    }
  ],
  "metadata": {
    "total_commits": 25,
    "github_integration_enabled": true
  }
}
```

### 8. fetch_agent_templates

Fetch agent template library.

**Parameters**:
```json
{
  "product_id": "uuid",
  "tenant_key": "string",
  "detail": "standard"  // minimal|standard|full
}
```

**Response**:
```json
{
  "templates": [
    {
      "name": "Backend Developer",
      "role": "implementer",
      "description": "Backend implementation specialist",
      "capabilities": [...],  // Only if detail=standard|full
      "tools": [...]          // Only if detail=full
    }
  ]
}
```

### 9. fetch_project_context

Fetch current project metadata.

**Parameters**:
```json
{
  "project_id": "uuid",
  "tenant_key": "string",
  "include_summary": false  // Optional
}
```

**Response**:
```json
{
  "project_name": "v1.0 Release",
  "project_alias": "v1.0",
  "project_description": "First production release",
  "orchestrator_mission": "Implement core features...",
  "status": "active",
  "staging_status": "complete",
  "context_used": 45000
}
```

## Error Handling

All tools return standard error format:
```json
{
  "error": "Product not found",
  "product_id": "uuid",
  "tenant_key": "string"
}
```

## Rate Limiting
MCP tools are not rate-limited but should be called responsibly. Excessive calls may impact performance.

## Pagination

Tools supporting pagination (vision_document, 360_memory):
1. Initial call with offset=0, limit=null
2. Check metadata.has_more
3. If true, call again with offset=metadata.next_offset
4. Repeat until has_more=false
